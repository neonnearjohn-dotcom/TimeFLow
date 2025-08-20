"""
База данных для модуля ИИ-ассистента
"""

from typing import Dict, List, Optional
from datetime import datetime, timezone, timedelta
import logging
from google.cloud import firestore

logger = logging.getLogger(__name__)


class AssistantDB:
    """Класс для работы с данными ИИ-ассистента в Firestore"""

    def __init__(self, db):
        """
        Инициализация с подключением к Firestore

        Args:
            db: Экземпляр Firestore Client
        """
        self.db = db
        self.collection_name = "users"

    async def save_message(
        self, user_id: int, user_message: str, assistant_response: str, tokens_used: int = 0
    ) -> bool:
        """
        Сохраняет сообщение и ответ в историю

        Args:
            user_id: ID пользователя
            user_message: Сообщение пользователя
            assistant_response: Ответ ассистента
            tokens_used: Количество использованных токенов

        Returns:
            bool: Успешность сохранения
        """
        try:
            user_ref = self.db.collection(self.collection_name).document(str(user_id))

            message_data = {
                "user_message": user_message,
                "assistant_response": assistant_response,
                "tokens_used": tokens_used,
                "timestamp": datetime.now(timezone.utc),
                "created_at": datetime.now(timezone.utc),
            }

            # Сохраняем в подколлекцию chat_history
            user_ref.collection("chat_history").add(message_data)

            # Обновляем статистику
            stats_data = {
                "total_messages": firestore.Increment(1),
                "total_tokens": firestore.Increment(tokens_used),
                "last_interaction": datetime.now(timezone.utc),
            }

            user_ref.set({"assistant_stats": stats_data}, merge=True)

            return True
        except Exception as e:
            logger.error(f"Ошибка при сохранении сообщения: {e}")
            return False

    async def add_message(
        self, user_id: int, role: str, content: str, scenario: str = None
    ) -> bool:
        """
        Добавляет сообщение в историю чата

        Args:
            user_id: ID пользователя
            role: Роль (user/assistant)
            content: Содержание сообщения
            scenario: Название сценария (опционально)

        Returns:
            bool: Успешность сохранения
        """
        try:
            user_ref = self.db.collection(self.collection_name).document(str(user_id))

            message_data = {
                "role": role,
                "content": content,
                "timestamp": datetime.now(timezone.utc),
                "created_at": datetime.now(timezone.utc),
            }

            if scenario:
                message_data["scenario"] = scenario

            # Сохраняем в подколлекцию chat_history
            user_ref.collection("chat_history").add(message_data)

            # Обновляем статистику
            if role == "assistant":
                stats_data = {
                    "total_messages": firestore.Increment(1),
                    "last_interaction": datetime.now(timezone.utc),
                }

                user_ref.set({"assistant_stats": stats_data}, merge=True)

            return True
        except Exception as e:
            logger.error(f"Ошибка при добавлении сообщения: {e}")
            return False

    async def get_chat_history(self, user_id: int, limit: int = 10) -> List[Dict]:
        """
        Получает историю сообщений пользователя

        Args:
            user_id: ID пользователя
            limit: Максимальное количество сообщений

        Returns:
            List[Dict]: История сообщений
        """
        try:
            user_ref = self.db.collection(self.collection_name).document(str(user_id))

            # Получаем последние сообщения
            messages = (
                user_ref.collection("chat_history")
                .order_by("timestamp", direction=firestore.Query.DESCENDING)
                .limit(limit)
                .get()
            )

            history = []
            for msg in messages:
                data = msg.to_dict()
                # Приводим к единому формату
                message = {
                    "role": data.get("role", "user"),
                    "content": data.get(
                        "content",
                        data.get("user_message", "") or data.get("assistant_response", ""),
                    ),
                    "timestamp": data.get("timestamp", data.get("created_at")),
                }
                if "scenario" in data:
                    message["scenario"] = data["scenario"]
                history.append(message)

            # Возвращаем в хронологическом порядке
            return list(reversed(history))
        except Exception as e:
            logger.error(f"Ошибка при получении истории: {e}")
            return []

    async def get_user_context(self, user_id: int, messages_count: int = 5) -> str:
        """
        Получает контекст последних сообщений для ИИ

        Args:
            user_id: ID пользователя
            messages_count: Количество сообщений для контекста

        Returns:
            str: Контекст в виде строки
        """
        try:
            history = await self.get_chat_history(user_id, messages_count)

            if not history:
                return ""

            context_parts = []
            for msg in history:
                context_parts.append(f"User: {msg.get('user_message', '')}")
                context_parts.append(f"Assistant: {msg.get('assistant_response', '')}")

            return "\n".join(context_parts)
        except Exception as e:
            logger.error(f"Ошибка при получении контекста: {e}")
            return ""

    async def get_user_stats(self, user_id: int) -> Dict:
        """
        Получает статистику использования ассистента

        Args:
            user_id: ID пользователя

        Returns:
            Dict: Статистика пользователя
        """
        try:
            user_ref = self.db.collection(self.collection_name).document(str(user_id))
            doc = user_ref.get()

            if not doc.exists:
                return {
                    "total_messages": 0,
                    "total_tokens": 0,
                    "scenarios_used": 0,
                    "points_earned": 0,
                    "favorite_scenarios": {},
                }

            data = doc.to_dict()
            stats = data.get("assistant_stats", {})

            # Подсчитываем использованные сценарии
            scenarios = await self._count_scenarios(user_id)
            stats["scenarios_used"] = scenarios["total"]
            stats["favorite_scenarios"] = scenarios["by_type"]

            # Подсчитываем заработанные очки
            stats["points_earned"] = stats.get("total_messages", 0) * 3

            return stats
        except Exception as e:
            logger.error(f"Ошибка при получении статистики: {e}")
            return {
                "total_messages": 0,
                "total_tokens": 0,
                "scenarios_used": 0,
                "points_earned": 0,
                "favorite_scenarios": {},
            }

    async def _count_scenarios(self, user_id: int) -> Dict:
        """
        Подсчитывает использованные сценарии

        Args:
            user_id: ID пользователя

        Returns:
            Dict: Количество сценариев по типам
        """
        try:
            user_ref = self.db.collection(self.collection_name).document(str(user_id))
            messages = user_ref.collection("chat_history").get()

            scenario_count = {}
            total = 0

            for msg in messages:
                data = msg.to_dict()
                user_msg = data.get("user_message", "")

                if user_msg.startswith("Сценарий:"):
                    scenario = user_msg.split(":")[1].strip()
                    scenario_count[scenario] = scenario_count.get(scenario, 0) + 1
                    total += 1

            return {"total": total, "by_type": scenario_count}
        except Exception as e:
            logger.error(f"Ошибка при подсчете сценариев: {e}")
            return {"total": 0, "by_type": {}}

    async def get_session_stats(self, user_id: int) -> Dict:
        """
        Получает статистику текущей сессии

        Args:
            user_id: ID пользователя

        Returns:
            Dict: Статистика сессии
        """
        try:
            # Получаем сообщения за последний час
            hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)

            user_ref = self.db.collection(self.collection_name).document(str(user_id))
            messages = user_ref.collection("chat_history").where("timestamp", ">=", hour_ago).get()

            messages_count = len(list(messages))
            points_earned = messages_count * 3  # 3 очка за сообщение

            return {"messages_count": messages_count, "points_earned": points_earned}
        except Exception as e:
            logger.error(f"Ошибка при получении статистики сессии: {e}")
            return {"messages_count": 0, "points_earned": 0}

    async def clear_history(self, user_id: int) -> bool:
        """
        Очищает историю чата пользователя

        Args:
            user_id: ID пользователя

        Returns:
            bool: Успешность очистки
        """
        try:
            user_ref = self.db.collection(self.collection_name).document(str(user_id))

            # Получаем все сообщения
            messages = user_ref.collection("chat_history").get()

            # Удаляем каждое сообщение
            for msg in messages:
                msg.reference.delete()

            # Обнуляем статистику
            user_ref.set(
                {
                    "assistant_stats": {
                        "total_messages": 0,
                        "total_tokens": 0,
                        "last_interaction": datetime.now(timezone.utc),
                    }
                },
                merge=True,
            )

            return True
        except Exception as e:
            logger.error(f"Ошибка при очистке истории: {e}")
            return False

    async def get_last_use_date(self, user_id: int) -> Optional[datetime]:
        """
        Получает дату последнего использования ассистента

        Args:
            user_id: ID пользователя

        Returns:
            Optional[datetime]: Дата последнего использования
        """
        try:
            user_ref = self.db.collection(self.collection_name).document(str(user_id))
            doc = user_ref.get()

            if doc.exists:
                data = doc.to_dict()
                stats = data.get("assistant_stats", {})
                return stats.get("last_interaction")

            return None
        except Exception as e:
            logger.error(f"Ошибка при получении даты последнего использования: {e}")
            return None

    async def update_last_use_date(self, user_id: int) -> bool:
        """
        Обновляет дату последнего использования

        Args:
            user_id: ID пользователя

        Returns:
            bool: Успешность обновления
        """
        try:
            user_ref = self.db.collection(self.collection_name).document(str(user_id))

            user_ref.set(
                {"assistant_stats": {"last_interaction": datetime.now(timezone.utc)}}, merge=True
            )

            return True
        except Exception as e:
            logger.error(f"Ошибка при обновлении даты последнего использования: {e}")
            return False

    async def clear_history(self, user_id: int) -> bool:
        """
        Очищает историю чата пользователя

        Args:
            user_id: ID пользователя

        Returns:
            bool: Успешность очистки
        """
        try:
            user_ref = self.db.collection(self.collection_name).document(str(user_id))

            # Получаем все сообщения
            messages = user_ref.collection("chat_history").get()

            # Удаляем каждое сообщение
            for msg in messages:
                msg.reference.delete()

            # Обнуляем статистику
            user_ref.set(
                {
                    "assistant_stats": {
                        "total_messages": 0,
                        "total_tokens": 0,
                        "last_interaction": datetime.now(timezone.utc),
                    }
                },
                merge=True,
            )

            return True
        except Exception as e:
            logger.error(f"Ошибка при очистке истории: {e}")
            return False

    async def get_last_use_date(self, user_id: int) -> Optional[datetime]:
        """
        Получает дату последнего использования ассистента

        Args:
            user_id: ID пользователя

        Returns:
            Optional[datetime]: Дата последнего использования
        """
        try:
            user_ref = self.db.collection(self.collection_name).document(str(user_id))
            doc = user_ref.get()

            if doc.exists:
                data = doc.to_dict()
                stats = data.get("assistant_stats", {})
                return stats.get("last_interaction")

            return None
        except Exception as e:
            logger.error(f"Ошибка при получении даты последнего использования: {e}")
            return None

    async def update_last_use_date(self, user_id: int) -> bool:
        """
        Обновляет дату последнего использования

        Args:
            user_id: ID пользователя

        Returns:
            bool: Успешность обновления
        """
        try:
            user_ref = self.db.collection(self.collection_name).document(str(user_id))

            user_ref.set(
                {"assistant_stats": {"last_interaction": datetime.now(timezone.utc)}}, merge=True
            )

            return True
        except Exception as e:
            logger.error(f"Ошибка при обновлении даты последнего использования: {e}")
            return False
