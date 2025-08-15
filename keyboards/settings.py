"""
Клавиатуры для раздела настроек
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import Dict, Any


def get_settings_keyboard(settings: Dict[str, Any]) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру настроек
    
    Args:
        settings: Текущие настройки пользователя
        
    Returns:
        InlineKeyboardMarkup с кнопками настроек
    """
    builder = InlineKeyboardBuilder()
    
    # Кнопка уведомлений
    notifications_text = "🔔 Уведомления: " + ("Вкл ✅" if settings['notifications_enabled'] else "Выкл ❌")
    builder.row(
        InlineKeyboardButton(
            text=notifications_text,
            callback_data="toggle_notifications"
        )
    )
    
    # Кнопки выбора темы
    theme_buttons = []
    themes = [
        ('system', '📱 System'),
        ('light', '☀️ Light'),
        ('dark', '🌙 Dark')
    ]
    
    current_theme = settings.get('theme', 'system')
    
    for theme_value, theme_text in themes:
        # Добавляем галочку к текущей теме
        button_text = theme_text
        if theme_value == current_theme:
            button_text += " ✓"
        
        theme_buttons.append(
            InlineKeyboardButton(
                text=button_text,
                callback_data=f"set_theme:{theme_value}"
            )
        )
    
    # Добавляем заголовок для темы
    builder.row(
        InlineKeyboardButton(
            text="🎨 Тема оформления:",
            callback_data="theme_header"  # Неактивная кнопка-заголовок
        )
    )
    
    # Добавляем кнопки темы в один ряд
    builder.row(*theme_buttons)
    
    # Кнопка возврата
    builder.row(
        InlineKeyboardButton(
            text="🔙 Назад в меню",
            callback_data="settings_back_to_main"
        )
    )
    
    return builder.as_markup()