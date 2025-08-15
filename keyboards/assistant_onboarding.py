"""
Клавиатуры для онбординга ИИ-ассистента
"""
from typing import List, Dict, Optional
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_onboarding_start_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура начала онбординга"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="🚀 Начать настройку",
            callback_data="ai_assistant_start"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="ℹ️ Как это работает?",
            callback_data="ai_how_it_works"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="◀️ Назад",
            callback_data="assistant_menu"
        )
    )
    
    return builder.as_markup()

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


def get_category_selection_keyboard(categories: Dict[str, Dict]) -> InlineKeyboardMarkup:
    """Клавиатура выбора категории с описаниями"""
    builder = InlineKeyboardBuilder()
    
    for category_id, category_data in categories.items():
        builder.row(
            InlineKeyboardButton(
                text=f"{category_data['emoji']} {category_data['title']}",
                callback_data=f"onb_category_{category_id}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(
            text="❓ Помощь в выборе",
            callback_data="onb_help_choose"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="◀️ Назад",
            callback_data="assistant_menu"
        )
    )
    
    return builder.as_markup()


def get_progress_keyboard(current: int, total: int) -> InlineKeyboardMarkup:
    """Клавиатура с прогрессом"""
    builder = InlineKeyboardBuilder()
    
    # Прогресс бар
    progress = int((current / total) * 10)
    progress_bar = "█" * progress + "░" * (10 - progress)
    
    builder.row(
        InlineKeyboardButton(
            text=f"[{progress_bar}] {current}/{total}",
            callback_data="progress"
        )
    )
    
    return builder.as_markup()


def get_skip_or_back_keyboard(can_skip: bool = True) -> InlineKeyboardMarkup:
    """Клавиатура с опциями пропуска и возврата"""
    builder = InlineKeyboardBuilder()
    
    buttons = []
    if can_skip:
        buttons.append(
            InlineKeyboardButton(
                text="Пропустить ➡️",
                callback_data="onb_skip_current"
            )
        )
    
    buttons.append(
        InlineKeyboardButton(
            text="◀️ Назад",
            callback_data="onb_previous_question"
        )
    )
    
    builder.row(*buttons)
    
    builder.row(
        InlineKeyboardButton(
            text="❌ Отмена",
            callback_data="onb_cancel"
        )
    )
    
    return builder.as_markup()


def get_time_selection_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для быстрого выбора времени"""
    builder = InlineKeyboardBuilder()
    
    # Утренние часы
    morning_times = ["06:00", "07:00", "08:00", "09:00"]
    builder.row(*[
        InlineKeyboardButton(text=time, callback_data=f"onb_time_{time}")
        for time in morning_times
    ])
    
    # Дневные часы
    day_times = ["10:00", "11:00", "12:00", "13:00"]
    builder.row(*[
        InlineKeyboardButton(text=time, callback_data=f"onb_time_{time}")
        for time in day_times
    ])
    
    # Вечерние часы
    evening_times = ["18:00", "19:00", "20:00", "21:00"]
    builder.row(*[
        InlineKeyboardButton(text=time, callback_data=f"onb_time_{time}")
        for time in evening_times
    ])
    
    builder.row(
        InlineKeyboardButton(
            text="✏️ Ввести вручную",
            callback_data="onb_time_manual"
        )
    )
    
    return builder.as_markup()


def get_date_quick_select_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для быстрого выбора даты"""
    from datetime import date, timedelta
    
    builder = InlineKeyboardBuilder()
    today = date.today()
    
    # Быстрые опции
    options = [
        ("Через неделю", 7),
        ("Через 2 недели", 14),
        ("Через месяц", 30),
        ("Через 2 месяца", 60),
        ("Через 3 месяца", 90)
    ]
    
    for label, days in options:
        target_date = today + timedelta(days=days)
        builder.row(
            InlineKeyboardButton(
                text=f"{label} ({target_date.strftime('%d.%m.%Y')})",
                callback_data=f"onb_date_{target_date.isoformat()}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(
            text="📅 Выбрать другую дату",
            callback_data="onb_date_manual"
        )
    )
    
    return builder.as_markup()


