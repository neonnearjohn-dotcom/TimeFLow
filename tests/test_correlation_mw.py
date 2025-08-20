import asyncio
import json
import logging
from io import StringIO
from unittest.mock import MagicMock

import pytest
from aiogram.types import CallbackQuery, Message

from middlewares import CorrelationMiddleware
from utils.logging import (
    JSONFormatter,
    get_logger,
    get_request_id,
    get_user_id,
    set_request_context,
)


@pytest.fixture(autouse=True)
def clear_context():
    set_request_context(None, None)


def _setup_capture():
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JSONFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)
    return stream


@pytest.mark.asyncio
async def test_concurrent_request_ids_isolated():
    mw = CorrelationMiddleware()

    async def handler(event, data):
        return get_request_id(), get_user_id()

    msg1 = MagicMock(spec=Message)
    msg1.from_user = MagicMock(id=1)
    msg2 = MagicMock(spec=Message)
    msg2.from_user = MagicMock(id=2)

    res1, res2 = await asyncio.gather(mw(handler, msg1, {}), mw(handler, msg2, {}))

    assert res1[0] != res2[0]
    assert res1[1] == "1"
    assert res2[1] == "2"
    assert get_request_id() is None
    assert get_user_id() is None


@pytest.mark.asyncio
async def test_user_id_in_handler_logs():
    stream = _setup_capture()
    mw = CorrelationMiddleware()

    async def handler(event, data):
        log = get_logger(__name__)
        log.info("handler called")

    msg = MagicMock(spec=Message)
    msg.from_user = MagicMock(id=42)

    await mw(handler, msg, {})

    lines = stream.getvalue().strip().splitlines()
    record = json.loads(lines[-1])
    assert record["user_id"] == "42"
    assert record["request_id"]


@pytest.mark.asyncio
async def test_callback_query_extraction():
    mw = CorrelationMiddleware()

    async def handler(event, data):
        return get_user_id()

    cb = MagicMock(spec=CallbackQuery)
    cb.from_user = MagicMock(id=99)

    user = await mw(handler, cb, {})
    assert user == "99"


@pytest.mark.asyncio
async def test_missing_user_id_not_logged():
    stream = _setup_capture()
    mw = CorrelationMiddleware()

    async def handler(event, data):
        pass

    msg = MagicMock(spec=Message)
    msg.from_user = None

    await mw(handler, msg, {})

    line = stream.getvalue().strip().splitlines()[0]
    record = json.loads(line)
    assert "user_id" not in record


@pytest.mark.asyncio
async def test_secret_redaction():
    stream = _setup_capture()
    mw = CorrelationMiddleware()

    async def handler(event, data):
        log = get_logger(__name__)
        log.info("secret", extra={"token": "abc", "api_key": "key"})

    msg = MagicMock(spec=Message)
    msg.from_user = MagicMock(id=5)

    await mw(handler, msg, {})

    record = json.loads(stream.getvalue().strip().splitlines()[-1])
    assert record["token"] == "***"
    assert record["api_key"] == "***"
