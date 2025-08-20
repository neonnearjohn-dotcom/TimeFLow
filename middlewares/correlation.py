# middlewares/correlation.py
from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from utils.logging import get_logger, set_request_context


class CorrelationMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        request_id = str(uuid.uuid4())

        user_id: str | None = None
        if isinstance(event, Message) and event.from_user:
            user_id = str(event.from_user.id)
        elif isinstance(event, CallbackQuery) and event.from_user:
            user_id = str(event.from_user.id)

        set_request_context(request_id=request_id, user_id=user_id)

        log = get_logger(__name__)
        log.info("update received", extra={"update_type": type(event).__name__})
        try:
            return await handler(event, data)
        finally:
            # очистим контекст, чтобы данные не «протекали» в следующий апдейт
            set_request_context(None, None)
