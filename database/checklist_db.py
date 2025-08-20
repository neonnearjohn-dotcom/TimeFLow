"""
Функции для работы с чек-листом в Firestore
"""
from google.cloud import firestore
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, date
import logging
import uuid

logger = logging.getLogger(__name__)


class ChecklistDB:
    """Класс для работы с задачами в Firestore"""
    
    def __init__(self, db: firestore.Client):
        """
        Инициализация с существующим клиентом Firestore
        
        Args:
            db: Клиент Firestore
        """
        self.db = db
    
    # === ЗАДАЧИ ===
    
    async def create_task(self, telegram_id: int, task_data: Dict[str, Any]) -> Optional[str]:
        """
        Создает новую задачу
        
        Args:
            telegram_id: ID пользователя
            task_data: Данные задачи
            
        Returns:
            ID созданной задачи или None
        """
        try:
            task_id = str(uuid.uuid4())
            task_data['id'] = task_id
            task_data['created_at'] = datetime.utcnow()
            task_data['status'] = 'active'
            task_data['completed_at'] = None
            
            # Сохраняем в подколлекцию tasks пользователя
            user_ref = self.db.collection('users').document(str(telegram_id))
            user_ref.collection('tasks').document(task_id).set(task_data)
            
            logger.info(f"Задача {task_id} создана для пользователя {telegram_id}")
            return task_id
        except Exception as e:
            logger.error(f"Ошибка при создании задачи: {e}")
            return None
    
    async def get_user_tasks(self, telegram_id: int, priority: Optional[str] = None, 
                           status: str = 'active') -> List[Dict[str, Any]]:
        """
        Получает задачи пользователя
        
        Args:
            telegram_id: ID пользователя
            priority: Фильтр по приоритету (опционально)
            status: Фильтр по статусу (active/completed)
            
        Returns:
            Список задач
        """
        try:
            user_ref = self.db.collection('users').document(str(telegram_id))
            query = user_ref.collection('tasks').where('status', '==', status)
            
            if priority and priority != 'all':
                query = query.where('priority', '==', priority)
            
            tasks = query.stream()
            
            tasks_list = []
            for task in tasks:
                task_data = task.to_dict()
                task_data['id'] = task.id
                tasks_list.append(task_data)
            
            # Сортировка по приоритету и дате создания
            priority_order = {
                'urgent_important': 0,
                'not_urgent_important': 1,
                'urgent_not_important': 2,
                'not_urgent_not_important': 3
            }
            
            tasks_list.sort(
                key=lambda x: (
                    priority_order.get(x.get('priority', ''), 4),
                    x.get('created_at', datetime.min)
                )
            )
            
            return tasks_list
        except Exception as e:
            logger.error(f"Ошибка при получении задач: {e}")
            return []
        
    async def get_all_tasks(self, telegram_id: int, status: str = 'active') -> List[Dict[str, Any]]:
   
         return await self.get_user_tasks(telegram_id, priority='all', status=status)    
    
    async def get_tasks_by_priority(self, telegram_id: int, priority: str, status: str = 'active') -> List[Dict[str, Any]]:
    
         return await self.get_user_tasks(telegram_id, priority=priority, status=status) 
    
    async def get_task(self, telegram_id: int, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Получает конкретную задачу
        """
        try:
            user_ref = self.db.collection('users').document(str(telegram_id))
            task_doc = user_ref.collection('tasks').document(task_id).get()
            
            if task_doc.exists:
                task_data = task_doc.to_dict()
                task_data['id'] = task_id
                return task_data
            return None
        except Exception as e:
            logger.error(f"Ошибка при получении задачи: {e}")
            return None
    
    async def complete_task(self, telegram_id: int, task_id: str) -> Tuple[bool, int]:
        """
        Отмечает задачу как выполненную

        Returns:
            (success, 0)
        """
        try:
            user_ref = self.db.collection('users').document(str(telegram_id))
            task_ref = user_ref.collection('tasks').document(task_id)
            
            # Получаем задачу
            task_doc = task_ref.get()
            if not task_doc.exists:
                return False, 0
            
            task_data = task_doc.to_dict()
            
           
            points = 0
            
            # Обновляем задачу
            task_ref.update({
                'status': 'completed',
                'completed_at': datetime.utcnow()
            })
            
            # Добавляем в историю выполненных
            completed_data = task_data.copy()
            completed_data['completed_at'] = datetime.utcnow()
            
            user_ref.collection('completed_tasks').add(completed_data)
            
            # Обновляем статистику
            await self._update_user_stats(telegram_id, task_data.get('priority'))
            
            return True, points
        except Exception as e:
            logger.error(f"Ошибка при выполнении задачи: {e}")
            return False, 0
    
    async def update_task(self, telegram_id: int, task_id: str, updates: Dict[str, Any]) -> bool:
        """
        Обновляет задачу
        
        Args:
            telegram_id: ID пользователя
            task_id: ID задачи
            updates: Словарь с обновляемыми полями
            
        Returns:
            True если успешно, False иначе
        """
        try:
            user_ref = self.db.collection('users').document(str(telegram_id))
            task_ref = user_ref.collection('tasks').document(task_id)
            
            # Проверяем существование задачи
            if not task_ref.get().exists:
                logger.warning(f"Задача {task_id} не найдена для пользователя {telegram_id}")
                return False
            
            # Добавляем время обновления
            updates['updated_at'] = datetime.utcnow()
            
            # Обновляем задачу
            task_ref.update(updates)
            
            logger.info(f"Задача {task_id} обновлена для пользователя {telegram_id}")
            return True
        except Exception as e:
            logger.error(f"Ошибка при обновлении задачи: {e}")
            return False
    
    async def delete_task(self, telegram_id: int, task_id: str) -> bool:
        """
        Удаляет задачу
        """
        try:
            user_ref = self.db.collection('users').document(str(telegram_id))
            user_ref.collection('tasks').document(task_id).delete()
            return True
        except Exception as e:
            logger.error(f"Ошибка при удалении задачи: {e}")
            return False
    

    
    # === СТАТИСТИКА ===
    
    async def get_user_stats(self, telegram_id: int) -> Dict[str, Any]:
        """
        Получает статистику пользователя
        """
        try:
            user_ref = self.db.collection('users').document(str(telegram_id))
            user_doc = user_ref.get()
            
            if user_doc.exists:
                data = user_doc.to_dict()
                checklist_stats = data.get('checklist_stats', {})
            else:
                checklist_stats = {}
            
            # Дефолтные значения
            default_stats = {
                'total_completed': 0,
                'current_streak': 0,
                'best_streak': 0,
                'last_completion_date': None,
                'completed_by_priority': {
                    'urgent_important': 0,
                    'not_urgent_important': 0,
                    'urgent_not_important': 0,
                    'not_urgent_not_important': 0
                }
            }
            
            # Объединяем с существующими данными
            for key, value in default_stats.items():
                if key not in checklist_stats:
                    checklist_stats[key] = value
            
            return checklist_stats
        except Exception as e:
            logger.error(f"Ошибка при получении статистики: {e}")
            return {}
    
    async def get_completed_tasks_history(self, telegram_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Получает историю выполненных задач
        """
        try:
            user_ref = self.db.collection('users').document(str(telegram_id))
            
            # Получаем последние выполненные задачи
            completed = user_ref.collection('completed_tasks')\
                .order_by('completed_at', direction=firestore.Query.DESCENDING)\
                .limit(limit)\
                .stream()
            
            history = []
            for task in completed:
                task_data = task.to_dict()
                history.append(task_data)
            
            return history
        except Exception as e:
            logger.error(f"Ошибка при получении истории: {e}")
            return []
    
    async def _update_user_stats(self, telegram_id: int, priority: str):
        """
        Обновляет статистику пользователя
        """
        try:
            user_ref = self.db.collection('users').document(str(telegram_id))
            
            # Получаем текущую статистику
            stats = await self.get_user_stats(telegram_id)
            
            # Обновляем общие показатели
            stats['total_completed'] += 1
            
            # Обновляем по приоритету
            if priority in stats['completed_by_priority']:
                stats['completed_by_priority'][priority] += 1
            
            # Обновляем streak
            today = date.today()
            last_date = stats.get('last_completion_date')
            
            if last_date:
                last_date = last_date.date() if isinstance(last_date, datetime) else last_date
                days_diff = (today - last_date).days
                
                if days_diff == 0:
                    # Уже выполняли сегодня
                    pass
                elif days_diff == 1:
                    # Выполняли вчера - продолжаем streak
                    stats['current_streak'] += 1
                else:
                    # Пропустили день - сбрасываем streak
                    stats['current_streak'] = 1
            else:
                # Первое выполнение
                stats['current_streak'] = 1
            
            # Обновляем лучший streak
            stats['best_streak'] = max(stats['current_streak'], stats.get('best_streak', 0))
            stats['last_completion_date'] = datetime.utcnow()
            
            # Сохраняем обновленную статистику
            user_ref.update({'checklist_stats': stats})
            
        except Exception as e:
            logger.error(f"Ошибка при обновлении статистики: {e}")
    
    def _get_template_name(self, template_key: str) -> str:
        """
        Возвращает название шаблона
        """
        template_names = {
            'morning': 'Утренние дела',
            'work': 'Рабочие задачи',
            'evening': 'Вечерняя рутина',
            'home': 'Домашние дела',
            'health': 'Здоровье и спорт',
            'education': 'Обучение'
        }
        return template_names.get(template_key, 'Шаблон')