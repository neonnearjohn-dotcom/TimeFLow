"""
Система достижений
Профессиональный стиль
"""
from typing import Dict, List

# === СИСТЕМА ДОСТИЖЕНИЙ ===
# Каждое достижение имеет: id, название, описание, условие, редкость, эмодзи

ACHIEVEMENTS = {
    # === STREAK ПРИВЫЧЕК ===
    'habit_streak_3': {
        'name': 'Первые шаги',
        'description': '3 дня последовательного выполнения привычки',
        'condition': {'type': 'habit_streak', 'value': 3},
        'rarity': 'common',
        'emoji': '•',
    },
    'habit_streak_7': {
        'name': 'Неделя дисциплины',
        'description': '7 дней последовательного выполнения привычки',
        'condition': {'type': 'habit_streak', 'value': 7},
        'rarity': 'common',
        'emoji': '•',
    },
    'habit_streak_21': {
        'name': 'Формирование привычки',
        'description': '21 день последовательного выполнения',
        'condition': {'type': 'habit_streak', 'value': 21},
        'rarity': 'rare',
        'emoji': '▸',
    },
    'habit_streak_50': {
        'name': 'Устойчивый результат',
        'description': '50 дней последовательного выполнения',
        'condition': {'type': 'habit_streak', 'value': 50},
        'rarity': 'epic',
        'emoji': '◆',
    },
    'habit_streak_100': {
        'name': 'Мастерство дисциплины',
        'description': '100 дней последовательного выполнения',
        'condition': {'type': 'habit_streak', 'value': 100},
        'rarity': 'legendary',
        'emoji': '★',
    },
    
    # === ФОКУС-СЕССИИ ===
    'focus_sessions_10': {
        'name': 'Концентрация',
        'description': 'Завершить 10 фокус-сессий',
        'condition': {'type': 'focus_sessions', 'value': 10},
        'rarity': 'common',
        'emoji': '•',
    },
    'focus_sessions_50': {
        'name': 'Глубокая работа',
        'description': 'Завершить 50 фокус-сессий',
        'condition': {'type': 'focus_sessions', 'value': 50},
        'rarity': 'rare',
        'emoji': '▸',
    },
    'focus_sessions_100': {
        'name': 'Мастер продуктивности',
        'description': 'Завершить 100 фокус-сессий',
        'condition': {'type': 'focus_sessions', 'value': 100},
        'rarity': 'epic',
        'emoji': '◆',
    },
    'focus_hours_100': {
        'name': 'Управление временем',
        'description': '100 часов в фокусе',
        'condition': {'type': 'focus_hours', 'value': 100},
        'rarity': 'legendary',
        'emoji': '★',
    },
    
    # === ЗАДАЧИ ЧЕК-ЛИСТА ===
    'tasks_completed_10': {
        'name': 'Исполнитель',
        'description': 'Выполнить 10 задач',
        'condition': {'type': 'tasks_completed', 'value': 10},
        'rarity': 'common',
        'emoji': '•',
    },
    'tasks_completed_50': {
        'name': 'Продуктивность',
        'description': 'Выполнить 50 задач',
        'condition': {'type': 'tasks_completed', 'value': 50},
        'rarity': 'rare',
        'emoji': '▸',
    },
    'tasks_completed_100': {
        'name': 'Системный подход',
        'description': 'Выполнить 100 задач',
        'condition': {'type': 'tasks_completed', 'value': 100},
        'rarity': 'epic',
        'emoji': '◆',
    },
    
    # === ВРЕДНЫЕ ПРИВЫЧКИ ===
    'bad_habit_free_7': {
        'name': 'Первая неделя',
        'description': '7 дней без вредной привычки',
        'condition': {'type': 'bad_habit_free', 'value': 7},
        'rarity': 'common',
        'emoji': '•',
    },
    'bad_habit_free_30': {
        'name': 'Месяц контроля',
        'description': '30 дней без вредной привычки',
        'condition': {'type': 'bad_habit_free', 'value': 30},
        'rarity': 'rare',
        'emoji': '▸',
    },
    'bad_habit_free_100': {
        'name': 'Победа над собой',
        'description': '100 дней без вредной привычки',
        'condition': {'type': 'bad_habit_free', 'value': 100},
        'rarity': 'epic',
        'emoji': '◆',
    },
    
    # === ПЕРВЫЕ ШАГИ ===
    'first_habit': {
        'name': 'Начало пути',
        'description': 'Создать первую привычку',
        'condition': {'type': 'first_action', 'value': 'habit'},
        'rarity': 'common',
        'emoji': '•',
    },
    'first_focus': {
        'name': 'Первый фокус',
        'description': 'Завершить первую фокус-сессию',
        'condition': {'type': 'first_action', 'value': 'focus'},
        'rarity': 'common',
        'emoji': '•',
    },
    'first_task': {
        'name': 'Первая задача',
        'description': 'Выполнить первую задачу',
        'condition': {'type': 'first_action', 'value': 'task'},
        'rarity': 'common',
        'emoji': '•',
    },
    
    # === КОМБО И ОСОБЫЕ ===
    'all_modules_used': {
        'name': 'Комплексный подход',
        'description': 'Использовать все модули бота',
        'condition': {'type': 'special', 'value': 'all_modules'},
        'rarity': 'rare',
        'emoji': '▸',
    },
    'early_bird': {
        'name': 'Раннее начало',
        'description': 'Выполнить задачу до 7 утра',
        'condition': {'type': 'special', 'value': 'early_bird'},
        'rarity': 'common',
        'emoji': '•',
    },
    'night_owl': {
        'name': 'Ночная работа',
        'description': 'Фокус-сессия после полуночи',
        'condition': {'type': 'special', 'value': 'night_owl'},
        'rarity': 'common',
        'emoji': '•',
    }
}


