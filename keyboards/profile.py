"""
Клавиатуры для профиля и геймификации
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List, Dict


def get_profile_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Главное меню профиля
    """
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="🏆 Достижения", callback_data="view_achievements")
    )
    builder.row(
        InlineKeyboardButton(text="💰 История очков", callback_data="points_history")
    )
    builder.row(
        InlineKeyboardButton(text="📊 Статистика", callback_data="detailed_stats")
    )
    builder.row(
        InlineKeyboardButton(text="🔄 Обновить", callback_data="refresh_profile")
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад в меню", callback_data="back_to_main")
    )
    
    return builder.as_markup()


def get_achievements_keyboard(has_achievements: bool = True) -> InlineKeyboardMarkup:
    """
    Клавиатура для просмотра достижений
    """
    builder = InlineKeyboardBuilder()
    
    if has_achievements:
        builder.row(
            InlineKeyboardButton(text="🏅 Все достижения", callback_data="all_achievements")
        )
        builder.row(
            InlineKeyboardButton(text="📈 Прогресс", callback_data="achievements_progress")
        )
    
    builder.row(
        InlineKeyboardButton(text="◀️ Назад в профиль", callback_data="view_profile")
    )
    
    return builder.as_markup()


def get_achievement_details_keyboard(achievement_id: str) -> InlineKeyboardMarkup:
    """
    Клавиатура для деталей достижения
    """
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="📊 Поделиться", callback_data=f"share_achievement:{achievement_id}")
    )
    builder.row(
        InlineKeyboardButton(text="◀️ К достижениям", callback_data="view_achievements")
    )
    
    return builder.as_markup()


def get_stats_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура для статистики
    """
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="📈 По модулям", callback_data="stats_by_module")
    )
    builder.row(
        InlineKeyboardButton(text="🏆 Рекорды", callback_data="stats_records")
    )
    builder.row(
        InlineKeyboardButton(text="📅 За период", callback_data="stats_period")
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад в профиль", callback_data="view_profile")
    )
    
    return builder.as_markup()


def get_achievement_categories_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура категорий достижений
    """
    builder = InlineKeyboardBuilder()
    
    categories = [
        ("🌱 Привычки", "ach_cat:habits"),
        ("🎯 Фокус", "ach_cat:focus"),
        ("📋 Задачи", "ach_cat:tasks"),
        ("💪 Воздержание", "ach_cat:bad_habits"),
        ("⭐ Особые", "ach_cat:special")
    ]
    
    for name, callback in categories:
        builder.row(InlineKeyboardButton(text=name, callback_data=callback))
    
    builder.row(
        InlineKeyboardButton(text="🏅 Все достижения", callback_data="all_achievements")
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="view_achievements")
    )
    
    return builder.as_markup()


def get_back_to_profile_keyboard() -> InlineKeyboardMarkup:
    """
    Простая клавиатура возврата в профиль
    """
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="◀️ Назад в профиль", callback_data="view_profile")
    )
    
    return builder.as_markup()