import asyncio
from datetime import datetime
from typing import Awaitable, Callable, List, Optional

from google.cloud import firestore
from google.cloud.firestore_v1.transaction import Transaction

from models.pomodoro import PomodoroSession, PomodoroStatus
from utils.logging import get_logger, get_request_id

logger = get_logger(__name__)


class PomodoroService:
    """Сервис для работы с Pomodoro сессиями."""

    def __init__(self, db: firestore.Client):
        self.db = db
        self.collection_name = "pomodoro_sessions"

    async def create_session(
        self,
        user_id: str,
        ends_at: datetime,
        status: PomodoroStatus = "active",
    ) -> str:
        """Создаёт новую Pomodoro сессию."""
        session = PomodoroSession(
            user_id=user_id,
            status=status,
            ends_at=ends_at,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            version=1,
        )

        await asyncio.to_thread(
            self.db.collection(self.collection_name)
            .document(f"{user_id}_{int(ends_at.timestamp())}")
            .set,
            session.to_dict(),
        )

        session_id = f"{user_id}_{int(ends_at.timestamp())}"
        logger.info(
            "Pomodoro session created",
            extra={
                "session_id": session_id,
                "user_id": user_id,
                "ends_at": ends_at.isoformat(),
                "request_id": get_request_id(),
            },
        )
        return session_id

    async def fetch_expired_active(self, limit: int = 100) -> List[tuple[str, PomodoroSession]]:
        """Получает активные просроченные сессии."""
        now = datetime.utcnow()

        docs = await asyncio.to_thread(
            lambda: list(
                self.db.collection(self.collection_name)
                .where("status", "==", "active")
                .where("ends_at", "<=", now)
                .limit(limit)
                .stream()
            )
        )

        sessions = []
        for doc in docs:
            session_id = doc.id
            session = PomodoroSession.from_dict(doc.to_dict(), session_id)
            sessions.append((session_id, session))

        logger.info(
            "Fetched expired sessions",
            extra={
                "count": len(sessions),
                "limit": limit,
                "request_id": get_request_id(),
            },
        )
        return sessions

    async def mark_done_and_notify(
        self,
        session_id: str,
        notify: Callable[[str, str], Awaitable[None]],
    ) -> bool:
        """Помечает просроченную сессию как завершённую и уведомляет пользователя."""

        doc_ref = self.db.collection(self.collection_name).document(session_id)

        @firestore.transactional
        def lock_session(transaction: Transaction) -> tuple[bool, Optional[str]]:
            doc = doc_ref.get(transaction=transaction)
            if not doc.exists:
                return False, None

            data = doc.to_dict()
            now = datetime.utcnow()
            if data["status"] != "active" or data["ends_at"] > now:
                logger.info(
                    "Session skip",
                    extra={
                        "session_id": session_id,
                        "status": data["status"],
                        "reason": "not active or not expired",
                        "request_id": get_request_id(),
                    },
                )
                return False, None

            transaction.update(
                doc_ref,
                {
                    "status": "done",
                    "version": data["version"] + 1,
                    "updated_at": now,
                },
            )
            return True, data["user_id"]

        try:
            should_notify, user_id = await asyncio.to_thread(
                lock_session,
                self.db.transaction(),
            )
            if not should_notify or not user_id:
                return False

            try:
                await notify(
                    user_id,
                    "⏰ Pomodoro сессия завершена! Время для перерыва.",
                )
            except Exception as e:
                logger.error(
                    "Notification failed",
                    extra={
                        "session_id": session_id,
                        "user_id": user_id,
                        "error": str(e),
                        "request_id": get_request_id(),
                    },
                )
                await asyncio.to_thread(
                    doc_ref.update,
                    {
                        "status": "active",
                        "updated_at": datetime.utcnow(),
                    },
                )
                return False

            await asyncio.to_thread(
                doc_ref.update,
                {
                    "status": "notified",
                    "last_notified_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                },
            )
            logger.info(
                "Pomodoro notification sent",
                extra={
                    "session_id": session_id,
                    "user_id": user_id,
                    "request_id": get_request_id(),
                },
            )
            return True

        except Exception as e:
            logger.error(
                "Failed to mark session done",
                extra={
                    "session_id": session_id,
                    "error": str(e),
                    "request_id": get_request_id(),
                },
            )
            return False
