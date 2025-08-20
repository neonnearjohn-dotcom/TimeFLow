import json
import logging
import re
import sys
from contextvars import ContextVar

# Контекстные переменные для correlation
_request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
_user_id_var: ContextVar[str | None] = ContextVar("user_id", default=None)


class JSONFormatter(logging.Formatter):
    """JSON formatter для структурированных логов."""

    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": _redact_secrets(record.getMessage()),
            "request_id": _request_id_var.get(),
            "user_id": _user_id_var.get(),
        }

        reserved = {
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
            "processName",
            "process",
            "message",
        }

        for key, value in record.__dict__.items():
            if key not in reserved and not key.startswith("_"):
                log_obj[key] = value

        # Убираем None значения
        log_obj = {k: v for k, v in log_obj.items() if v is not None}

        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_obj, ensure_ascii=False)


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
    if request_id is not None:
        _request_id_var.set(request_id)
    if user_id is not None:
        _user_id_var.set(user_id)


def get_request_id() -> str | None:
    """Получает текущий request_id из контекста."""
    return _request_id_var.get()


def get_user_id() -> str | None:
    """Получает текущий user_id из контекста."""
    return _user_id_var.get()


# --- Backwards compatibility aliases ---


def set_request_id(request_id: str | None = None) -> None:
    set_request_context(request_id=request_id)


def setup_json_logging(level: str = "INFO") -> None:
    setup_logging(level)


_SECRET_RE = re.compile(r"(token|password|secret|api_key)=([^\s]+)", re.IGNORECASE)


def _redact_secrets(message: str) -> str:
    return _SECRET_RE.sub(lambda m: f"{m.group(1)}=***", message)