def get_number_quick_select_keyboard(min_val: int, max_val: int, step: int = 1, unit: str = "") -> InlineKeyboardMarkup:
    """Клавиатура для быстрого выбора числа"""
    builder = InlineKeyboardBuilder()
    
    # Генерируем опции
    options = []
    current = min_val
    while current <= max_val and len(options) < 8:
        options.append(current)
        if current < 5:
            current += 1
        elif current < 30:
            current += 5
        elif current < 60:
            current += 10
        else:
            current += 30
    
    # Добавляем кнопки
    for i in range(0, len(options), 4):
        row_options = options[i:i+4]
        builder.row(*[
            InlineKeyboardButton(
                text=f"{opt}{unit}",
                callback_data=f"onb_number_{opt}"
            )
            for opt in row_options
        ])
    
    builder.row(
        InlineKeyboardButton(
            text="✏️ Ввести вручную",
            callback_data="onb_number_manual"
        )
    )
    
    return builder.as_markup()


def get_help_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура помощи"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="📚 Экзамены",
            callback_data="onb_help_exam"
        ),
        InlineKeyboardButton(
            text="🎯 Навыки",
            callback_data="onb_help_skill"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🌱 Привычки",
            callback_data="onb_help_habit"
        ),
        InlineKeyboardButton(
            text="💪 Здоровье",
            callback_data="onb_help_health"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="⏰ Время",
            callback_data="onb_help_time"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="◀️ Назад к выбору",
            callback_data="ai_assistant_start"
        )
    )
    
    return builder.as_markup()


def get_example_keyboard(category: str) -> InlineKeyboardMarkup:
    """Клавиатура с примерами для категории"""
    builder = InlineKeyboardBuilder()
    
    examples = {
        "exam": [
            ("ЕГЭ по математике", "ЕГЭ математика"),
            ("IELTS/TOEFL", "IELTS"),
            ("Экзамен в автошколе", "Автошкола"),
            ("Профессиональная сертификация", "Сертификация")
        ],
        "skill": [
            ("Программирование", "Программирование"),
            ("Иностранный язык", "Язык"),
            ("Музыкальный инструмент", "Музыка"),
            ("Рисование", "Рисование")
        ],
        "habit": [
            ("Медитация", "Медитация"),
            ("Чтение книг", "Чтение"),
            ("Утренняя зарядка", "Зарядка"),
            ("Правильное питание", "Питание")
        ],
        "health": [
            ("Похудение", "Похудение"),
            ("Набор мышечной массы", "Мышцы"),
            ("Подготовка к марафону", "Марафон"),
            ("Йога и гибкость", "Йога")
        ],
        "time": [
            ("Борьба с прокрастинацией", "Прокрастинация"),
            ("Баланс работа/жизнь", "Баланс"),
            ("Эффективное планирование", "Планирование"),
            ("Фокус и концентрация", "Фокус")
        ]
    }
    
    if category in examples:
        for label, value in examples[category]:
            builder.row(
                InlineKeyboardButton(
                    text=f"→ {label}",
                    callback_data=f"onb_example_{category}_{value}"
                )
            )
    
    builder.row(
        InlineKeyboardButton(
            text="✏️ Свой вариант",
            callback_data=f"onb_custom_{category}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="◀️ Назад",
            callback_data="ai_assistant_start"
        )
    )
    
    return builder.as_markup()


def get_error_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура при ошибке"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="🔄 Попробовать снова",
            callback_data="onb_retry"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="💬 Связаться с поддержкой",
            callback_data="support"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="◀️ В меню",
            callback_data="assistant_menu"
        )
    )
    
    return builder.as_markup()