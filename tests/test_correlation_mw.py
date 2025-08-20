import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.types import Message, Update, User

from middlewares.correlation import CorrelationMiddleware


@pytest.fixture
def correlation_middleware():
    """Фикстура для создания экземпляра middleware."""
    return CorrelationMiddleware()


@pytest.fixture
def mock_update_with_user():
    """Фикстура для Update с user_id."""
    user = User(id=123456, is_bot=False, first_name="Test")
    message = MagicMock(spec=Message)
    message.from_user = user

    update = MagicMock(spec=Update)
    update.update_id = 1001
    update.message = message
    update.callback_query = None
    update.inline_query = None
    update.edited_message = None
    update.my_chat_member = None
    update.poll = None
    update.poll_answer = None

    return update


@pytest.fixture
def mock_update_without_user():
    """Фикстура для Update без user_id (например, poll)."""
    update = MagicMock(spec=Update)
    update.update_id = 1002
    update.message = None
    update.callback_query = None
    update.inline_query = None
    update.edited_message = None
    update.my_chat_member = None
    update.poll = MagicMock()  # Poll без from_user
    update.poll_answer = None

    return update


@pytest.mark.asyncio
async def test_correlation_middleware_with_user(correlation_middleware, mock_update_with_user):
    """Тест: middleware добавляет request_id и извлекает user_id."""
    handler = AsyncMock(return_value="ok")
    data = {}

    with patch("middlewares.correlation.logger") as mock_logger:
        with patch("middlewares.correlation.set_request_context") as mock_set_context:
            with patch(
                "uuid.uuid4", return_value=uuid.UUID("12345678-1234-5678-1234-567812345678")
            ):
                result = await correlation_middleware(handler, mock_update_with_user, data)

    # Проверяем что handler был вызван
    handler.assert_called_once_with(mock_update_with_user, data)

    # Проверяем что request_id добавлен в data
    assert "request_id" in data
    assert data["request_id"] == "12345678-1234-5678-1234-567812345678"

    # Проверяем логирование
    mock_logger.info.assert_called_once()
    call_args = mock_logger.info.call_args
    assert call_args[0][0] == "update received"
    assert call_args[1]["extra"]["user_id"] == "123456"
    assert call_args[1]["extra"]["update_type"] == "message"
    assert call_args[1]["extra"]["request_id"] == "12345678-1234-5678-1234-567812345678"

    # Проверяем установку контекста
    assert mock_set_context.call_count == 2  # установка и очистка
    first_call = mock_set_context.call_args_list[0]
    assert first_call[1]["request_id"] == "12345678-1234-5678-1234-567812345678"
    assert first_call[1]["user_id"] == "123456"

    assert result == "ok"


@pytest.mark.asyncio
async def test_correlation_middleware_without_user(
    correlation_middleware, mock_update_without_user
):
    """Тест: middleware корректно обрабатывает update без user_id."""
    handler = AsyncMock(return_value="ok")
    data = {}

    with patch("middlewares.correlation.logger") as mock_logger:
        with patch("middlewares.correlation.set_request_context") as mock_set_context:
            with patch(
                "uuid.uuid4", return_value=uuid.UUID("87654321-4321-8765-4321-876543218765")
            ):
                result = await correlation_middleware(handler, mock_update_without_user, data)

    # Проверяем что handler был вызван
    handler.assert_called_once_with(mock_update_without_user, data)

    # Проверяем что request_id добавлен в data
    assert "request_id" in data
    assert data["request_id"] == "87654321-4321-8765-4321-876543218765"

    # Проверяем логирование
    mock_logger.info.assert_called_once()
    call_args = mock_logger.info.call_args
    assert call_args[0][0] == "update received"
    assert call_args[1]["extra"]["user_id"] is None
    assert call_args[1]["extra"]["update_type"] == "poll"
    assert call_args[1]["extra"]["request_id"] == "87654321-4321-8765-4321-876543218765"

    # Проверяем установку контекста
    assert mock_set_context.call_count == 2  # установка и очистка
    first_call = mock_set_context.call_args_list[0]
    assert first_call[1]["request_id"] == "87654321-4321-8765-4321-876543218765"
    assert first_call[1]["user_id"] is None

    assert result == "ok"