def get_achievement_message(achievement_id: str) -> str:
    """
    Возвращает поздравительное сообщение для достижения
    """
    achievement = ACHIEVEMENTS.get(achievement_id)
    if not achievement:
        return ""
    
    emoji = achievement['emoji']
    name = achievement['name']
    description = achievement['description']
    
    rarity_messages = {
        'common': 'Новое достижение',
        'rare': 'Редкое достижение',
        'epic': 'Особое достижение',
        'legendary': 'Выдающееся достижение'
    }
    
    rarity = achievement.get('rarity', 'common')
    header = rarity_messages.get(rarity, 'Новое достижение')
    
    return (
        f"🏆 <b>{header}</b>\n\n"
        f"{name}\n"
        f"{description}"
    )


def get_rarity_color(rarity: str) -> str:
    """
    Возвращает цвет для редкости достижения
    """
    colors = {
        'common': '#9CA3AF',    # Серый
        'rare': '#3B82F6',      # Синий
        'epic': '#8B5CF6',      # Фиолетовый
        'legendary': '#F59E0B'  # Золотой
    }
    return colors.get(rarity, '#9CA3AF')




def check_achievements_for_user(user_stats: Dict, already_unlocked: List[str]) -> List[str]:
    """
    Проверяет, какие достижения может разблокировать пользователь
    
    Args:
        user_stats: Словарь со статистикой пользователя
        already_unlocked: Список уже разблокированных достижений
        
    Returns:
        List[str]: Список ID достижений для разблокировки
    """
    # bugfix: функция воссоздана для исправления ошибки импорта
    unlockable = []
    
    for achievement_id, achievement in ACHIEVEMENTS.items():
        # Пропускаем уже разблокированные
        if achievement_id in already_unlocked:
            continue
            
        condition = achievement['condition']
        condition_type = condition['type']
        required_value = condition['value']
        
        # Проверяем разные типы условий
        if condition_type == 'habit_streak':
            max_streak = user_stats.get('max_habit_streak', 0)
            if max_streak >= required_value:
                unlockable.append(achievement_id)
                
        elif condition_type == 'focus_sessions':
            total_sessions = user_stats.get('total_focus_sessions', 0)
            if total_sessions >= required_value:
                unlockable.append(achievement_id)
                
        elif condition_type == 'focus_hours':
            total_minutes = user_stats.get('total_focus_minutes', 0)
            total_hours = total_minutes // 60
            if total_hours >= required_value:
                unlockable.append(achievement_id)
                
        elif condition_type == 'tasks_completed':
            total_tasks = user_stats.get('total_tasks_completed', 0)
            if total_tasks >= required_value:
                unlockable.append(achievement_id)
                
        elif condition_type == 'bad_habit_days':
            max_days = user_stats.get('max_bad_habit_days', 0)
            if max_days >= required_value:
                unlockable.append(achievement_id)
                
        elif condition_type == 'checklist_streak':
            checklist_streak = user_stats.get('max_checklist_streak', 0)
            if checklist_streak >= required_value:
                unlockable.append(achievement_id)
    
    return unlockable
