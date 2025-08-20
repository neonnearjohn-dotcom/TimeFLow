import json
import logging
import sys
from contextvars import ContextVar
from typing import Any, Optional

# Контекстные переменные для correlation
_request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
_user_id_var: ContextVar[Optional[str]] = ContextVar("user_id", default=None)


class JSONFormatter(logging.Formatter):
    """JSON formatter для структурированных логов."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": _request_id_var.get(),
            "user_id": _user_id_var.get(),
        }
        
        # Добавляем extra поля
        if hasattr(record, "extra"):
            for key, value in record.extra.items():
                if key not in ["timestamp", "level", "logger", "message"]:
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


def set_request_context(request_id: Optional[str] = None, user_id: Optional[str] = None) -> None:
    """Устанавливает контекст для текущего request."""
    if request_id is not None:
        _request_id_var.set(request_id)
    if user_id is not None:
        _user_id_var.set(user_id)


def get_request_id() -> Optional[str]:
    """Получает текущий request_id из контекста."""
    return _request_id_var.get()


def get_user_id() -> Optional[str]:
    """Получает текущий user_id из контекста."""
    return _user_id_var.get()