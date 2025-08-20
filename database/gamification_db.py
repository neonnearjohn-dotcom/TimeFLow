"""
Функции для работы с геймификацией в Firestore
"""
from google.cloud import firestore
from typing import Dict, List, Any
from datetime import datetime, date
import logging
from utils.achievements import ACHIEVEMENTS, check_achievements_for_user

logger = logging.getLogger(__name__)


class GamificationDB:
    """Класс для работы с достижениями в Firestore"""
    
    def __init__(self, db: firestore.Client):
        """
        Инициализация с существующим клиентом Firestore
        
        Args:
            db: Клиент Firestore
        """
        self.db = db
    
    # === ДОСТИЖЕНИЯ ===
    
    async def unlock_achievement(self, telegram_id: int, achievement_id: str) -> bool:
        """Разблокирует достижение для пользователя"""
        try:
            if achievement_id not in ACHIEVEMENTS:
                return False

            user_ref = self.db.collection('users').document(str(telegram_id))

            achievement_data = {
                'achievement_id': achievement_id,
                'unlocked_at': datetime.utcnow()
            }

            user_ref.collection('achievements').document(achievement_id).set(achievement_data)

            user_ref.update({
                'achievements_count': firestore.Increment(1)
            })

            logger.info(f"Достижение {achievement_id} разблокировано для пользователя {telegram_id}")
            return True

        except Exception as e:
            logger.error(f"Ошибка при разблокировке достижения: {e}")
            return False
    
    async def get_user_achievements(self, telegram_id: int) -> List[Dict]:
        """
        Получает все достижения пользователя
        """
        try:
            user_ref = self.db.collection('users').document(str(telegram_id))
            
            achievements = user_ref.collection('achievements')\
                .order_by('unlocked_at', direction=firestore.Query.DESCENDING)\
                .stream()
            
            achievements_list = []
            for ach in achievements:
                ach_data = ach.to_dict()
                ach_id = ach_data['achievement_id']
                
                # Добавляем информацию о достижении
                if ach_id in ACHIEVEMENTS:
                    ach_info = ACHIEVEMENTS[ach_id].copy()
                    ach_info['unlocked_at'] = ach_data['unlocked_at']
                    achievements_list.append(ach_info)
            
            return achievements_list
            
        except Exception as e:
            logger.error(f"Ошибка при получении достижений: {e}")
            return []
    
    async def check_and_unlock_achievements(self, telegram_id: int) -> List[str]:
        """
        Проверяет и разблокирует новые достижения
        
        Returns:
            Список ID новых достижений
        """
        try:
            # Получаем статистику пользователя
            user_stats = await self._get_user_stats(telegram_id)
            
            # Получаем уже разблокированные достижения
            user_ref = self.db.collection('users').document(str(telegram_id))
            unlocked = user_ref.collection('achievements').stream()
            unlocked_ids = [ach.id for ach in unlocked]
            
            # Проверяем новые достижения
            new_achievements = check_achievements_for_user(user_stats, unlocked_ids)
            
            # Разблокируем новые
            unlocked_now = []
            for ach_id in new_achievements:
                success = await self.unlock_achievement(telegram_id, ach_id)
                if success:
                    unlocked_now.append(ach_id)
            
            return unlocked_now
            
        except Exception as e:
            logger.error(f"Ошибка при проверке достижений: {e}")
            return []
    
    # === СТАТИСТИКА ===
    
    async def get_user_profile(self, telegram_id: int) -> Dict[str, Any]:
        """
        Получает полный профиль пользователя для отображения
        """
        try:
            user_ref = self.db.collection('users').document(str(telegram_id))
            user_doc = user_ref.get()
            
            if not user_doc.exists:
                logger.warning(f"Пользователь {telegram_id} не найден при получении профиля")
                return {}
            
            user_data = user_doc.to_dict()
            
            # Базовая информация с проверкой на None
            profile = {
                'username': user_data.get('username') or 'Пользователь',
                'full_name': user_data.get('full_name') or 'Без имени',
                'created_at': user_data.get('created_at'),
                'achievements_count': user_data.get('achievements_count', 0)
            }
            
            # Получаем статистику по модулям
            stats = await self._get_user_stats(telegram_id)
            
            # Лучшие streak'и
            profile['best_streaks'] = {
                'habits': stats.get('max_habit_streak', 0),
                'focus': stats.get('max_focus_streak', 0),
                'checklist': stats.get('max_checklist_streak', 0),
                'bad_habits': stats.get('max_bad_habit_free_days', 0)
            }
            
            # Общий прогресс
            profile['total_progress'] = {
                'habits_completed': stats.get('total_habits_completed', 0),
                'focus_sessions': stats.get('total_focus_sessions', 0),
                'tasks_completed': stats.get('total_tasks_completed', 0),
                'focus_hours': stats.get('total_focus_minutes', 0) // 60 if stats.get('total_focus_minutes') else 0
            }
            
            # Последние действия
            try:
                profile['recent_actions'] = await self._get_recent_actions(telegram_id)
            except Exception as e:
                logger.warning(f"Ошибка при получении последних действий: {e}")
                profile['recent_actions'] = []
            
            # Достижения
            try:
                profile['achievements'] = await self.get_user_achievements(telegram_id)
            except Exception as e:
                logger.warning(f"Ошибка при получении достижений: {e}")
                profile['achievements'] = []
            
            return profile
            
        except Exception as e:
            logger.error(f"Ошибка при получении профиля пользователя {telegram_id}: {e}", exc_info=True)
            return {}
    
    async def _get_user_stats(self, telegram_id: int) -> Dict[str, Any]:
        """
        Собирает полную статистику пользователя из всех модулей
        """
        stats = {
            'max_habit_streak': 0,
            'total_habits_created': 0,
            'total_habits_completed': 0,
            'max_bad_habit_free_days': 0,
            'total_bad_habits_created': 0,
            'total_focus_sessions': 0,
            'total_focus_minutes': 0,
            'max_focus_streak': 0,
            'total_tasks_completed': 0,
            'max_checklist_streak': 0
        }
        
        try:
            user_ref = self.db.collection('users').document(str(telegram_id))
            user_doc = user_ref.get()
            
            if user_doc.exists:
                user_data = user_doc.to_dict()
                
                # Статистика привычек
                try:
                    habits = user_ref.collection('habits').stream()
                    for habit in habits:
                        habit_data = habit.to_dict()
                        stats['total_habits_created'] += 1
                        stats['total_habits_completed'] += habit_data.get('total_completions', 0)
                        best_streak = habit_data.get('best_streak', 0)
                        if best_streak > stats['max_habit_streak']:
                            stats['max_habit_streak'] = best_streak
                except Exception as e:
                    logger.warning(f"Ошибка при получении статистики привычек: {e}")
                
                # Статистика вредных привычек
                try:
                    bad_habits = user_ref.collection('bad_habits').stream()
                    for bad_habit in bad_habits:
                        bad_habit_data = bad_habit.to_dict()
                        stats['total_bad_habits_created'] += 1
                        best_streak = bad_habit_data.get('best_streak', 0)
                        if best_streak > stats['max_bad_habit_free_days']:
                            stats['max_bad_habit_free_days'] = best_streak
                except Exception as e:
                    logger.warning(f"Ошибка при получении статистики вредных привычек: {e}")
                
                # Статистика фокуса
                try:
                    focus_settings = user_data.get('focus_settings', {})
                    stats['max_focus_streak'] = focus_settings.get('current_streak', 0)
                    
                    # Считаем завершенные сессии
                    focus_sessions = user_ref.collection('focus_sessions')\
                        .where('status', '==', 'completed').stream()
                    
                    for session in focus_sessions:
                        session_data = session.to_dict()
                        stats['total_focus_sessions'] += 1
                        stats['total_focus_minutes'] += session_data.get('actual_duration', 0)
                except Exception as e:
                    logger.warning(f"Ошибка при получении статистики фокуса: {e}")
                
                # Статистика чек-листа
                try:
                    checklist_stats = user_data.get('checklist_stats', {})
                    stats['total_tasks_completed'] = checklist_stats.get('total_completed', 0)
                    stats['max_checklist_streak'] = checklist_stats.get('best_streak', 0)
                except Exception as e:
                    logger.warning(f"Ошибка при получении статистики чек-листа: {e}")
            
            return stats
            
        except Exception as e:
            logger.error(f"Общая ошибка при получении статистики: {e}")
            return stats
    
    async def _get_recent_actions(self, telegram_id: int, limit: int = 5) -> List[Dict]:
        """
        Получает последние действия пользователя
        """
        try:
            actions = []
            user_ref = self.db.collection('users').document(str(telegram_id))
            
            # Получаем последние записи из истории действий
            points_history = user_ref.collection('points_history')\
                .order_by('timestamp', direction=firestore.Query.DESCENDING)\
                .limit(limit)\
                .stream()

            for record in points_history:
                data = record.to_dict()
                reason = data.get('reason', '')
                
                # Преобразуем reason в читаемый вид
                action_names = {
                    'habit_completed': '✅ Выполнена привычка',
                    'focus_session_complete': '🎯 Завершена фокус-сессия',
                    'task_completed': '📋 Выполнена задача',
                    'achievement_unlocked': '🏆 Получено достижение',
                    'bad_habit_day': '💪 День без вредной привычки'
                }
                
                action = {
                    'name': action_names.get(reason, 'Действие'),
                    'timestamp': data.get('timestamp')
                }
                
                actions.append(action)
            
            return actions
            
        except Exception as e:
            logger.error(f"Ошибка при получении последних действий: {e}")
            return []
    
    # === СПЕЦИАЛЬНЫЕ ПРОВЕРКИ ===
    
    async def check_time_based_achievements(self, telegram_id: int, action_type: str) -> List[str]:
        """
        Проверяет достижения, связанные со временем
        """
        unlocked = []
        
        try:
            current_hour = datetime.utcnow().hour
            
            # Ранняя пташка (до 7 утра)
            if action_type == 'task_completed' and current_hour < 7:
                if await self._check_and_unlock_if_new(telegram_id, 'early_bird'):
                    unlocked.append('early_bird')
            
            # Ночная сова (после полуночи)
            if action_type == 'focus_session' and (current_hour >= 0 and current_hour < 6):
                if await self._check_and_unlock_if_new(telegram_id, 'night_owl'):
                    unlocked.append('night_owl')
            
            return unlocked
            
        except Exception as e:
            logger.error(f"Ошибка при проверке временных достижений: {e}")
            return []
    
    async def _check_and_unlock_if_new(self, telegram_id: int, achievement_id: str) -> bool:
        """
        Проверяет и разблокирует достижение, если оно новое
        """
        try:
            user_ref = self.db.collection('users').document(str(telegram_id))
            ach_doc = user_ref.collection('achievements').document(achievement_id).get()
            
            if not ach_doc.exists:
                success = await self.unlock_achievement(telegram_id, achievement_id)
                return success
            
            return False
            
        except Exception as e:
            logger.error(f"Ошибка при проверке достижения {achievement_id}: {e}")
            return False