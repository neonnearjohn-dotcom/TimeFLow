"""
Система достижений и очков
Профессиональный стиль
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime

# === ТАБЛИЦА НАЧИСЛЕНИЯ ОЧКОВ ===
# Фиксированные значения очков за различные действия

POINTS_TABLE = {
    # Привычки
    "habit_completed": 5,  # Выполнение полезной привычки
    "habit_streak_bonus": 10,  # Бонус за новый день streak привычки
    # Вредные привычки
    "bad_habit_day": 3,  # Каждый день без вредной привычки
    "bad_habit_milestone": 20,  # Достижение важной отметки (7, 30, 100 дней)
    # Фокус-сессии
    "focus_per_minute": 1,  # За каждую минуту фокуса
    "focus_session_complete": 5,  # Бонус за завершение сессии
    # Чек-лист (зависит от приоритета)
    "task_urgent_important": 10,  # Важно и срочно
    "task_not_urgent_important": 8,  # Важно, но не срочно
    "task_urgent_not_important": 5,  # Срочно, но не важно
    "task_not_urgent_not_important": 3,  # Не важно и не срочно
    # Достижения
    "achievement_common": 10,  # Обычное достижение
    "achievement_rare": 25,  # Редкое достижение
    "achievement_epic": 50,  # Эпическое достижение
    "achievement_legendary": 100,  # Легендарное достижение
}

# === СИСТЕМА ДОСТИЖЕНИЙ ===
# Каждое достижение имеет: id, название, описание, условие, редкость, эмодзи

ACHIEVEMENTS = {
    # === STREAK ПРИВЫЧЕК ===
    "habit_streak_3": {
        "name": "Первые шаги",
        "description": "3 дня последовательного выполнения привычки",
        "condition": {"type": "habit_streak", "value": 3},
        "rarity": "common",
        "emoji": "•",
        "points": POINTS_TABLE["achievement_common"],
    },
    "habit_streak_7": {
        "name": "Неделя дисциплины",
        "description": "7 дней последовательного выполнения привычки",
        "condition": {"type": "habit_streak", "value": 7},
        "rarity": "common",
        "emoji": "•",
        "points": POINTS_TABLE["achievement_common"],
    },
    "habit_streak_21": {
        "name": "Формирование привычки",
        "description": "21 день последовательного выполнения",
        "condition": {"type": "habit_streak", "value": 21},
        "rarity": "rare",
        "emoji": "▸",
        "points": POINTS_TABLE["achievement_rare"],
    },
    "habit_streak_50": {
        "name": "Устойчивый результат",
        "description": "50 дней последовательного выполнения",
        "condition": {"type": "habit_streak", "value": 50},
        "rarity": "epic",
        "emoji": "◆",
        "points": POINTS_TABLE["achievement_epic"],
    },
    "habit_streak_100": {
        "name": "Мастерство дисциплины",
        "description": "100 дней последовательного выполнения",
        "condition": {"type": "habit_streak", "value": 100},
        "rarity": "legendary",
        "emoji": "★",
        "points": POINTS_TABLE["achievement_legendary"],
    },
    # === ФОКУС-СЕССИИ ===
    "focus_sessions_10": {
        "name": "Концентрация",
        "description": "Завершить 10 фокус-сессий",
        "condition": {"type": "focus_sessions", "value": 10},
        "rarity": "common",
        "emoji": "•",
        "points": POINTS_TABLE["achievement_common"],
    },
    "focus_sessions_50": {
        "name": "Глубокая работа",
        "description": "Завершить 50 фокус-сессий",
        "condition": {"type": "focus_sessions", "value": 50},
        "rarity": "rare",
        "emoji": "▸",
        "points": POINTS_TABLE["achievement_rare"],
    },
    "focus_sessions_100": {
        "name": "Мастер продуктивности",
        "description": "Завершить 100 фокус-сессий",
        "condition": {"type": "focus_sessions", "value": 100},
        "rarity": "epic",
        "emoji": "◆",
        "points": POINTS_TABLE["achievement_epic"],
    },
    "focus_hours_100": {
        "name": "Управление временем",
        "description": "100 часов в фокусе",
        "condition": {"type": "focus_hours", "value": 100},
        "rarity": "legendary",
        "emoji": "★",
        "points": POINTS_TABLE["achievement_legendary"],
    },
    # === ЗАДАЧИ ЧЕК-ЛИСТА ===
    "tasks_completed_10": {
        "name": "Исполнитель",
        "description": "Выполнить 10 задач",
        "condition": {"type": "tasks_completed", "value": 10},
        "rarity": "common",
        "emoji": "•",
        "points": POINTS_TABLE["achievement_common"],
    },
    "tasks_completed_50": {
        "name": "Продуктивность",
        "description": "Выполнить 50 задач",
        "condition": {"type": "tasks_completed", "value": 50},
        "rarity": "rare",
        "emoji": "▸",
        "points": POINTS_TABLE["achievement_rare"],
    },
    "tasks_completed_100": {
        "name": "Системный подход",
        "description": "Выполнить 100 задач",
        "condition": {"type": "tasks_completed", "value": 100},
        "rarity": "epic",
        "emoji": "◆",
        "points": POINTS_TABLE["achievement_epic"],
    },
    # === ВРЕДНЫЕ ПРИВЫЧКИ ===
    "bad_habit_free_7": {
        "name": "Первая неделя",
        "description": "7 дней без вредной привычки",
        "condition": {"type": "bad_habit_free", "value": 7},
        "rarity": "common",
        "emoji": "•",
        "points": POINTS_TABLE["achievement_common"],
    },
    "bad_habit_free_30": {
        "name": "Месяц контроля",
        "description": "30 дней без вредной привычки",
        "condition": {"type": "bad_habit_free", "value": 30},
        "rarity": "rare",
        "emoji": "▸",
        "points": POINTS_TABLE["achievement_rare"],
    },
    "bad_habit_free_100": {
        "name": "Победа над собой",
        "description": "100 дней без вредной привычки",
        "condition": {"type": "bad_habit_free", "value": 100},
        "rarity": "epic",
        "emoji": "◆",
        "points": POINTS_TABLE["achievement_epic"],
    },
    # === ПЕРВЫЕ ШАГИ ===
    "first_habit": {
        "name": "Начало пути",
        "description": "Создать первую привычку",
        "condition": {"type": "first_action", "value": "habit"},
        "rarity": "common",
        "emoji": "•",
        "points": POINTS_TABLE["achievement_common"],
    },
    "first_focus": {
        "name": "Первый фокус",
        "description": "Завершить первую фокус-сессию",
        "condition": {"type": "first_action", "value": "focus"},
        "rarity": "common",
        "emoji": "•",
        "points": POINTS_TABLE["achievement_common"],
    },
    "first_task": {
        "name": "Первая задача",
        "description": "Выполнить первую задачу",
        "condition": {"type": "first_action", "value": "task"},
        "rarity": "common",
        "emoji": "•",
        "points": POINTS_TABLE["achievement_common"],
    },
    # === КОМБО И ОСОБЫЕ ===
    "all_modules_used": {
        "name": "Комплексный подход",
        "description": "Использовать все модули бота",
        "condition": {"type": "special", "value": "all_modules"},
        "rarity": "rare",
        "emoji": "▸",
        "points": POINTS_TABLE["achievement_rare"],
    },
    "early_bird": {
        "name": "Раннее начало",
        "description": "Выполнить задачу до 7 утра",
        "condition": {"type": "special", "value": "early_bird"},
        "rarity": "common",
        "emoji": "•",
        "points": POINTS_TABLE["achievement_common"],
    },
    "night_owl": {
        "name": "Ночная работа",
        "description": "Фокус-сессия после полуночи",
        "condition": {"type": "special", "value": "night_owl"},
        "rarity": "common",
        "emoji": "•",
        "points": POINTS_TABLE["achievement_common"],
    },
}


def get_achievement_message(achievement_id: str) -> str:
    """
    Возвращает поздравительное сообщение для достижения
    """
    achievement = ACHIEVEMENTS.get(achievement_id)
    if not achievement:
        return ""

    emoji = achievement["emoji"]
    name = achievement["name"]
    description = achievement["description"]
    points = achievement["points"]

    rarity_messages = {
        "common": "Новое достижение",
        "rare": "Редкое достижение",
        "epic": "Особое достижение",
        "legendary": "Выдающееся достижение",
    }

    rarity = achievement.get("rarity", "common")
    header = rarity_messages.get(rarity, "Новое достижение")

    return f"🏆 <b>{header}</b>\n\n" f"{name}\n" f"{description}\n\n" f"Награда: {points} очков"


def get_rarity_color(rarity: str) -> str:
    """
    Возвращает цвет для редкости достижения
    """
    colors = {
        "common": "#9CA3AF",  # Серый
        "rare": "#3B82F6",  # Синий
        "epic": "#8B5CF6",  # Фиолетовый
        "legendary": "#F59E0B",  # Золотой
    }
    return colors.get(rarity, "#9CA3AF")


def calculate_points_for_task(priority: str) -> int:
    """
    Рассчитывает очки за выполнение задачи в зависимости от приоритета
    """
    points_map = {
        "urgent_important": POINTS_TABLE["task_urgent_important"],
        "not_urgent_important": POINTS_TABLE["task_not_urgent_important"],
        "urgent_not_important": POINTS_TABLE["task_urgent_not_important"],
        "not_urgent_not_important": POINTS_TABLE["task_not_urgent_not_important"],
    }
    return points_map.get(priority, 5)


def get_level_from_points(total_points: int) -> Tuple[int, int, int]:
    """
    Рассчитывает уровень по общему количеству очков

    Returns:
        Tuple[int, int, int]: (уровень, очки на текущем уровне, очки до следующего уровня)
    """
    # Формула: каждый уровень требует на 50 очков больше предыдущего
    # Уровень 1: 100 очков
    # Уровень 2: 150 очков
    # Уровень 3: 200 очков и т.д.

    level = 1
    points_for_current_level = 0
    points_for_next_level = 100

    while total_points >= points_for_next_level:
        level += 1
        points_for_current_level = points_for_next_level
        points_for_next_level += 50 * level

    points_in_level = total_points - points_for_current_level
    points_to_next = points_for_next_level - total_points

    return level, points_in_level, points_to_next


def get_rank_by_level(level: int) -> str:
    """
    Возвращает ранг по уровню
    """
    ranks = {
        (1, 5): "Новичок",
        (6, 10): "Практик",
        (11, 20): "Специалист",
        (21, 30): "Эксперт",
        (31, 50): "Мастер",
        (51, 75): "Гуру",
        (76, 100): "Легенда",
    }

    for (min_level, max_level), rank in ranks.items():
        if min_level <= level <= max_level:
            return rank

    return "Легенда"  # Для уровней выше 100


def check_achievements_for_user(user_stats: Dict) -> List[str]:
    """
    Проверяет, какие достижения может разблокировать пользователь

    Args:
        user_stats: Словарь со статистикой пользователя

    Returns:
        List[str]: Список ID достижений, которые можно разблокировать
    """
    unlockable = []

    for achievement_id, achievement in ACHIEVEMENTS.items():
        condition = achievement["condition"]
        condition_type = condition["type"]
        required_value = condition["value"]

        # Проверяем разные типы условий
        if condition_type == "habit_streak":
            # Проверяем максимальный streak среди всех привычек
            max_streak = user_stats.get("max_habit_streak", 0)
            if max_streak >= required_value:
                unlockable.append(achievement_id)

        elif condition_type == "focus_sessions":
            # Проверяем количество завершенных сессий
            sessions = user_stats.get("total_focus_sessions", 0)
            if sessions >= required_value:
                unlockable.append(achievement_id)

        elif condition_type == "focus_hours":
            # Проверяем общее время в фокусе
            minutes = user_stats.get("total_focus_minutes", 0)
            hours = minutes / 60
            if hours >= required_value:
                unlockable.append(achievement_id)

        elif condition_type == "tasks_completed":
            # Проверяем количество выполненных задач
            tasks = user_stats.get("total_tasks_completed", 0)
            if tasks >= required_value:
                unlockable.append(achievement_id)

        elif condition_type == "bad_habit_free":
            # Проверяем максимальные дни без вредной привычки
            max_days = user_stats.get("max_bad_habit_free_days", 0)
            if max_days >= required_value:
                unlockable.append(achievement_id)

        elif condition_type == "first_action":
            # Проверяем первые действия
            action = condition["value"]
            if action == "habit" and user_stats.get("has_habits", False):
                unlockable.append(achievement_id)
            elif action == "focus" and user_stats.get("has_focus_sessions", False):
                unlockable.append(achievement_id)
            elif action == "task" and user_stats.get("has_tasks", False):
                unlockable.append(achievement_id)

        elif condition_type == "special":
            # Специальные достижения
            special_type = condition["value"]
            if special_type == "all_modules" and user_stats.get("used_all_modules", False):
                unlockable.append(achievement_id)
            elif special_type == "early_bird" and user_stats.get(
                "completed_task_before_7am", False
            ):
                unlockable.append(achievement_id)
            elif special_type == "night_owl" and user_stats.get(
                "focus_session_after_midnight", False
            ):
                unlockable.append(achievement_id)

    return unlockable


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

        condition = achievement["condition"]
        condition_type = condition["type"]
        required_value = condition["value"]

        # Проверяем разные типы условий
        if condition_type == "habit_streak":
            max_streak = user_stats.get("max_habit_streak", 0)
            if max_streak >= required_value:
                unlockable.append(achievement_id)

        elif condition_type == "focus_sessions":
            total_sessions = user_stats.get("total_focus_sessions", 0)
            if total_sessions >= required_value:
                unlockable.append(achievement_id)

        elif condition_type == "focus_hours":
            total_minutes = user_stats.get("total_focus_minutes", 0)
            total_hours = total_minutes // 60
            if total_hours >= required_value:
                unlockable.append(achievement_id)

        elif condition_type == "tasks_completed":
            total_tasks = user_stats.get("total_tasks_completed", 0)
            if total_tasks >= required_value:
                unlockable.append(achievement_id)

        elif condition_type == "points_earned":
            total_points = user_stats.get("total_points_earned", 0)
            if total_points >= required_value:
                unlockable.append(achievement_id)

        elif condition_type == "bad_habit_days":
            max_days = user_stats.get("max_bad_habit_days", 0)
            if max_days >= required_value:
                unlockable.append(achievement_id)

        elif condition_type == "checklist_streak":
            checklist_streak = user_stats.get("max_checklist_streak", 0)
            if checklist_streak >= required_value:
                unlockable.append(achievement_id)

    return unlockable
