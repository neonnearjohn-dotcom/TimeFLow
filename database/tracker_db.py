"""
Функции для работы с привычками в Firestore
"""

from google.cloud import firestore
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, date
import logging
import uuid
from google.cloud.firestore import SERVER_TIMESTAMP

logger = logging.getLogger(__name__)


class TrackerDB:
    """Класс для работы с привычками в Firestore"""

    def __init__(self, db: firestore.Client):
        """
        Инициализация с существующим клиентом Firestore

        Args:
            db: Клиент Firestore
        """
        self.db = db

    # === ПОЛЕЗНЫЕ ПРИВЫЧКИ ===

    async def create_habit(self, telegram_id: int, habit_data: Dict[str, Any]) -> Optional[str]:
        """
        Создает новую привычку

        Args:
            telegram_id: ID пользователя
            habit_data: Данные привычки

        Returns:
            ID созданной привычки или None
        """
        try:

            habit_id = str(uuid.uuid4())
            habit_data["id"] = habit_id
            habit_data["created_at"] = datetime.utcnow()
            habit_data["current_streak"] = 0
            habit_data["best_streak"] = 0
            habit_data["total_completions"] = 0
            habit_data["last_completed"] = None

            # Сохраняем в подколлекцию habits пользователя
            user_ref = self.db.collection("users").document(str(telegram_id))
            user_ref.collection("habits").document(habit_id).set(habit_data)

            logger.info(f"Привычка {habit_id} создана для пользователя {telegram_id}")
            return habit_id
        except Exception as e:
            logger.error(f"Ошибка при создании привычки: {e}")
            return None

    async def get_user_habits(self, telegram_id: int) -> List[Dict[str, Any]]:
        """
        Получает все привычки пользователя

        Args:
            telegram_id: ID пользователя

        Returns:
            Список привычек
        """
        try:
            user_ref = self.db.collection("users").document(str(telegram_id))
            habits = user_ref.collection("habits").stream()

            habits_list = []
            for habit in habits:
                habit_data = habit.to_dict()
                habit_data["id"] = habit.id
                habits_list.append(habit_data)

            return sorted(habits_list, key=lambda x: x.get("created_at", datetime.min))
        except Exception as e:
            logger.error(f"Ошибка при получении привычек: {e}")
            return []

    async def get_habit(self, telegram_id: int, habit_id: str) -> Optional[Dict[str, Any]]:
        """
        Получает конкретную привычку
        """
        try:
            user_ref = self.db.collection("users").document(str(telegram_id))
            habit_doc = user_ref.collection("habits").document(habit_id).get()

            if habit_doc.exists:
                habit_data = habit_doc.to_dict()
                habit_data["id"] = habit_id
                return habit_data
            return None
        except Exception as e:
            logger.error(f"Ошибка при получении привычки: {e}")
            return None

    async def complete_habit(self, telegram_id: int, habit_id: str) -> Tuple[bool, int]:
        """
        Отмечает привычку как выполненную

        Returns:
            (success, new_streak)
        """
        try:
            user_ref = self.db.collection("users").document(str(telegram_id))
            habit_ref = user_ref.collection("habits").document(habit_id)

            # Получаем текущие данные привычки
            habit = habit_ref.get()
            if not habit.exists:
                return False, 0, 0

            habit_data = habit.to_dict()
            today = date.today()
            last_completed = habit_data.get("last_completed")

            # Проверяем, не выполнена ли уже сегодня
            if last_completed and last_completed.date() == today:
                # bugfix: возвращаем 3 значения
                return False, habit_data.get("current_streak", 0), habit_data.get("best_streak", 0)

            # Обновляем streak
            current_streak = habit_data.get("current_streak", 0)
            if last_completed:
                last_date = (
                    last_completed.date()
                    if isinstance(last_completed, datetime)
                    else last_completed
                )
                days_diff = (today - last_date).days

                if days_diff == 1:
                    # Продолжаем streak
                    current_streak += 1
                elif days_diff > 1:
                    # Streak сброшен
                    current_streak = 1
            else:
                # Первое выполнение
                current_streak = 1

            # Обновляем данные
            best_streak = max(current_streak, habit_data.get("best_streak", 0))
            total_completions = habit_data.get("total_completions", 0) + 1

            habit_ref.update(
                {
                    "last_completed": datetime.utcnow(),
                    "current_streak": current_streak,
                    "best_streak": best_streak,
                    "total_completions": total_completions,
                }
            )

            # Добавляем запись в историю
            habit_ref.collection("history").add(
                {"completed_at": datetime.utcnow(), "streak_at_time": current_streak}
            )

            return True, current_streak, best_streak
        except Exception as e:
            logger.error(f"Ошибка при выполнении привычки: {e}")
            return False, 0, 0

    async def delete_habit(self, telegram_id: int, habit_id: str) -> bool:
        """
        Удаляет привычку
        """
        try:
            user_ref = self.db.collection("users").document(str(telegram_id))
            habit_ref = user_ref.collection("habits").document(habit_id)

            # Удаляем историю
            history = habit_ref.collection("history").stream()
            for record in history:
                record.reference.delete()

            # Удаляем саму привычку
            habit_ref.delete()

            return True
        except Exception as e:
            logger.error(f"Ошибка при удалении привычки: {e}")
            return False

    async def is_habit_completed_today(self, telegram_id: int, habit_id: str) -> bool:
        """
        Проверяет, выполнена ли привычка сегодня
        """
        try:
            habit = await self.get_habit(telegram_id, habit_id)
            if not habit:
                return False

            last_completed = habit.get("last_completed")
            if not last_completed:
                return False

            last_date = (
                last_completed.date() if isinstance(last_completed, datetime) else last_completed
            )
            return last_date == date.today()
        except Exception as e:
            logger.error(f"Ошибка при проверке выполнения: {e}")
            return False

    # === ВРЕДНЫЕ ПРИВЫЧКИ ===

    async def create_bad_habit(self, telegram_id: int, habit_data: Dict[str, Any]) -> Optional[str]:
        """
        Создает вредную привычку для отслеживания воздержания
        """
        try:
            habit_id = str(uuid.uuid4())
            habit_data["id"] = habit_id
            habit_data["created_at"] = datetime.utcnow()
            habit_data["start_date"] = datetime.utcnow()
            habit_data["days_without"] = 0
            habit_data["best_streak"] = 0
            habit_data["total_resets"] = 0
            habit_data["last_reset"] = None

            user_ref = self.db.collection("users").document(str(telegram_id))
            user_ref.collection("bad_habits").document(habit_id).set(habit_data)

            return habit_id
        except Exception as e:
            logger.error(f"Ошибка при создании вредной привычки: {e}")
            return None

    async def get_user_bad_habits(self, telegram_id: int) -> List[Dict[str, Any]]:
        """
        Получает все вредные привычки пользователя
        """
        try:
            user_ref = self.db.collection("users").document(str(telegram_id))
            habits = user_ref.collection("bad_habits").stream()

            habits_list = []
            for habit in habits:
                habit_data = habit.to_dict()
                habit_data["id"] = habit.id

                # Вычисляем количество дней
                start_date = habit_data.get("start_date", datetime.utcnow())
                if habit_data.get("last_reset"):
                    start_date = habit_data["last_reset"]

                now = datetime.utcnow()
                if start_date.tzinfo is not None:
                    start_date = start_date.replace(tzinfo=None)
                days_without = (now - start_date).days

                days_without = (datetime.utcnow() - start_date).days
                habit_data["days_without"] = days_without

                habits_list.append(habit_data)

            return sorted(habits_list, key=lambda x: x.get("created_at", datetime.min))
        except Exception as e:
            logger.error(f"Ошибка при получении вредных привычек: {e}")
            return []

    async def get_bad_habit(self, telegram_id: int, habit_id: str) -> Optional[Dict[str, Any]]:
        """
        Получает конкретную вредную привычку
        """
        try:
            user_ref = self.db.collection("users").document(str(telegram_id))
            habit_doc = user_ref.collection("bad_habits").document(habit_id).get()

            if habit_doc.exists:
                habit_data = habit_doc.to_dict()
                habit_data["id"] = habit_id

                # Вычисляем количество дней
                start_date = habit_data.get("start_date", datetime.utcnow())
                if habit_data.get("last_reset"):
                    start_date = habit_data["last_reset"]

                now = datetime.utcnow()
                if start_date.tzinfo is not None:
                    start_date = start_date.replace(tzinfo=None)
                days_without = (now - start_date).days

                days_without = (datetime.utcnow() - start_date).days
                habit_data["days_without"] = days_without

                return habit_data
            return None
        except Exception as e:
            logger.error(f"Ошибка при получении вредной привычки: {e}")
            return None

    async def reset_bad_habit(self, telegram_id: int, habit_id: str) -> Tuple[bool, int]:
        """
        Сбрасывает счетчик воздержания

        Returns:
            (success, days_lost)
        """
        try:
            user_ref = self.db.collection("users").document(str(telegram_id))
            habit_ref = user_ref.collection("bad_habits").document(habit_id)

            habit = habit_ref.get()
            if not habit.exists:
                return False, 0

            habit_data = habit.to_dict()

            # Вычисляем потерянные дни
            start_date = habit_data.get("start_date", datetime.utcnow())
            if habit_data.get("last_reset"):
                start_date = habit_data["last_reset"]

            now = datetime.utcnow()
            if start_date.tzinfo is not None:
                start_date = start_date.replace(tzinfo=None)
            days_lost = (now - start_date).days

            days_lost = (datetime.utcnow() - start_date).days

            # Обновляем best_streak если нужно
            best_streak = max(days_lost, habit_data.get("best_streak", 0))

            # Сбрасываем счетчик
            habit_ref.update(
                {
                    "last_reset": datetime.utcnow(),
                    "best_streak": best_streak,
                    "total_resets": habit_data.get("total_resets", 0) + 1,
                }
            )

            # Добавляем запись в историю
            habit_ref.collection("resets").add(
                {"reset_at": datetime.utcnow(), "days_lost": days_lost}
            )

            return True, days_lost
        except Exception as e:
            logger.error(f"Ошибка при сбросе счетчика: {e}")
            return False, 0

    async def delete_bad_habit(self, telegram_id: int, habit_id: str) -> bool:
        """
        Удаляет вредную привычку
        """
        try:
            user_ref = self.db.collection("users").document(str(telegram_id))
            habit_ref = user_ref.collection("bad_habits").document(habit_id)

            # Удаляем историю сбросов
            resets = habit_ref.collection("resets").stream()
            for reset in resets:
                reset.reference.delete()

            # Удаляем привычку
            habit_ref.delete()

            return True
        except Exception as e:
            logger.error(f"Ошибка при удалении вредной привычки: {e}")
            return False
