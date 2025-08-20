"""
Клавиатуры для модуля ИИ-ассистента
"""

from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder


def get_assistant_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Главное меню ИИ-ассистента
    """
    builder = InlineKeyboardBuilder()

    # Кнопка генерации/управления планом всегда видна
    builder.row(InlineKeyboardButton(text="📅 Сгенерировать план", callback_data="ai_plan_menu"))

    # Быстрые сценарии
    builder.row(InlineKeyboardButton(text="⚡ Быстрые сценарии", callback_data="quick_scenarios"))

    # Свободный чат
    builder.row(InlineKeyboardButton(text="💬 Свободный чат", callback_data="free_chat"))

    # История и статистика
    builder.row(
        InlineKeyboardButton(text="📜 История", callback_data="chat_history"),
    )

    # Выход
    builder.row(InlineKeyboardButton(text="❌ Закрыть", callback_data="exit_assistant"))

    return builder.as_markup()


def get_scenarios_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура с быстрыми сценариями
    """
    builder = InlineKeyboardBuilder()

    scenarios = [
        ("📅 План на день", "scenario:plan"),
        ("💪 Мотивация", "scenario:motivation"),
        ("🔄 Разбор неудачи", "scenario:failure"),
        ("🌱 Совет по привычкам", "scenario:habits"),
    ]

    for text, callback in scenarios:
        builder.row(InlineKeyboardButton(text=text, callback_data=callback))

    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="assistant_menu"))

    return builder.as_markup()


def get_exit_keyboard() -> ReplyKeyboardMarkup:
    """
    Клавиатура для выхода из режима ассистента
    """
    builder = ReplyKeyboardBuilder()

    builder.add(KeyboardButton(text="❌ Выйти из ассистента"))

    return builder.as_markup(resize_keyboard=True)


def get_back_to_scenarios_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура для возврата к сценариям после ответа
    """
    builder = InlineKeyboardBuilder()

    builder.row(InlineKeyboardButton(text="🎯 Другие сценарии", callback_data="quick_scenarios"))
    builder.row(InlineKeyboardButton(text="💬 Свободный чат", callback_data="free_chat"))
    builder.row(
        InlineKeyboardButton(text="◀️ Главное меню ассистента", callback_data="assistant_menu")
    )

    return builder.as_markup()


def get_chat_mode_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура для режима свободного чата
    """
    builder = InlineKeyboardBuilder()

    builder.row(InlineKeyboardButton(text="🎯 Быстрые сценарии", callback_data="quick_scenarios"))
    builder.row(InlineKeyboardButton(text="◀️ Назад к меню", callback_data="back_to_assistant"))
    builder.row(InlineKeyboardButton(text="❌ Выйти из ассистента", callback_data="exit_assistant"))

    return builder.as_markup()


def get_error_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура для сообщений об ошибках
    """
    builder = InlineKeyboardBuilder()

    builder.row(InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="assistant_menu"))
    builder.row(InlineKeyboardButton(text="❌ Выйти", callback_data="exit_assistant"))

    return builder.as_markup()


def get_demo_mode_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура для демо-режима
    """
    builder = InlineKeyboardBuilder()

    builder.row(InlineKeyboardButton(text="🎭 Попробовать демо", callback_data="quick_scenarios"))
    builder.row(InlineKeyboardButton(text="📖 Как настроить?", callback_data="setup_guide"))
    builder.row(InlineKeyboardButton(text="◀️ В главное меню", callback_data="exit_assistant"))

    return builder.as_markup()
