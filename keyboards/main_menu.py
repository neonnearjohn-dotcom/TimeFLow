"""
Клавиатуры для главного меню бота
"""

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """
    Создает клавиатуру главного меню

    Returns:
        ReplyKeyboardMarkup: Клавиатура с кнопками главного меню
    """
    # Используем ReplyKeyboardBuilder для удобного создания клавиатуры
    builder = ReplyKeyboardBuilder()

    # Добавляем кнопки в две колонки
    buttons = [
        KeyboardButton(text="📊 Трекеры"),
        KeyboardButton(text="✓ Чек-лист"),
        KeyboardButton(text="⏱ Фокус"),
        KeyboardButton(text="💬 Ассистент"),
        KeyboardButton(text="👤 Профиль"),
        KeyboardButton(text="⚙ Настройки"),
    ]

    # Добавляем кнопки по 2 в ряд
    for button in buttons:
        builder.add(button)

    # Устанавливаем размещение кнопок: 2 кнопки в ряд
    builder.adjust(2)

    # Возвращаем клавиатуру с параметром resize_keyboard для адаптации размера
    return builder.as_markup(resize_keyboard=True)


def get_skip_keyboard() -> ReplyKeyboardMarkup:
    """
    Создает клавиатуру с кнопкой "Пропустить"

    Returns:
        ReplyKeyboardMarkup: Клавиатура с кнопкой пропуска
    """
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="Пропустить"))
    return builder.as_markup(resize_keyboard=True)


def main_menu_kb() -> InlineKeyboardMarkup:
    """Клавиатура главного меню"""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="📊 Трекеры", callback_data="trackers"),
        InlineKeyboardButton(text="✓ Чек-лист", callback_data="checklist"),
    )
    builder.row(
        InlineKeyboardButton(text="⏱ Фокус", callback_data="focus"),
        InlineKeyboardButton(text="💬 Ассистент", callback_data="assistant"),
    )
    builder.row(
        InlineKeyboardButton(text="👤 Профиль", callback_data="profile"),
        InlineKeyboardButton(text="⚙ Настройки", callback_data="settings"),
    )
    """
Клавиатуры для модуля чек-листа
"""


from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from typing import List, Dict, Any, Optional


def get_checklist_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное меню чек-листа"""
    builder = InlineKeyboardBuilder()

    builder.row(InlineKeyboardButton(text="Новая задача", callback_data="add_task"))
    builder.row(
        InlineKeyboardButton(text="Активные задачи", callback_data="active_tasks"),
        InlineKeyboardButton(text="Выполненные", callback_data="completed_tasks"),
    )
    builder.row(InlineKeyboardButton(text="Все задачи", callback_data="all_tasks"))
    builder.row(InlineKeyboardButton(text="◀ В главное меню", callback_data="back_to_main"))

    return builder.as_markup()


def get_priority_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора приоритета задачи"""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="● Важно и срочно", callback_data="priority:urgent_important")
    )
    builder.row(
        InlineKeyboardButton(
            text="● Важно, но не срочно", callback_data="priority:not_urgent_important"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="● Срочно, но не важно", callback_data="priority:urgent_not_important"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="● Не важно и не срочно", callback_data="priority:not_urgent_not_important"
        )
    )
    builder.row(InlineKeyboardButton(text="Отмена", callback_data="cancel_task_creation"))

    return builder.as_markup()


def get_tasks_list_keyboard(
    tasks: List[Dict[str, Any]], task_type: str = "all"
) -> InlineKeyboardMarkup:
    """Клавиатура со списком задач"""
    builder = InlineKeyboardBuilder()

    if not tasks:
        builder.row(InlineKeyboardButton(text="Нет задач", callback_data="no_tasks"))
    else:
        for task in tasks:
            priority_symbol = get_priority_symbol(task.get("priority"))
            status = "✓" if task.get("is_completed") else "▸"
            title = task.get("title", "Без названия")

            builder.row(
                InlineKeyboardButton(
                    text=f"{status} {priority_symbol} {title}",
                    callback_data=f"task_detail:{task['id']}",
                )
            )

    builder.row(InlineKeyboardButton(text="◀ Назад", callback_data="checklist"))

    return builder.as_markup()


def get_task_actions_keyboard(task_id: str, is_completed: bool) -> InlineKeyboardMarkup:
    """Клавиатура действий с задачей"""
    builder = InlineKeyboardBuilder()

    if not is_completed:
        builder.row(
            InlineKeyboardButton(text="✓ Выполнить", callback_data=f"complete_task:{task_id}")
        )
        builder.row(InlineKeyboardButton(text="Изменить", callback_data=f"edit_task:{task_id}"))

    builder.row(InlineKeyboardButton(text="Удалить", callback_data=f"delete_task:{task_id}"))
    builder.row(InlineKeyboardButton(text="◀ К задачам", callback_data="all_tasks"))

    return builder.as_markup()


def get_deadline_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора дедлайна"""
    builder = InlineKeyboardBuilder()

    builder.row(InlineKeyboardButton(text="Сегодня", callback_data="deadline:today"))
    builder.row(InlineKeyboardButton(text="Завтра", callback_data="deadline:tomorrow"))
    builder.row(InlineKeyboardButton(text="Через 3 дня", callback_data="deadline:3days"))
    builder.row(InlineKeyboardButton(text="Через неделю", callback_data="deadline:week"))
    builder.row(InlineKeyboardButton(text="Через месяц", callback_data="deadline:month"))
    builder.row(InlineKeyboardButton(text="Без дедлайна", callback_data="deadline:none"))
    builder.row(InlineKeyboardButton(text="Отмена", callback_data="cancel_task_creation"))

    return builder.as_markup()


def get_skip_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для пропуска шага"""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="Пропустить"))
    builder.add(KeyboardButton(text="Отмена"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)


def get_confirmation_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения действия"""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="Да", callback_data="confirm_yes"),
        InlineKeyboardButton(text="Нет", callback_data="confirm_no"),
    )

    return builder.as_markup()


def get_priority_symbol(priority: str) -> str:
    """Возвращает символ для приоритета"""
    priority_symbols = {
        "urgent_important": "●",
        "not_urgent_important": "○",
        "urgent_not_important": "◐",
        "not_urgent_not_important": "◯",
    }
    return priority_symbols.get(priority, "◦")


def get_priority_emoji(priority: str) -> str:
    """Возвращает эмодзи для приоритета (для обратной совместимости)"""
    return get_priority_symbol(priority)


def get_priority_name(priority: str) -> str:
    """Возвращает название приоритета"""
    priority_names = {
        "urgent_important": "Важно и срочно",
        "not_urgent_important": "Важно, но не срочно",
        "urgent_not_important": "Срочно, но не важно",
        "not_urgent_not_important": "Не важно и не срочно",
    }
    return priority_names.get(priority, "Без приоритета")
    return builder.as_markup()


InlineKeyboardButton(text="💬 Ассистент", callback_data="assistant")
