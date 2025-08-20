"""
Клавиатуры для модуля трекинга привычек
"""

from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from typing import List, Dict


def get_tracker_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Главное меню трекера привычек
    """
    builder = InlineKeyboardBuilder()

    builder.row(InlineKeyboardButton(text="+ Добавить привычку", callback_data="add_habit"))
    builder.row(
        InlineKeyboardButton(text="Мои привычки", callback_data="my_habits"),
        InlineKeyboardButton(text="Воздержание", callback_data="bad_habits"),
    )
    builder.row(
        InlineKeyboardButton(text="📊 Статистика", callback_data="tracker_stats"),
        InlineKeyboardButton(text="Справка", callback_data="tracker_help"),
    )
    builder.row(InlineKeyboardButton(text="◀ Назад в меню", callback_data="back_to_main"))

    return builder.as_markup()


def get_habit_detail_keyboard(
    habit_id: str, is_completed_today: bool = False
) -> InlineKeyboardMarkup:
    """
    Клавиатура для деталей привычки
    """
    builder = InlineKeyboardBuilder()

    if not is_completed_today:
        builder.row(
            InlineKeyboardButton(text="✓ Выполнить", callback_data=f"complete_habit:{habit_id}")
        )
    else:
        builder.row(
            InlineKeyboardButton(text="✓ Уже выполнено сегодня", callback_data="already_completed")
        )

    builder.row(
        InlineKeyboardButton(text="📊 История", callback_data=f"habit_history:{habit_id}"),
        InlineKeyboardButton(text="Удалить", callback_data=f"delete_habit:{habit_id}"),
    )
    builder.row(InlineKeyboardButton(text="◀ Назад", callback_data="my_habits"))

    return builder.as_markup()


def get_bad_habit_detail_keyboard(habit_id: str) -> InlineKeyboardMarkup:
    """
    Клавиатура для деталей вредной привычки
    """
    builder = InlineKeyboardBuilder()

    builder.row(InlineKeyboardButton(text="Срыв", callback_data=f"reset_bad_habit:{habit_id}"))
    builder.row(
        InlineKeyboardButton(text="📊 История", callback_data=f"bad_habit_history:{habit_id}"),
        InlineKeyboardButton(text="Удалить", callback_data=f"delete_bad_habit:{habit_id}"),
    )
    builder.row(InlineKeyboardButton(text="◀ Назад", callback_data="bad_habits"))

    return builder.as_markup()


def get_trackers_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Главное меню раздела Трекеры
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="✨ Мои привычки", callback_data="my_habits"),
        InlineKeyboardButton(text="🚫 Воздержание", callback_data="bad_habits"),
    )
    builder.row(InlineKeyboardButton(text="➕ Добавить привычку", callback_data="add_habit"))
    builder.row(InlineKeyboardButton(text="◀️ Назад в меню", callback_data="back_to_main"))

    return builder.as_markup()


def get_habit_type_keyboard() -> InlineKeyboardMarkup:
    """
    Выбор типа привычки при создании
    """
    builder = InlineKeyboardBuilder()

    builder.row(InlineKeyboardButton(text="✅ Полезная привычка", callback_data="habit_type:good"))
    builder.row(InlineKeyboardButton(text="🚫 Вредная привычка", callback_data="habit_type:bad"))
    builder.row(
        InlineKeyboardButton(text="📋 Выбрать из пресетов", callback_data="habit_type:preset")
    )
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_habit_creation"))

    return builder.as_markup()


def get_habits_list_keyboard(habits: List[Dict], habit_type: str = "good") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for habit in habits:
        habit_id = habit.get("id", habit.get("habit_id"))  # ← убедитесь что получаем правильный id
        name = habit.get("name", "Без названия")
        emoji = habit.get("emoji", "▸")

        callback_data = (
            f"habit_detail:{habit_id}" if habit_type == "good" else f"bad_habit_detail:{habit_id}"
        )

        builder.row(InlineKeyboardButton(text=f"{emoji} {name}", callback_data=callback_data))

    # Кнопка назад
    builder.row(InlineKeyboardButton(text="◀ Назад", callback_data="tracker_menu"))

    # Кнопка добавления новой привычки
    if habit_type == "good":
        builder.row(InlineKeyboardButton(text="➕ Добавить привычку", callback_data="add_habit"))
    else:
        builder.row(
            InlineKeyboardButton(text="➕ Добавить вредную привычку", callback_data="add_bad_habit")
        )

    # Кнопка назад
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="trackers_menu"))

    return builder.as_markup()


def get_habit_actions_keyboard(
    habit_id: str, completed_today: bool = False
) -> InlineKeyboardMarkup:
    """
    Действия с конкретной привычкой
    """
    builder = InlineKeyboardBuilder()

    if not completed_today:
        builder.row(
            InlineKeyboardButton(
                text="✅ Выполнено сегодня", callback_data=f"complete_habit:{habit_id}"
            )
        )
    else:
        builder.row(
            InlineKeyboardButton(text="✔️ Уже выполнено сегодня", callback_data="already_completed")
        )

    builder.row(
        InlineKeyboardButton(text="📊 История", callback_data=f"habit_history:{habit_id}"),
        InlineKeyboardButton(text="🗑 Удалить", callback_data=f"delete_habit:{habit_id}"),
    )
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="my_habits"))

    return builder.as_markup()


def get_bad_habit_actions_keyboard(habit_id: str) -> InlineKeyboardMarkup:
    """
    Действия с вредной привычкой
    """
    builder = InlineKeyboardBuilder()

    builder.row(InlineKeyboardButton(text="💔 Срыв", callback_data=f"reset_bad_habit:{habit_id}"))
    builder.row(
        InlineKeyboardButton(text="📊 История", callback_data=f"bad_habit_history:{habit_id}"),
        InlineKeyboardButton(text="🗑 Удалить", callback_data=f"delete_bad_habit:{habit_id}"),
    )
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="bad_habits"))

    return builder.as_markup()


def get_preset_habits_keyboard() -> InlineKeyboardMarkup:
    """
    Пресеты полезных привычек
    """
    builder = InlineKeyboardBuilder()

    presets = [
        ("💧 Пить воду", "preset:water"),
        ("🏃 Утренняя зарядка", "preset:exercise"),
        ("📚 Чтение", "preset:reading"),
        ("🧘 Медитация", "preset:meditation"),
        ("🌅 Ранний подъем", "preset:early_rise"),
        ("🥗 Здоровое питание", "preset:healthy_food"),
        ("🚶 Прогулка", "preset:walk"),
        ("📝 Дневник", "preset:journal"),
        ("🎯 Планирование дня", "preset:planning"),
        ("💤 Режим сна", "preset:sleep"),
    ]

    # Добавляем пресеты по 2 в ряд
    for i in range(0, len(presets), 2):
        if i + 1 < len(presets):
            builder.row(
                InlineKeyboardButton(text=presets[i][0], callback_data=presets[i][1]),
                InlineKeyboardButton(text=presets[i + 1][0], callback_data=presets[i + 1][1]),
            )
        else:
            builder.row(InlineKeyboardButton(text=presets[i][0], callback_data=presets[i][1]))

    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_habit_creation"))

    return builder.as_markup()


def get_frequency_keyboard() -> ReplyKeyboardMarkup:
    """
    Клавиатура для выбора частоты привычки
    """
    builder = ReplyKeyboardBuilder()

    frequencies = [
        "Ежедневно",
        "Через день",
        "2 раза в неделю",
        "3 раза в неделю",
        "По будням",
        "По выходным",
    ]

    for freq in frequencies:
        builder.add(KeyboardButton(text=freq))

    builder.adjust(2)

    return builder.as_markup(resize_keyboard=True)


def get_confirmation_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура подтверждения действия
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="✅ Да", callback_data="confirm_yes"),
        InlineKeyboardButton(text="❌ Нет", callback_data="confirm_no"),
    )

    return builder.as_markup()


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """
    Клавиатура с кнопкой отмены
    """
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="❌ Отмена"))
    return builder.as_markup(resize_keyboard=True)
