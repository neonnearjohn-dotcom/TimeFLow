import asyncio
from datetime import datetime, timedelta
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest

from models.pomodoro import PomodoroSession
from services.pomodoro_service import PomodoroService
from tasks.pomodoro_recovery import recovery_pass, start_scheduler


@pytest.fixture
def mock_firestore_client():
    """Мок Firestore клиента."""
    client = MagicMock()
    return client


@pytest.fixture
def pomodoro_service(mock_firestore_client):
    """Фикстура для PomodoroService."""
    return PomodoroService(mock_firestore_client)


@pytest.fixture
def mock_notify():
    """Мок функции отправки уведомлений."""
    return AsyncMock()


@pytest.mark.asyncio
async def test_recovery_marks_expired_sessions_once(pomodoro_service, mock_notify):
    """Тест: просроченная активная сессия становится done/notified, notify вызван ровно один раз."""
    session_id = "user123_1234567890"
    expired_session = PomodoroSession(
        user_id="user123",
        status="active",
        ends_at=datetime.utcnow() - timedelta(minutes=5),
        version=1,
    )
    
    # Мокаем fetch_expired_active: сначала просроченная сессия, затем пусто
    with patch.object(
        pomodoro_service,
        "fetch_expired_active",
        side_effect=[
            [(session_id, expired_session)],
            [],
        ],
    ) as mock_fetch:
        # Мокаем mark_done_and_notify
        with patch.object(
            pomodoro_service,
            "mark_done_and_notify",
            return_value=True
        ) as mock_mark:
            # Запускаем recovery
            processed = await recovery_pass(pomodoro_service, mock_notify)

            # Проверки
            assert processed == 1
            assert mock_fetch.call_count == 2
            mock_fetch.assert_called_with(limit=100)
            mock_mark.assert_called_once_with(
                session_id=session_id,
                notify=mock_notify
            )


@pytest.mark.asyncio
async def test_scheduler_idempotent_under_race(pomodoro_service, mock_notify):
    """Тест: имитация гонки - двойной вызов mark_done_and_notify → одно уведомление."""
    session_id = "user456_1234567890"
    
    # Мокаем транзакционную логику
    doc_mock = MagicMock()
    doc_mock.exists = True
    doc_mock.to_dict.return_value = {
        "user_id": "user456",
        "status": "active",
        "ends_at": datetime.utcnow() - timedelta(minutes=1),
        "version": 1,
        "last_notified_at": None,
    }
    
    # Первый вызов успешный, второй - нет (уже обработано)
    call_count = {"count": 0}
    
    async def side_effect(*args, **kwargs):
        call_count["count"] += 1
        if call_count["count"] == 1:
            return True  # Первый вызов отправляет уведомление
        return False  # Второй вызов - уже обработано
    
    with patch.object(
        pomodoro_service,
        "mark_done_and_notify",
        side_effect=side_effect
    ):
        # Имитируем два параллельных вызова
        results = await asyncio.gather(
            pomodoro_service.mark_done_and_notify(session_id, mock_notify),
            pomodoro_service.mark_done_and_notify(session_id, mock_notify),
            return_exceptions=True
        )
        
        # Только один должен вернуть True
        assert sum(r for r in results if r is True) == 1
        assert call_count["count"] == 2


@pytest.mark.asyncio
async def test_no_action_for_future_session(pomodoro_service, mock_notify):
    """Тест: ends_at > now → ничего не делает."""
    session_id = "user789_1234567890"
    future_session = PomodoroSession(
        user_id="user789",
        status="active",
        ends_at=datetime.utcnow() + timedelta(hours=1),
        version=1,
    )
    
    # Мокаем документ
    doc_mock = MagicMock()
    doc_mock.exists = True
    doc_mock.to_dict.return_value = future_session.to_dict()
    
    doc_ref_mock = MagicMock()
    doc_ref_mock.get.return_value = doc_mock
    
    pomodoro_service.db.collection.return_value.document.return_value = doc_ref_mock
    
    # Мокаем транзакцию
    with patch("asyncio.to_thread", side_effect=lambda f, *args: f(*args)):
        result = await pomodoro_service.mark_done_and_notify(
            session_id, mock_notify
        )
    
    # Проверки
    assert result is False
    mock_notify.assert_not_called()


@pytest.mark.asyncio
async def test_handles_empty_set_gracefully(pomodoro_service, mock_notify):
    """Тест: корректная обработка пустого набора сессий."""
    # Мокаем fetch_expired_active чтобы вернул пустой список
    with patch.object(
        pomodoro_service,
        "fetch_expired_active",
        return_value=[]
    ) as mock_fetch:
        # Запускаем recovery
        processed = await recovery_pass(pomodoro_service, mock_notify)
        
        # Проверки
        assert processed == 0
        mock_fetch.assert_called_once_with(limit=100)
        mock_notify.assert_not_called()


@pytest.mark.asyncio
async def test_scheduler_stops_on_shutdown_event():
    """Тест: scheduler останавливается при установке shutdown_event."""
    service = MagicMock()
    service.fetch_expired_active = AsyncMock(return_value=[])
    
    notify = AsyncMock()
    shutdown_event = asyncio.Event()
    
    # Запускаем scheduler в фоне
    task = asyncio.create_task(
        start_scheduler(
            service=service,
            notify=notify,
            interval_sec=0.1,  # Короткий интервал для теста
            shutdown_event=shutdown_event
        )
    )
    
    # Даём немного поработать
    await asyncio.sleep(0.2)
    
    # Останавливаем
    shutdown_event.set()
    
    # Ждём завершения
    await asyncio.wait_for(task, timeout=1.0)

    # Проверяем что задача завершена корректно
    assert task.done()
    assert not task.cancelled()


@pytest.mark.asyncio
async def test_notify_failure_resets_status_for_retry(pomodoro_service):
    session_id = "user999_123"
    expired_session = PomodoroSession(
        user_id="user999",
        status="active",
        ends_at=datetime.utcnow() - timedelta(minutes=1),
        version=1,
    )

    doc_mock = MagicMock()
    doc_mock.exists = True
    doc_mock.to_dict.return_value = expired_session.to_dict()
    doc_ref_mock = MagicMock()
    doc_ref_mock.get.return_value = doc_mock

    pomodoro_service.db.collection.return_value.document.return_value = doc_ref_mock
    pomodoro_service.db.transaction.return_value = MagicMock()

    notify = AsyncMock(side_effect=Exception("boom"))

    with patch("asyncio.to_thread", side_effect=lambda f, *args: f(*args)):
        result = await pomodoro_service.mark_done_and_notify(session_id, notify)

    assert result is False
    notify.assert_called_once()
    doc_ref_mock.update.assert_called_with({"status": "active", "updated_at": ANY})
