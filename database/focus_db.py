"""
База данных для модуля фокус-сессий
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, date, timedelta, timezone
from google.cloud import firestore

logger = logging.getLogger(__name__)


class FocusDB:
    """Класс для работы с фокус-сессиями в Firestore"""
    
    def __init__(self, db):
        """
        Args:
            db: Инстанс Firestore database
        """
        self.db = db
    
    # === Работа с сессиями ===
    
    async def create_session(self, session_data: Dict[str, Any]) -> str:
        """
        Создает новую фокус-сессию.
        
        Args:
            session_data: Данные сессии
            
        Returns:
            ID созданной сессии
        """
        try:
            # Создаем документ сессии
            sessions_ref = self.db.collection('focus_sessions')
            doc_ref = sessions_ref.document(session_data['id'])
            
            doc_ref.set({
                **session_data,
                'created_at': firestore.SERVER_TIMESTAMP,
                'updated_at': firestore.SERVER_TIMESTAMP
            })
            
            logger.info(f"Создана фокус-сессия {session_data['id']}")
            return session_data['id']
            
        except Exception as e:
            logger.error(f"Ошибка создания сессии: {e}")
            raise
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Получает сессию по ID.
        
        Returns:
            Данные сессии или None
        """
        try:
            doc_ref = self.db.collection('focus_sessions').document(session_id)
            doc = doc_ref.get()
            
            if doc.exists:
                data = doc.to_dict()
                data['id'] = doc.id
                return data
            
            return None
            
        except Exception as e:
            logger.error(f"Ошибка получения сессии {session_id}: {e}")
            return None
    
    async def get_active_session(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Получает активную сессию пользователя.
        
        Returns:
            Данные активной сессии или None
        """
        try:
            sessions_ref = self.db.collection('focus_sessions')
            
            # Ищем активную или приостановленную сессию
            query = sessions_ref.where(
                'user_id', '==', user_id
            ).where(
                'status', 'in', ['active', 'paused']
            ).limit(1)
            
            docs = query.get()
            
            for doc in docs:
                data = doc.to_dict()
                data['id'] = doc.id
                return data
            
            return None
            
        except Exception as e:
            logger.error(f"Ошибка получения активной сессии: {e}")
            return None
    
    async def update_session(
        self,
        session_id: str,
        update_data: Dict[str, Any]
    ) -> bool:
        """
        Обновляет данные сессии.
        
        Returns:
            True если успешно
        """
        try:
            doc_ref = self.db.collection('focus_sessions').document(session_id)
            
            update_data['updated_at'] = firestore.SERVER_TIMESTAMP
            doc_ref.update(update_data)
            
            logger.info(f"Обновлена сессия {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка обновления сессии {session_id}: {e}")
            return False
    
    async def get_all_active_sessions(self) -> List[Dict[str, Any]]:
        """
        Получает все активные сессии (для восстановления).
        
        Returns:
            Список активных сессий
        """
        try:
            sessions_ref = self.db.collection('focus_sessions')
            
            # Получаем все активные сессии
            query = sessions_ref.where('status', '==', 'active')
            
            docs = query.get()
            sessions = []
            
            for doc in docs:
                data = doc.to_dict()
                data['id'] = doc.id
                sessions.append(data)
            
            return sessions
            
        except Exception as e:
            logger.error(f"Ошибка получения активных сессий: {e}")
            return []
    
    # === Работа с настройками пользователя ===
    
    async def get_user_settings(self, user_id: str) -> Dict[str, Any]:
        """
        Получает настройки фокус-сессий пользователя.
        
        Returns:
            Настройки с дефолтными значениями
        """
        try:
            user_ref = self.db.collection('users').document(user_id)
            user_doc = user_ref.get()
            
            if user_doc.exists:
                data = user_doc.to_dict()
                settings = data.get('focus_settings', {})
            else:
                settings = {}
            
            # notifications removed - убрано поле notifications_enabled из дефолтных настроек
            # Возвращаем с дефолтными значениями
            return {
                'work_duration': settings.get('work_duration', 25),
                'short_break_duration': settings.get('short_break_duration', 5),
                'long_break_duration': settings.get('long_break_duration', 15),
                'sound_enabled': settings.get('sound_enabled', True),
                'auto_start_break': settings.get('auto_start_break', True),
                'daily_goal': settings.get('daily_goal', 8),  # Pomodoros в день
                'weekly_goal': settings.get('weekly_goal', 40)  # Pomodoros в неделю
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения настроек: {e}")
            # notifications removed - убрано поле notifications_enabled из дефолтных настроек
            return {
                'work_duration': 25,
                'short_break_duration': 5,
                'long_break_duration': 15,
                'sound_enabled': True,
                'auto_start_break': True,
                'daily_goal': 8,
                'weekly_goal': 40
            }
    
    async def update_user_settings(
        self,
        user_id: str,
        settings: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Обновляет настройки пользователя.
        
        Returns:
            Обновленные настройки
        """
        try:
            user_ref = self.db.collection('users').document(user_id)
            
            # Обновляем только переданные настройки
            update_data = {
                f'focus_settings.{key}': value
                for key, value in settings.items()
            }
            update_data['focus_settings_updated_at'] = firestore.SERVER_TIMESTAMP
            
            user_ref.update(update_data)
            
            # Возвращаем полные настройки
            return await self.get_user_settings(user_id)
            
        except Exception as e:
            logger.error(f"Ошибка обновления настроек: {e}")
            raise
    
    # === Работа со статистикой ===
    
    async def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """
        Получает базовую статистику пользователя.
        
        Returns:
            Словарь со статистикой
        """
        try:
            user_ref = self.db.collection('users').document(user_id)
            user_doc = user_ref.get()
            
            if user_doc.exists:
                data = user_doc.to_dict()
                stats = data.get('focus_stats', {})
            else:
                stats = {}
            
            return {
                'total_sessions': stats.get('total_sessions', 0),
                'total_minutes': stats.get('total_minutes', 0),
                'current_streak': stats.get('current_streak', 0),
                'best_streak': stats.get('best_streak', 0),
                'last_session_date': stats.get('last_session_date'),
                'sessions_today': await self._get_sessions_count_today(user_id)
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
            return {
                'total_sessions': 0,
                'total_minutes': 0,
                'current_streak': 0,
                'best_streak': 0,
                'sessions_today': 0
            }
    
    async def increment_stats(
        self,
        user_id: str,
        completed_minutes: int
    ):
        """
        Увеличивает статистику пользователя.
        """
        try:
            user_ref = self.db.collection('users').document(user_id)
            
            # Получаем текущую статистику
            user_doc = user_ref.get()
            if user_doc.exists:
                data = user_doc.to_dict()
                stats = data.get('focus_stats', {})
            else:
                stats = {}
            
            # Обновляем статистику
            current_date = date.today()
            last_session_date = stats.get('last_session_date')
            
            # Обновляем streak
            if last_session_date:
                last_date = last_session_date.date() if hasattr(last_session_date, 'date') else last_session_date
                days_diff = (current_date - last_date).days
                
                if days_diff == 0:
                    # Сессия в тот же день
                    current_streak = stats.get('current_streak', 0)
                elif days_diff == 1:
                    # Следующий день - увеличиваем streak
                    current_streak = stats.get('current_streak', 0) + 1
                else:
                    # Пропущены дни - сбрасываем streak
                    current_streak = 1
            else:
                # Первая сессия
                current_streak = 1
            
            # Обновляем лучший streak
            best_streak = max(current_streak, stats.get('best_streak', 0))
            
            # Обновляем данные
            update_data = {
                'focus_stats.total_sessions': firestore.Increment(1),
                'focus_stats.total_minutes': firestore.Increment(completed_minutes),
                'focus_stats.current_streak': current_streak,
                'focus_stats.best_streak': best_streak,
                'focus_stats.last_session_date': current_date
            }
            
            user_ref.update(update_data)
            
            logger.info(f"Обновлена статистика пользователя {user_id}")
            
        except Exception as e:
            logger.error(f"Ошибка обновления статистики: {e}")
    
    async def get_today_stats(self, user_id: str) -> Dict[str, Any]:
        """
        Получает статистику за сегодня.
        """
        try:
            today_start = datetime.combine(
                date.today(),
                datetime.min.time()
            ).replace(tzinfo=timezone.utc)
            
            sessions_ref = self.db.collection('focus_sessions')
            query = sessions_ref.where(
                'user_id', '==', user_id
            ).where(
                'status', '==', 'completed'
            ).where(
                'started_at', '>=', today_start
            )
            
            docs = query.get()
            
            total_minutes = 0
            sessions_count = 0
            
            for doc in docs:
                data = doc.to_dict()
                total_minutes += data.get('completed_minutes', 0)
                sessions_count += 1
            
            return {
                'completed_sessions': sessions_count,
                'total_minutes': total_minutes,
                'avg_duration': total_minutes // sessions_count if sessions_count > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения статистики за сегодня: {e}")
            return {
                'completed_sessions': 0,
                'total_minutes': 0,
                'avg_duration': 0
            }
    
    async def get_week_stats(self, user_id: str) -> Dict[str, Any]:
        """
        Получает статистику за неделю.
        """
        try:
            week_start = datetime.combine(
                date.today() - timedelta(days=7),
                datetime.min.time()
            ).replace(tzinfo=timezone.utc)
            
            sessions_ref = self.db.collection('focus_sessions')
            query = sessions_ref.where(
                'user_id', '==', user_id
            ).where(
                'status', '==', 'completed'
            ).where(
                'started_at', '>=', week_start
            )
            
            docs = query.get()
            
            total_minutes = 0
            sessions_count = 0
            
            for doc in docs:
                data = doc.to_dict()
                total_minutes += data.get('completed_minutes', 0)
                sessions_count += 1
            
            # Получаем общую статистику для streak
            user_stats = await self.get_user_stats(user_id)
            
            return {
                'completed_sessions': sessions_count,
                'total_minutes': total_minutes,
                'avg_duration': total_minutes // sessions_count if sessions_count > 0 else 0,
                'current_streak': user_stats.get('current_streak', 0),
                'best_streak': user_stats.get('best_streak', 0)
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения статистики за неделю: {e}")
            return {
                'completed_sessions': 0,
                'total_minutes': 0,
                'avg_duration': 0,
                'current_streak': 0,
                'best_streak': 0
            }
    
    async def get_month_stats(self, user_id: str) -> Dict[str, Any]:
        """
        Получает статистику за месяц.
        """
        try:
            month_start = datetime.combine(
                date.today() - timedelta(days=30),
                datetime.min.time()
            ).replace(tzinfo=timezone.utc)
            
            sessions_ref = self.db.collection('focus_sessions')
            query = sessions_ref.where(
                'user_id', '==', user_id
            ).where(
                'status', '==', 'completed'
            ).where(
                'started_at', '>=', month_start
            )
            
            docs = query.get()
            
            total_minutes = 0
            sessions_count = 0
            
            for doc in docs:
                data = doc.to_dict()
                total_minutes += data.get('completed_minutes', 0)
                sessions_count += 1
            
            # Получаем общую статистику для streak
            user_stats = await self.get_user_stats(user_id)
            
            return {
                'completed_sessions': sessions_count,
                'total_minutes': total_minutes,
                'avg_duration': total_minutes // sessions_count if sessions_count > 0 else 0,
                'current_streak': user_stats.get('current_streak', 0),
                'best_streak': user_stats.get('best_streak', 0)
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения статистики за месяц: {e}")
            return {
                'completed_sessions': 0,
                'total_minutes': 0,
                'avg_duration': 0,
                'current_streak': 0,
                'best_streak': 0
            }
    
    async def get_all_time_stats(self, user_id: str) -> Dict[str, Any]:
        """
        Получает статистику за всё время.
        """
        try:
            user_stats = await self.get_user_stats(user_id)
            
            return {
                'completed_sessions': user_stats.get('total_sessions', 0),
                'total_minutes': user_stats.get('total_minutes', 0),
                'avg_duration': (
                    user_stats.get('total_minutes', 0) // user_stats.get('total_sessions', 1)
                    if user_stats.get('total_sessions', 0) > 0 else 0
                ),
                'current_streak': user_stats.get('current_streak', 0),
                'best_streak': user_stats.get('best_streak', 0)
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения общей статистики: {e}")
            return {
                'completed_sessions': 0,
                'total_minutes': 0,
                'avg_duration': 0,
                'current_streak': 0,
                'best_streak': 0
            }
    
    # === Вспомогательные методы ===
    
    async def _get_sessions_count_today(self, user_id: str) -> int:
        """
        Получает количество сессий за сегодня.
        """
        try:
            stats = await self.get_today_stats(user_id)
            return stats.get('completed_sessions', 0)
            
        except Exception as e:
            logger.error(f"Ошибка подсчета сессий за сегодня: {e}")
            return 0