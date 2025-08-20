import io
import json
import sys
from utils.logging import setup_json_logging, get_logger, set_request_id

def test_json_logging_includes_basic_fields(monkeypatch):
    buf = io.StringIO()
    monkeypatch.setattr(sys, "stderr", buf)
    setup_json_logging("INFO")
    set_request_id("req-123")
    log = get_logger(__name__)
    log.info("Pomodoro started", extra={"user_id": "u42", "session_id": "s1"})
    line = buf.getvalue().strip()
    data = json.loads(line)
    assert data["level"] == "INFO"
    assert data["message"] == "Pomodoro started"
    assert data["request_id"] == "req-123"
    assert data["user_id"] == "u42"
    assert data["session_id"] == "s1"
    assert "ts" in data and "module" in data and "line" in data

def test_redaction_of_secrets(monkeypatch):
    buf = io.StringIO()
    monkeypatch.setattr(sys, "stderr", buf)
    setup_json_logging("INFO")
    log = get_logger(__name__)
    log.info("using token=abc123 and api_key=xyz")
    data = json.loads(buf.getvalue().strip())
    assert "token=***" in data["message"]
    assert "api_key=***" in data["message"]