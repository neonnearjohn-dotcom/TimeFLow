"""
Клавиатуры для работы с планами ИИ-ассистента
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_plan_preview_keyboard(start_day: int, horizon_days: int) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для превью плана с навигацией
    
    Args:
        start_day: Начальный день для отображения
        horizon_days: Общее количество дней в плане
        
    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками навигации
    """
    buttons = []
    nav_row = []
    
    # Кнопка "Назад" (только если не на первой странице)
    if start_day > 1:
        nav_row.append(
            InlineKeyboardButton(
                text="◀️ Назад",
                callback_data=f"plan:prev:{start_day}"
            )
        )
    
    # Кнопка "Дальше" (только если есть еще дни)
    if start_day + 2 < horizon_days:  # +2 потому что показываем 3 дня
        nav_row.append(
            InlineKeyboardButton(
                text="Дальше ▶️",
                callback_data=f"plan:next:{start_day}"
            )
        )
    
    if nav_row:
        buttons.append(nav_row)
    
    # Кнопки действий
    action_row = [
        InlineKeyboardButton(
            text="💾 Сохранить план",
            callback_data="plan:save"
        ),
        InlineKeyboardButton(
            text="✖️ Отмена",
            callback_data="plan:cancel"
        )
    ]
    buttons.append(action_row)
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)




def get_plan_saved_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура после сохранения плана"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="📊 Мой прогресс",
                callback_data="ai_progress"
            )
        ],
        [
            InlineKeyboardButton(
                text="◀️ В меню ассистента",
                callback_data="assistant_menu"
            )
        ]
    ])
    return keyboard


def get_plan_generate_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с кнопкой генерации плана"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="📅 Сгенерировать план",
                callback_data="plan:generate"
            )
        ],
        [
            InlineKeyboardButton(
                text="◀️ Назад",
                callback_data="assistant_menu"
            )
        ]
    ])
    return keyboard

def get_plan_management_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура меню плана (когда план уже есть):
    - "📄 Просмотреть план"  -> callback: "plan:open_preview"
    - "🔄 Пересоздать план"  -> callback: "plan:regenerate"  
    - "⬅️ Назад"             -> callback: "plan:back"
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="📄 Просмотреть план",
                callback_data="plan:open_preview"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔄 Пересоздать план",
                callback_data="plan:regenerate"
            )
        ],
        [
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data="plan:back"
            )
        ]
    ])
    return keyboard