from __future__ import annotations
import contextvars
import datetime as _dt
import json
import logging
import re
import sys
from typing import Any, Dict

_request_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("request_id", default=None)

_STD_ATTRS = {
    "name","msg","args","levelname","levelno","pathname","filename","module","exc_info",
    "exc_text","stack_info","lineno","funcName","created","msecs","relativeCreated",
    "thread","threadName","processName","process","asctime",
}

class _JSONFormatter(logging.Formatter):
    REDACT_RE = re.compile(r"(token|password|secret|api_key)=([A-Za-z0-9\._\-]+)", re.IGNORECASE)

    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            "ts": _dt.datetime.now(_dt.timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "func": record.funcName,
            "line": record.lineno,
            "request_id": _request_id.get(),
        }
        for k, v in record.__dict__.items():
            if k not in _STD_ATTRS and k not in payload:
                payload[k] = v
        for k, v in list(payload.items()):
            if isinstance(v, str):
                payload[k] = self.REDACT_RE.sub(r"\\1=***", v)
        return json.dumps(payload, ensure_ascii=False)

def setup_json_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    root.setLevel(level.upper())
    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setFormatter(_JSONFormatter())
    root.handlers.clear()
    root.addHandler(handler)

def set_request_id(value: str | None) -> None:
    _request_id.set(value)

def get_logger(name: str | None = None) -> logging.Logger:
    return logging.getLogger(name or "timeflow")
