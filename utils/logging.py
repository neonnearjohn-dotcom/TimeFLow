import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

# Контекстные переменные для correlation
_request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
_user_id_var: ContextVar[str | None] = ContextVar("user_id", default=None)

_SENSITIVE_KEYS = {"token", "password", "secret", "api_key"}


def _redact(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: ("***" if k.lower() in _SENSITIVE_KEYS else _redact(v)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_redact(v) for v in obj]
    return obj


class JSONFormatter(logging.Formatter):
    """JSON formatter для структурированных логов."""

    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "ts": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "func": record.funcName,
            "line": record.lineno,
            "request_id": _request_id_var.get(),
            "user_id": _user_id_var.get(),
        }

        for key, value in record.__dict__.items():
            if key in log_obj or key.startswith("_"):
                continue
            if key in {
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "exc_info",
                "exc_text",
                "stack_info",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "process",
                "processName",
            }:
                continue
            log_obj[key] = value

        log_obj = {k: v for k, v in log_obj.items() if v is not None}

        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        return json.dumps(_redact(log_obj), ensure_ascii=False)


def setup_logging(level: str = "INFO") -> None:
    """Настройка системы логирования."""
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Удаляем существующие handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Создаём handler с JSON форматированием
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    root_logger.addHandler(handler)

    # Убираем лишнее логирование от библиотек
    logging.getLogger("aiogram").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Получить logger для модуля."""
    return logging.getLogger(name)


def set_request_context(request_id: str | None = None, user_id: str | None = None) -> None:
    """Устанавливает контекст для текущего request."""
    _request_id_var.set(request_id)
    _user_id_var.set(user_id)


def get_request_id() -> str | None:
    """Получает текущий request_id из контекста."""
    return _request_id_var.get()


def get_user_id() -> str | None:
    """Получает текущий user_id из контекста."""
    return _user_id_var.get()
