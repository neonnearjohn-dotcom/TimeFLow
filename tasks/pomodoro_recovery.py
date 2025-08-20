import asyncio
from typing import Awaitable, Callable

from services.pomodoro_service import PomodoroService
from utils.logging import get_logger, set_request_context

logger = get_logger(__name__)


async def recovery_pass(
    service: PomodoroService, notify: Callable[[str, str], Awaitable[None]], batch_size: int = 100
) -> int:
    """
    Единоразовый проход восстановления просроченных сессий.
    Возвращает количество обработанных сессий.
    """
    set_request_context(request_id="recovery-pass")

    logger.info("Starting recovery pass")

    processed = 0
    total_notified = 0

    while True:
        # Получаем пачку просроченных сессий
        sessions = await service.fetch_expired_active(limit=batch_size)

        if not sessions:
            break

        # Обрабатываем каждую сессию
        for session_id, session in sessions:
            set_request_context(user_id=session.user_id)

            notified = await service.mark_done_and_notify(session_id=session_id, notify=notify)

            if notified:
                total_notified += 1

            processed += 1

        # Небольшая пауза между пачками
        await asyncio.sleep(0.1)

    logger.info(
        "Recovery pass completed",
        extra={
            "processed": processed,
            "notified": total_notified,
        },
    )

    set_request_context(request_id=None, user_id=None)
    return processed


async def start_scheduler(
    service: PomodoroService,
    notify: Callable[[str, str], Awaitable[None]],
    interval_sec: int = 30,
    shutdown_event: asyncio.Event = None,
) -> None:
    """
    Периодическая проверка просроченных сессий.
    Останавливается при установке shutdown_event.
    """
    logger.info("Starting Pomodoro scheduler", extra={"interval_sec": interval_sec})

    while True:
        # Проверяем флаг остановки
        if shutdown_event and shutdown_event.is_set():
            logger.info("Pomodoro scheduler stopped by shutdown event")
            break

        try:
            # Устанавливаем контекст для этой итерации
            set_request_context(request_id=f"scheduler-tick-{asyncio.get_event_loop().time()}")

            # Получаем и обрабатываем просроченные сессии
            sessions = await service.fetch_expired_active(limit=50)

            for session_id, session in sessions:
                set_request_context(user_id=session.user_id)

                await service.mark_done_and_notify(session_id=session_id, notify=notify)

            if sessions:
                logger.info("Scheduler tick processed", extra={"count": len(sessions)})

        except Exception as e:
            logger.error("Scheduler tick failed", extra={"error": str(e)})

        finally:
            set_request_context(request_id=None, user_id=None)

        # Ждём следующей итерации
        try:
            await asyncio.wait_for(
                shutdown_event.wait() if shutdown_event else asyncio.sleep(interval_sec),
                timeout=interval_sec,
            )
            # Если дождались shutdown_event, выходим
            if shutdown_event and shutdown_event.is_set():
                logger.info("Pomodoro scheduler stopped by shutdown event")
                break
        except asyncio.TimeoutError:
            # Таймаут истёк, продолжаем цикл
            pass
