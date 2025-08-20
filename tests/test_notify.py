import logging
import pytest
from unittest.mock import AsyncMock

from aiogram.exceptions import TelegramAPIError
from aiogram.methods import SendMessage

from utils.notify import make_notifier


@pytest.mark.asyncio
async def test_notifier_sends_message_once():
    bot = AsyncMock()
    notify = make_notifier(bot)
    await notify("42", "hi")
    bot.send_message.assert_called_once_with(chat_id="42", text="hi")


@pytest.mark.asyncio
async def test_notifier_logs_error(caplog):
    bot = AsyncMock()
    method = SendMessage(chat_id=1, text="a")
    bot.send_message.side_effect = TelegramAPIError(method, "boom")
    notify = make_notifier(bot)
    with caplog.at_level(logging.ERROR):
        await notify("42", "hi")
    assert "Notification failed" in caplog.text
