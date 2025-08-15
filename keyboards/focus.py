"""
Клавиатуры для модуля фокусировки
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import Optional, Dict, Any, List


def get_focus_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное меню модуля Фокус"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="🚀 Начать фокус", callback_data="start_focus")
    )
    builder.row(
        InlineKeyboardButton(text="⚙️ Настройки", callback_data="focus_settings"),
        InlineKeyboardButton(text="📊 Статистика", callback_data="focus_stats")
    )
    builder.row(
        InlineKeyboardButton(text="❓ Помощь", callback_data="focus_help")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_main")
    )
    
    return builder.as_markup()


def get_session_control_keyboard(is_paused: bool = False) -> InlineKeyboardMarkup:
    """Управление активной сессией"""
    builder = InlineKeyboardBuilder()
    
    if is_paused:
        builder.row(
            InlineKeyboardButton(text="▶️ Продолжить", callback_data="resume_focus"),
            InlineKeyboardButton(text="⏹ Завершить", callback_data="stop_focus")
        )
    else:
        builder.row(
            InlineKeyboardButton(text="⏸ Пауза", callback_data="pause_focus"),
            InlineKeyboardButton(text="⏹ Завершить", callback_data="stop_focus")
        )
    
    return builder.as_markup()


def get_focus_settings_keyboard(settings: Dict[str, Any]) -> InlineKeyboardMarkup:
    """Настройки фокус-сессий"""
    builder = InlineKeyboardBuilder()
    
    # Длительности
    builder.row(
        InlineKeyboardButton(
            text=f"⏱ Работа: {settings['work_duration']} мин",
            callback_data="set_duration:work"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=f"☕ Короткий перерыв: {settings['short_break_duration']} мин",
            callback_data="set_duration:short_break"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=f"🌴 Длинный перерыв: {settings['long_break_duration']} мин",
            callback_data="set_duration:long_break"
        )
    )
    
    # notifications removed - убрана кнопка уведомлений
    
    # Автоматический переход на перерыв
    auto_break_emoji = "✅" if settings['auto_start_break'] else "❌"
    builder.row(
        InlineKeyboardButton(
            text=f"🔄 Авто-перерыв: {auto_break_emoji}",
            callback_data="toggle_auto_break"
        )
    )
    
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="focus")
    )
    
    return builder.as_markup()


def get_duration_presets_keyboard(duration_type: str, presets: List[int]) -> InlineKeyboardMarkup:
    """Клавиатура с пресетами длительности"""
    builder = InlineKeyboardBuilder()
    
    # Создаем кнопки для каждого пресета
    buttons = []
    for minutes in presets:
        buttons.append(
            InlineKeyboardButton(
                text=f"{minutes} мин",
                callback_data=f"duration:{duration_type}:{minutes}"
            )
        )
    
    # Размещаем по 3 кнопки в ряд
    for i in range(0, len(buttons), 3):
        builder.row(*buttons[i:i+3])
    
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="focus_settings")
    )
    
    return builder.as_markup()


def get_stats_period_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора периода статистики"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="📅 Сегодня", callback_data="stats_period:today")
    )
    builder.row(
        InlineKeyboardButton(text="📅 За неделю", callback_data="stats_period:week")
    )
    builder.row(
        InlineKeyboardButton(text="📅 За месяц", callback_data="stats_period:month")
    )
    builder.row(
        InlineKeyboardButton(text="📅 За всё время", callback_data="stats_period:all")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="focus")
    )
    
    return builder.as_markup()


def get_session_complete_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура после завершения сессии"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="🚀 Новая сессия", callback_data="start_focus")
    )
    builder.row(
        InlineKeyboardButton(text="📊 Статистика", callback_data="focus_stats")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 В меню", callback_data="focus")
    )
    
    return builder.as_markup()