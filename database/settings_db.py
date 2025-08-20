"""
База данных для настроек пользователей
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class SettingsDB:
    """Класс для работы с настройками пользователей в Firestore"""

    DEFAULT_SETTINGS = {"notifications_enabled": True, "theme": "system"}

    VALID_THEMES = ["system", "light", "dark"]

    def __init__(self, db):
        """
        Инициализация с существующим Firestore клиентом

        Args:
            db: Firestore database instance
        """
        self.db = db

    def get_settings(self, telegram_id: str) -> Dict[str, Any]:
        """
        Получить настройки пользователя

        Args:
            telegram_id: Telegram ID пользователя

        Returns:
            Словарь с настройками (с дефолтными значениями если документа нет)
        """
        try:
            doc_ref = (
                self.db.collection("users")
                .document(telegram_id)
                .collection("settings")
                .document("main")
            )
            doc = doc_ref.get()

            if doc.exists:
                settings = doc.to_dict()
                # Проверяем наличие всех полей
                for key, default_value in self.DEFAULT_SETTINGS.items():
                    if key not in settings:
                        settings[key] = default_value
                return settings
            else:
                # Создаем документ с дефолтными настройками
                settings = self.DEFAULT_SETTINGS.copy()
                settings["updated_at"] = datetime.now()
                doc_ref.set(settings)
                logger.info(f"Создан документ настроек для пользователя {telegram_id}")
                return settings

        except Exception as e:
            logger.error(f"Ошибка получения настроек для {telegram_id}: {e}", exc_info=True)
            # Возвращаем дефолтные настройки в случае ошибки
            return self.DEFAULT_SETTINGS.copy()

    def update_settings(self, telegram_id: str, partial: Dict[str, Any]) -> Dict[str, Any]:
        """
        Обновить настройки пользователя

        Args:
            telegram_id: Telegram ID пользователя
            partial: Частичный словарь с обновляемыми полями

        Returns:
            Обновленные настройки

        Raises:
            ValueError: Если передано невалидное значение
        """
        try:
            # Валидация theme если передана
            if "theme" in partial and partial["theme"] not in self.VALID_THEMES:
                raise ValueError(f"Недопустимое значение темы: {partial['theme']}")

            # Валидация notifications_enabled
            if "notifications_enabled" in partial and not isinstance(
                partial["notifications_enabled"], bool
            ):
                raise ValueError(
                    f"notifications_enabled должно быть bool, получено: {type(partial['notifications_enabled'])}"
                )

            # Добавляем timestamp
            partial["updated_at"] = datetime.now()

            # Обновляем документ
            doc_ref = (
                self.db.collection("users")
                .document(telegram_id)
                .collection("settings")
                .document("main")
            )

            # Проверяем существование документа
            doc = doc_ref.get()
            if not doc.exists:
                # Создаем новый документ с дефолтными значениями + обновления
                settings = self.DEFAULT_SETTINGS.copy()
                settings.update(partial)
                doc_ref.set(settings)
                logger.info(f"Создан и обновлен документ настроек для пользователя {telegram_id}")
            else:
                # Обновляем существующий
                doc_ref.update(partial)
                logger.info(
                    f"Обновлены настройки для пользователя {telegram_id}: {list(partial.keys())}"
                )

            # Возвращаем актуальные настройки
            return self.get_settings(telegram_id)

        except ValueError as e:
            logger.error(f"Ошибка валидации настроек: {e}")
            raise
        except Exception as e:
            logger.error(f"Ошибка обновления настроек для {telegram_id}: {e}", exc_info=True)
            raise

    def toggle_notifications(self, telegram_id: str) -> bool:
        """
        Переключить уведомления вкл/выкл

        Args:
            telegram_id: Telegram ID пользователя

        Returns:
            Новое значение notifications_enabled
        """
        try:
            current_settings = self.get_settings(telegram_id)
            new_value = not current_settings.get("notifications_enabled", True)

            self.update_settings(telegram_id, {"notifications_enabled": new_value})
            return new_value

        except Exception as e:
            logger.error(f"Ошибка переключения уведомлений для {telegram_id}: {e}", exc_info=True)
            raise
