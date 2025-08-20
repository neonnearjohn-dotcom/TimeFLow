# middlewares/correlation.py
from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from utils.logging import get_logger, set_request_context

logger = get_logger(__name__)


class CorrelationMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        request_id = str(uuid.uuid4())
        user_id: str | None = None
        update_type = type(event).__name__
        if isinstance(event, Message) and event.from_user:
            user_id = str(event.from_user.id)
            update_type = "message"
        elif isinstance(event, CallbackQuery) and event.from_user:
            user_id = str(event.from_user.id)
            update_type = "callback_query"
        elif getattr(event, "message", None) and event.message.from_user:
            user_id = str(event.message.from_user.id)
            update_type = "message"
        elif getattr(event, "poll", None):
            update_type = "poll"
        elif getattr(event, "poll_answer", None):
            update_type = "poll_answer"

        set_request_context(request_id=request_id, user_id=user_id)
        data["request_id"] = request_id

        logger.info(
            "update received",
            extra={
                "request_id": request_id,
                "user_id": user_id,
                "update_type": update_type,
            },
        )
        try:
            return await handler(event, data)
        finally:
            # очистим контекст, чтобы значения не «протекали» в следующий апдейт
            set_request_context(request_id=None, user_id=None)
