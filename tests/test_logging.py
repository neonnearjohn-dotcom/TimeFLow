import io
import json
import sys

from utils.logging import (
    get_logger,
    get_request_id,
    set_request_context,
    set_request_id,
    setup_json_logging,
    setup_logging,
)


def test_json_logging_and_context(monkeypatch):
    buf = io.StringIO()
    monkeypatch.setattr(sys, "stdout", buf)
    setup_logging("INFO")
    set_request_context(request_id="req-123", user_id="u42")
    log = get_logger(__name__)
    log.info("Pomodoro started", extra={"session_id": "s1"})
    data = json.loads(buf.getvalue().strip())
    assert data["level"] == "INFO"
    assert data["message"] == "Pomodoro started"
    assert data["request_id"] == "req-123"
    assert data["user_id"] == "u42"
    assert data["session_id"] == "s1"


def test_back_compat_aliases(monkeypatch):
    buf = io.StringIO()
    monkeypatch.setattr(sys, "stdout", buf)
    setup_json_logging("INFO")
    set_request_id("req-456")
    log = get_logger(__name__)
    log.info("using token=abc123 and api_key=xyz")
    data = json.loads(buf.getvalue().strip())
    assert get_request_id() == "req-456"
    assert "token=***" in data["message"]
    assert "api_key=***" in data["message"]
