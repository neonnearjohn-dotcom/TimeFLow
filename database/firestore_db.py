"""
Модуль для работы с Firestore
"""

from google.cloud import firestore
from typing import Dict, Optional, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def is_connected(self) -> bool:
    """Проверка подключения к БД"""
    return self.db is not None


def get_client(self):
    """Получить клиент Firestore"""
    return self.db


class FirestoreDB:
    """Класс для работы с Firestore"""

    def __init__(self, project_id: Optional[str] = None):
        """
        Инициализация клиента Firestore

        Args:
            project_id: ID проекта в Google Cloud (опционально)
        """
        self.db = firestore.Client(project=project_id)
        self.users_collection = "users"

    async def user_exists(self, telegram_id: int) -> bool:
        """
        Проверяет, существует ли пользователь в базе

        Args:
            telegram_id: Telegram ID пользователя

        Returns:
            True если пользователь существует, False если нет
        """
        try:
            doc_ref = self.db.collection(self.users_collection).document(str(telegram_id))
            doc = doc_ref.get()
            return doc.exists
        except Exception as e:
            logger.error(f"Ошибка при проверке пользователя {telegram_id}: {e}")
            return False

    async def create_user(self, telegram_id: int, user_data: Dict[str, Any]) -> bool:
        """
        Создает нового пользователя в базе

        Args:
            telegram_id: Telegram ID пользователя
            user_data: Данные пользователя для сохранения

        Returns:
            True если пользователь успешно создан, False в случае ошибки
        """
        try:
            # Добавляем служебные поля
            user_data["telegram_id"] = telegram_id
            user_data["created_at"] = datetime.utcnow()
            user_data["updated_at"] = datetime.utcnow()

            # Сохраняем в Firestore
            doc_ref = self.db.collection(self.users_collection).document(str(telegram_id))
            doc_ref.set(user_data)

            logger.info(f"Пользователь {telegram_id} успешно создан")
            return True
        except Exception as e:
            logger.error(f"Ошибка при создании пользователя {telegram_id}: {e}")
            return False

    async def get_user(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """
        Получает данные пользователя из базы

        Args:
            telegram_id: Telegram ID пользователя

        Returns:
            Словарь с данными пользователя или None если не найден
        """
        try:
            doc_ref = self.db.collection(self.users_collection).document(str(telegram_id))
            doc = doc_ref.get()

            if doc.exists:
                return doc.to_dict()
            return None
        except Exception as e:
            logger.error(f"Ошибка при получении пользователя {telegram_id}: {e}")
            return None

    async def update_user(self, telegram_id: int, update_data: Dict[str, Any]) -> bool:
        """
        Обновляет данные пользователя

        Args:
            telegram_id: Telegram ID пользователя
            update_data: Данные для обновления

        Returns:
            True если обновление успешно, False в случае ошибки
        """
        try:
            # Добавляем время обновления
            update_data["updated_at"] = datetime.utcnow()

            doc_ref = self.db.collection(self.users_collection).document(str(telegram_id))
            doc_ref.update(update_data)

            logger.info(f"Данные пользователя {telegram_id} обновлены")
            return True
        except Exception as e:
            logger.error(f"Ошибка при обновлении пользователя {telegram_id}: {e}")
            return False

    async def save_onboarding_answers(self, telegram_id: int, answers: Dict[str, str]) -> bool:
        """
        Сохраняет ответы пользователя из начального опроса

        Args:
            telegram_id: Telegram ID пользователя
            answers: Словарь с ответами на вопросы

        Returns:
            True если сохранение успешно, False в случае ошибки
        """
        try:
            update_data = {
                "onboarding_completed": True,
                "onboarding_answers": answers,
                "onboarding_completed_at": datetime.utcnow(),
            }

            return await self.update_user(telegram_id, update_data)
        except Exception as e:
            logger.error(f"Ошибка при сохранении ответов опроса для {telegram_id}: {e}")
            return False
