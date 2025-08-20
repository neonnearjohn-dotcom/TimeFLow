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
    tasks: List[Dict[str, Any]], task_type: str = "all", page: int = 1, tasks_per_page: int = 10
) -> InlineKeyboardMarkup:
    """Клавиатура со списком задач с пагинацией"""
    builder = InlineKeyboardBuilder()

    if not tasks:
        builder.row(InlineKeyboardButton(text="Нет задач", callback_data="no_tasks"))
    else:
        # Вычисляем индексы для текущей страницы
        total_tasks = len(tasks)
        total_pages = (total_tasks + tasks_per_page - 1) // tasks_per_page
        start_idx = (page - 1) * tasks_per_page
        end_idx = min(start_idx + tasks_per_page, total_tasks)

        # Показываем задачи текущей страницы
        for task in tasks[start_idx:end_idx]:
            priority_symbol = get_priority_symbol(task.get("priority"))
            # Проверяем статус задачи
            status = "✓" if task.get("status") == "completed" else "▸"
            title = task.get("title", "Без названия")
            # Обрезаем слишком длинные названия
            if len(title) > 30:
                title = title[:27] + "..."

            builder.row(
                InlineKeyboardButton(
                    text=f"{status} {priority_symbol} {title}",
                    callback_data=f"task_detail:{task['id']}",
                )
            )

        # Добавляем кнопки навигации по страницам, если нужно
        if total_pages > 1:
            nav_buttons = []
            if page > 1:
                nav_buttons.append(
                    InlineKeyboardButton(
                        text="◀ Пред.", callback_data=f"tasks_page:{task_type}:{page-1}"
                    )
                )

            # Показываем номер текущей страницы
            nav_buttons.append(
                InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="current_page")
            )

            if page < total_pages:
                nav_buttons.append(
                    InlineKeyboardButton(
                        text="След. ▶", callback_data=f"tasks_page:{task_type}:{page+1}"
                    )
                )

            builder.row(*nav_buttons)

    builder.row(InlineKeyboardButton(text="◀ Назад", callback_data="checklist_menu"))

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


def get_edit_field_keyboard(task_id: str) -> InlineKeyboardMarkup:
    """Клавиатура выбора поля для редактирования"""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="📝 Название", callback_data=f"edit_field:title:{task_id}")
    )
    builder.row(
        InlineKeyboardButton(text="📄 Описание", callback_data=f"edit_field:description:{task_id}")
    )
    builder.row(
        InlineKeyboardButton(text="🎯 Приоритет", callback_data=f"edit_field:priority:{task_id}")
    )
    builder.row(
        InlineKeyboardButton(text="📅 Дедлайн", callback_data=f"edit_field:deadline:{task_id}")
    )
    builder.row(InlineKeyboardButton(text="◀ Отмена", callback_data=f"task_detail:{task_id}"))

    return builder.as_markup()


def get_cancel_edit_keyboard(task_id: str) -> ReplyKeyboardMarkup:
    """Клавиатура отмены редактирования"""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="Отмена"))
    return builder.as_markup(resize_keyboard=True)
