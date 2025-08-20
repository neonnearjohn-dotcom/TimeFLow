from unittest.mock import AsyncMock

import pytest


@pytest.mark.asyncio
async def test_app_boot_without_firestore(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "TEST:TOKEN")

    import main

    dummy_bot = AsyncMock()
    dummy_bot.delete_webhook = AsyncMock()
    dummy_bot.session = AsyncMock()
    monkeypatch.setattr(main, "Bot", lambda *args, **kwargs: dummy_bot)

    dummy_dp = AsyncMock()
    dummy_dp.start_polling = AsyncMock()
    monkeypatch.setattr(main, "Dispatcher", lambda *args, **kwargs: dummy_dp)

    monkeypatch.setattr(main, "create_firestore_client", lambda: None)

    await main.main()

    assert dummy_dp.start_polling.called
    assert dummy_bot.delete_webhook.called
