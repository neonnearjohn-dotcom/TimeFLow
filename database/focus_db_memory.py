"""
Заглушка для FocusDB - хранение данных в памяти для режима разработки
"""
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


class FocusDBMemory:
    """
    In-memory реализация FocusDB для работы без Firestore
    ДОБАВЛЕНО: Класс для работы без базы данных в режиме разработки
    """
    
    def __init__(self):
        self.sessions = {}
        self.user_settings = {}
        self.user_stats = {}
        logger.info("FocusDBMemory инициализирована (данные в памяти)")
    
    async def create_session(self, session_data: Dict[str, Any]):
        """Создает новую сессию"""
        session_id = session_data['id']
        self.sessions[session_id] = session_data
        logger.debug(f"Сессия {session_id} создана в памяти")
    
    async def get_active_session(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Получает активную сессию пользователя"""
        for session in self.sessions.values():
            if (session['user_id'] == user_id and 
                session['status'] in ['active', 'paused']):
                return session
        return None
    
    async def update_session(self, session_id: str, updates: Dict[str, Any]):
        """Обновляет данные сессии"""
        if session_id in self.sessions:
            self.sessions[session_id].update(updates)
            logger.debug(f"Сессия {session_id} обновлена")
    
    async def get_all_active_sessions(self) -> List[Dict[str, Any]]:
        """Получает все активные сессии"""
        return [s for s in self.sessions.values() 
                if s['status'] in ['active', 'paused']]
    
    async def get_user_settings(self, user_id: str) -> Dict[str, Any]:
        """Получает настройки пользователя"""
        if user_id not in self.user_settings:
            # Возвращаем настройки по умолчанию
            self.user_settings[user_id] = {
                'work_duration': 25,
                'short_break_duration': 5,
                'long_break_duration': 15,
                'auto_start_break': True,
                'sound_enabled': True,
                'daily_goal': 8
            }
        return self.user_settings[user_id]
    
    async def update_user_settings(self, user_id: str, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Обновляет настройки пользователя"""
        if user_id not in self.user_settings:
            await self.get_user_settings(user_id)
        self.user_settings[user_id].update(settings)
        return self.user_settings[user_id]
    
    async def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """Получает статистику пользователя"""
        if user_id not in self.user_stats:
            self.user_stats[user_id] = {
                'total_sessions': 0,
                'total_minutes': 0,
                'current_streak': 0,
                'best_streak': 0,
                'sessions_today': 0,
                'last_session_date': None
            }
        return self.user_stats[user_id]
    
    async def increment_stats(self, user_id: str, minutes: int):
        """Увеличивает статистику пользователя"""
        stats = await self.get_user_stats(user_id)
        stats['total_sessions'] += 1
        stats['total_minutes'] += minutes
        stats['sessions_today'] += 1
        stats['last_session_date'] = datetime.now(timezone.utc)
    
    async def get_today_stats(self, user_id: str) -> Dict[str, Any]:
        """Получает статистику за сегодня"""
        stats = await self.get_user_stats(user_id)
        return {
            'completed_sessions': stats['sessions_today'],
            'total_minutes': stats.get('today_minutes', 0),
            'avg_duration': stats['total_minutes'] / max(stats['total_sessions'], 1)
        }
    
    async def get_week_stats(self, user_id: str) -> Dict[str, Any]:
        """Получает статистику за неделю"""
        return await self.get_today_stats(user_id)  # Упрощенная версия
    
    async def get_month_stats(self, user_id: str) -> Dict[str, Any]:
        """Получает статистику за месяц"""
        return await self.get_today_stats(user_id)  # Упрощенная версия
    
    async def get_all_time_stats(self, user_id: str) -> Dict[str, Any]:
        """Получает статистику за все время"""
        stats = await self.get_user_stats(user_id)
        return {
            'completed_sessions': stats['total_sessions'],
            'total_minutes': stats['total_minutes'],
            'avg_duration': stats['total_minutes'] / max(stats['total_sessions'], 1)
        }
