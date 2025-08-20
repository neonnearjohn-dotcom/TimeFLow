from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional

PomodoroStatus = Literal["active", "done", "notified"]


@dataclass
class PomodoroSession:
    """Модель Pomodoro сессии в Firestore."""
    
    user_id: str
    status: PomodoroStatus
    ends_at: datetime  # UTC
    last_notified_at: Optional[datetime] = None
    version: int = 1  # для идемпотентности
    created_at: Optional[datetime] = None  # UTC
    updated_at: Optional[datetime] = None  # UTC
    
    def to_dict(self) -> dict:
        """Преобразование в dict для Firestore."""
        return {
            "user_id": self.user_id,
            "status": self.status,
            "ends_at": self.ends_at,
            "last_notified_at": self.last_notified_at,
            "version": self.version,
            "created_at": self.created_at or datetime.utcnow(),
            "updated_at": self.updated_at or datetime.utcnow(),
        }
    
    @classmethod
    def from_dict(cls, data: dict, session_id: str = None) -> "PomodoroSession":
        """Создание из dict Firestore."""
        session = cls(
            user_id=data["user_id"],
            status=data["status"],
            ends_at=data["ends_at"],
            last_notified_at=data.get("last_notified_at"),
            version=data.get("version", 1),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )
        if session_id:
            session.id = session_id
        return session