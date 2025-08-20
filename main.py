import asyncio
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from services.pomodoro_service import PomodoroService
from tasks.pomodoro_recovery import recovery_pass, start_scheduler
from utils.firestore_client import create_firestore_client
from utils.logging import get_logger, setup_logging
from utils.notify import make_notifier

log = get_logger(__name__)


async def main() -> None:
    """Entry point for the TimeFlow bot."""
    setup_logging(os.getenv("LOG_LEVEL", "INFO"))

    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN is not set")

    bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    db = create_firestore_client()
    service: PomodoroService | None = PomodoroService(db) if db else None
    notify = make_notifier(bot)

    if service:
        await recovery_pass(service=service, notify=notify)
        asyncio.create_task(start_scheduler(service=service, notify=notify, interval_sec=30))
    else:
        log.error("Firestore credentials not provided; skipping scheduler and recovery")

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
