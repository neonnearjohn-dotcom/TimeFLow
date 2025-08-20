from typing import Awaitable, Callable

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from utils.logging import get_logger

logger = get_logger(__name__)


def make_notifier(bot: Bot) -> Callable[[str, str], Awaitable[None]]:
    async def notify(user_id: str, message: str) -> None:
        try:
            await bot.send_message(chat_id=user_id, text=message)
            logger.info("Notification sent", extra={"user_id": user_id})
        except TelegramAPIError as e:
            logger.error(
                "Notification failed",
                extra={"user_id": user_id, "error": str(e)},
            )
    return notify
