"""
База данных для работы с профилями ИИ-ассистента
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import logging
from google.cloud import firestore
from google.cloud.firestore_v1 import FieldFilter

# Импорт моделей - избегаем циклических импортов
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.ai_profile import (
    AIProfile, 
    CategoryType,
    OnboardingData,
    PlanData,
    ConstraintsData,
    ProgressData,
    PreferencesData
)

logger = logging.getLogger(__name__)


class AssistantProfileDB:
    """Класс для работы с профилями ИИ-ассистента в Firestore"""
    
    def __init__(self, db: firestore.Client):
        """
        Инициализация с подключением к Firestore
        
        Args:
            db: Экземпляр Firestore Client
        """
        self.db = db
        self.collection_name = 'users'
        logger.info("AssistantProfileDB инициализирована")
    
    async def get_profile(self, telegram_id: int) -> Optional[AIProfile]:
        """
        Получает профиль ИИ-ассистента пользователя
        
        Args:
            telegram_id: ID пользователя в Telegram
            
        Returns:
            AIProfile или None если профиль не найден
        """
        try:
            user_ref = self.db.collection(self.collection_name).document(str(telegram_id))
            doc = user_ref.get()
            
            if not doc.exists:
                logger.info(f"Профиль для пользователя {telegram_id} не найден")
                return None
            
            data = doc.to_dict()
            ai_profile_data = data.get('ai_profile')
            
            if not ai_profile_data:
                logger.info(f"AI профиль отсутствует для пользователя {telegram_id}")
                return None
            
            # Преобразуем данные из Firestore в модель
            profile = AIProfile.from_firestore(ai_profile_data)
            logger.info(f"Профиль пользователя {telegram_id} успешно загружен")
            
            return profile
            
        except Exception as e:
            logger.error(f"Ошибка при получении профиля для {telegram_id}: {e}")
            return None
    
    async def save_onboarding_answer(
        self, 
        telegram_id: int, 
        qid: str, 
        answer: Any
    ) -> bool:
        """
        Сохраняет ответ на вопрос онбординга
        
        Args:
            telegram_id: ID пользователя
            qid: ID вопроса
            answer: Ответ на вопрос
            
        Returns:
            bool: Успешность сохранения
        """
        try:
            user_ref = self.db.collection(self.collection_name).document(str(telegram_id))
            
            # Проверяем существование профиля
            doc = user_ref.get()
            if not doc.exists:
                # Создаем новый профиль с пустым онбордингом
                initial_profile = AIProfile()
                user_ref.set({
                    'ai_profile': initial_profile.to_firestore(),
                    'updated_at': datetime.now(timezone.utc)
                })
            
            # Обновляем ответ в онбординге
            user_ref.update({
                f'ai_profile.onboarding.answers.{qid}': answer,
                'ai_profile.updated_at': datetime.now(timezone.utc),
                'updated_at': datetime.now(timezone.utc)
            })
            
            logger.info(f"Ответ {qid} сохранен для пользователя {telegram_id}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при сохранении ответа онбординга: {e}")
            return False
    
    async def finalize_onboarding(
        self,
        telegram_id: int,
        category: str,
        answers: Dict[str, Any],
        constraints: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Завершает онбординг и сохраняет финальные данные
        
        Args:
            telegram_id: ID пользователя
            category: Выбранная категория
            answers: Все ответы онбординга
            constraints: Ограничения пользователя
            
        Returns:
            bool: Успешность завершения
        """
        try:
            user_ref = self.db.collection(self.collection_name).document(str(telegram_id))
            
            # Подготавливаем данные онбординга
            onboarding_data = {
                'completed': True,
                'answers': answers,
                'completed_at': datetime.now(timezone.utc)
            }
            
            # Подготавливаем обновление
            update_data = {
                'ai_profile.active_category': category,
                'ai_profile.onboarding': onboarding_data,
                'ai_profile.updated_at': datetime.now(timezone.utc),
                'updated_at': datetime.now(timezone.utc)
            }
            
            # Добавляем ограничения если они есть
            if constraints:
                # Определяем поле для специфичных ограничений
                constraint_field = f'{category}_constraints'
                update_data['ai_profile.constraints.daily_time_minutes'] = constraints.get('daily_time_minutes', 60)
                update_data['ai_profile.constraints.working_days'] = constraints.get('working_days', [1,2,3,4,5])
                update_data[f'ai_profile.constraints.{constraint_field}'] = constraints
            
            # Обновляем документ
            user_ref.update(update_data)
            
            logger.info(f"Онбординг завершен для пользователя {telegram_id}, категория: {category}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при завершении онбординга: {e}")
            return False
    
    async def save_plan(
        self,
        telegram_id: int,
        plan: Dict[str, Any]
    ) -> bool:
        """
        Сохраняет план пользователя
        
        Args:
            telegram_id: ID пользователя
            plan: Данные плана (может быть dict или PlanData)
            
        Returns:
            bool: Успешность сохранения
        """
        try:
            user_ref = self.db.collection(self.collection_name).document(str(telegram_id))
            
            # Преобразуем план в словарь если это модель
            if hasattr(plan, 'dict'):
                plan_data = plan.dict()
            else:
                plan_data = plan
            
            # Добавляем временные метки
            plan_data['created_at'] = datetime.now(timezone.utc)
            plan_data['updated_at'] = datetime.now(timezone.utc)
            
            # Обновляем план и сбрасываем прогресс
            update_data = {
                'ai_profile.plan': plan_data,
                'ai_profile.progress': {
                    'days_done': 0,
                    'last_checkin': None,
                    'fail_reasons': [],
                    'streak_current': 0,
                    'streak_best': 0,
                    'completion_rate': 0.0
                },
                'ai_profile.updated_at': datetime.now(timezone.utc),
                'updated_at': datetime.now(timezone.utc)
            }
            
            user_ref.update(update_data)
            
            logger.info(f"План сохранен для пользователя {telegram_id}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при сохранении плана: {e}")
            return False
    
    async def delete_plan(self, telegram_id: int) -> bool:
        """
        Удаляет план пользователя
        
        Args:
            telegram_id: ID пользователя
            
        Returns:
            bool: Успешность удаления
        """
        try:
            user_ref = self.db.collection(self.collection_name).document(str(telegram_id))
            
            # Проверяем существование документа
            doc = user_ref.get()
            if not doc.exists:
                logger.warning(f"Документ пользователя {telegram_id} не найден")
                return False
            
            # Удаляем план и сбрасываем прогресс
            update_data = {
                'ai_profile.plan': None,
                'ai_profile.progress': {
                    'days_done': 0,
                    'last_checkin': None,
                    'fail_reasons': [],
                    'streak_current': 0,
                    'streak_best': 0,
                    'completion_rate': 0.0
                },
                'ai_profile.updated_at': datetime.now(timezone.utc),
                'updated_at': datetime.now(timezone.utc)
            }
            
            user_ref.update(update_data)
            
            logger.info(f"План удален для пользователя {telegram_id}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при удалении плана: {e}")
            return False
    
    async def update_progress(
        self,
        telegram_id: int,
        patch: Dict[str, Any]
    ) -> bool:
        """
        Обновляет прогресс пользователя (частичное обновление)
        
        Args:
            telegram_id: ID пользователя
            patch: Словарь с полями для обновления
            
        Returns:
            bool: Успешность обновления
        """
        try:
            user_ref = self.db.collection(self.collection_name).document(str(telegram_id))
            
            # Проверяем существование документа
            doc = user_ref.get()
            if not doc.exists:
                logger.warning(f"Документ пользователя {telegram_id} не найден")
                return False
            
            # Подготавливаем обновление с префиксом ai_profile.progress
            update_data = {}
            for key, value in patch.items():
                # Обрабатываем специальные случаи
                if key == 'increment_days_done':
                    update_data['ai_profile.progress.days_done'] = firestore.Increment(value)
                elif key == 'increment_streak':
                    update_data['ai_profile.progress.streak_current'] = firestore.Increment(value)
                elif key == 'add_fail_reason':
                    update_data['ai_profile.progress.fail_reasons'] = firestore.ArrayUnion([value])
                else:
                    # Обычное обновление поля
                    update_data[f'ai_profile.progress.{key}'] = value
            
            # Добавляем временные метки
            update_data['ai_profile.progress.last_checkin'] = datetime.now(timezone.utc)
            update_data['ai_profile.updated_at'] = datetime.now(timezone.utc)
            update_data['updated_at'] = datetime.now(timezone.utc)
            
            # Выполняем обновление
            user_ref.update(update_data)
            
            logger.info(f"Прогресс обновлен для пользователя {telegram_id}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при обновлении прогресса: {e}")
            return False
    
    # Дополнительные полезные методы
    
    async def create_profile(self, telegram_id: int) -> bool:
        """
        Создает новый пустой профиль для пользователя
        
        Args:
            telegram_id: ID пользователя
            
        Returns:
            bool: Успешность создания
        """
        try:
            user_ref = self.db.collection(self.collection_name).document(str(telegram_id))
            
            # Создаем пустой профиль
            profile = AIProfile()
            
            # Сохраняем или обновляем
            user_ref.set({
                'ai_profile': profile.to_firestore(),
                'created_at': datetime.now(timezone.utc),
                'updated_at': datetime.now(timezone.utc)
            }, merge=True)
            
            logger.info(f"Создан новый AI профиль для пользователя {telegram_id}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при создании профиля: {e}")
            return False
    
    async def update_preferences(
        self,
        telegram_id: int,
        preferences: Dict[str, Any]
    ) -> bool:
        """
        Обновляет предпочтения пользователя
        
        Args:
            telegram_id: ID пользователя
            preferences: Словарь с предпочтениями
            
        Returns:
            bool: Успешность обновления
        """
        try:
            user_ref = self.db.collection(self.collection_name).document(str(telegram_id))
            
            # Подготавливаем обновление
            update_data = {}
            for key, value in preferences.items():
                update_data[f'ai_profile.preferences.{key}'] = value
            
            update_data['ai_profile.updated_at'] = datetime.now(timezone.utc)
            update_data['updated_at'] = datetime.now(timezone.utc)
            
            user_ref.update(update_data)
            
            logger.info(f"Предпочтения обновлены для пользователя {telegram_id}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при обновлении предпочтений: {e}")
            return False
    
    async def add_risk(
        self,
        telegram_id: int,
        risk: Dict[str, Any]
    ) -> bool:
        """
        Добавляет новый риск в профиль
        
        Args:
            telegram_id: ID пользователя
            risk: Данные риска
            
        Returns:
            bool: Успешность добавления
        """
        try:
            user_ref = self.db.collection(self.collection_name).document(str(telegram_id))
            
            # Добавляем риск в массив
            user_ref.update({
                'ai_profile.risks': firestore.ArrayUnion([risk]),
                'ai_profile.updated_at': datetime.now(timezone.utc),
                'updated_at': datetime.now(timezone.utc)
            })
            
            logger.info(f"Риск добавлен для пользователя {telegram_id}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при добавлении риска: {e}")
            return False
    
    async def update_task_status(
        self,
        telegram_id: int,
        task_id: str,
        status: str,
        notes: Optional[str] = None
    ) -> bool:
        """
        Обновляет статус конкретной задачи в плане
        
        Args:
            telegram_id: ID пользователя
            task_id: ID задачи
            status: Новый статус
            notes: Заметки (опционально)
            
        Returns:
            bool: Успешность обновления
        """
        try:
            user_ref = self.db.collection(self.collection_name).document(str(telegram_id))
            doc = user_ref.get()
            
            if not doc.exists:
                return False
            
            data = doc.to_dict()
            ai_profile = data.get('ai_profile', {})
            plan = ai_profile.get('plan', {})
            days = plan.get('days', [])
            
            # Находим и обновляем задачу
            task_updated = False
            for i, day_task in enumerate(days):
                if day_task.get('id') == task_id:
                    days[i]['status'] = status
                    days[i]['completed_at'] = datetime.now(timezone.utc).isoformat() if status == 'completed' else None
                    if notes:
                        days[i]['notes'] = notes
                    task_updated = True
                    break
            
            if not task_updated:
                logger.warning(f"Задача {task_id} не найдена")
                return False
            
            # Обновляем план
            user_ref.update({
                'ai_profile.plan.days': days,
                'ai_profile.updated_at': datetime.now(timezone.utc),
                'updated_at': datetime.now(timezone.utc)
            })
            
            logger.info(f"Статус задачи {task_id} обновлен для пользователя {telegram_id}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при обновлении статуса задачи: {e}")
            return False
    
    async def get_active_users_by_category(self, category: str) -> List[int]:
        """
        Получает список пользователей с активной категорией
        
        Args:
            category: Категория для поиска
            
        Returns:
            List[int]: Список telegram_id пользователей
        """
        try:
            users = self.db.collection(self.collection_name)\
                .where(filter=FieldFilter('ai_profile.active_category', '==', category))\
                .get()
            
            user_ids = [int(user.id) for user in users]
            logger.info(f"Найдено {len(user_ids)} пользователей с категорией {category}")
            
            return user_ids
            
        except Exception as e:
            logger.error(f"Ошибка при поиске пользователей по категории: {e}")
            return []