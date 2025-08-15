"""
Обработчики для модуля ИИ-ассистента
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import StateFilter, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from datetime import datetime, timezone
import logging
import asyncio

from database.firestore_db import FirestoreDB
from database.assistant_db import AssistantDB
from database.gamification_db import GamificationDB
from keyboards.assistant import (
    get_assistant_menu_keyboard,
    get_scenarios_keyboard,
    get_exit_keyboard,
    get_back_to_scenarios_keyboard,
    get_chat_mode_keyboard
)
from keyboards.main_menu import get_main_menu_keyboard
from states.assistant import AssistantStates
from utils.openai_api import OpenAIAssistant
from utils.messages import ERROR_MESSAGES
from utils.achievements import POINTS_TABLE

# Создаем роутер
router = Router()
logger = logging.getLogger(__name__)

# Инициализируем базу данных и ассистента
db = FirestoreDB()
assistant_db = AssistantDB(db.db)
gamification_db = GamificationDB(db.db)

# Используем глобальный экземпляр OpenAI Assistant
try:
    from utils.openai_api import assistant
    openai_assistant = assistant
except ImportError:
    openai_assistant = OpenAIAssistant()

# Сообщения для пользователя
ASSISTANT_MESSAGES = {
    'welcome': """
<b>💬 ИИ-ассистент</b>

Я помогу вам:
- 🎯 Создать персональный план достижения целей
- ⚡ Быстро решить типовые задачи
- 💭 Ответить на любые вопросы
- 📊 Отслеживать ваш прогресс

Выберите, что вас интересует:
""",
    
    'chat_mode': """
<b>💬 Режим свободного общения</b>

Задавайте любые вопросы! Я помогу с:
- 📋 Планированием и продуктивностью
- 🎯 Постановкой и достижением целей  
- 🌱 Формированием привычек
- 💪 Мотивацией и поддержкой
- 🧠 Анализом проблем и поиском решений

Просто напишите ваш вопрос!
""",
    
    'thinking': "Обрабатываю запрос...",
    
    'error_api': """
Не удалось получить ответ от ИИ.

Возможные причины:
• Превышен лимит запросов
• Проблемы с подключением
• Временная недоступность сервиса

Попробуйте позже или обратитесь к администратору.
""",
    
    'demo_mode': """
<b>Демо-режим</b>

Сейчас ассистент работает в демо-режиме с примерами ответов.

Для полноценной работы с ИИ необходимо:
1. Получить API ключ OpenAI
2. Добавить его в файл .env
3. Перезапустить бота

Пока можете посмотреть, как работают сценарии.
"""
}

# Примеры ответов для демо-режима
DEMO_RESPONSES = {
    'plan_day': """
<b>План на день</b>

Основываясь на вашем распорядке, рекомендую:

<b>Утро (7:00-12:00)</b>
• Утренняя рутина и завтрак
• Фокус-сессия на важную задачу (90 мин)
• Короткий перерыв

<b>День (12:00-18:00)</b>
• Обед и отдых
• Работа над текущими задачами
• Коммуникация и встречи

<b>Вечер (18:00-22:00)</b>
• Подведение итогов дня
• Личное время
• Планирование завтрашнего дня

Используйте технику Помодоро для поддержания концентрации.
""",
    
    'motivation': """
<b>Мотивация</b>

Каждый шаг вперед — это прогресс. Не сравнивайте себя с другими, сравнивайте с собой вчерашним.

Ваши сильные стороны:
• Стремление к развитию
• Готовность работать над собой
• Понимание важности систематичности

Помните: успех — это сумма маленьких усилий, повторяемых изо дня в день.

Начните с одного небольшого действия прямо сейчас.
""",
    
    'analyze_failure': """
<b>Анализ ситуации</b>

Срывы — это часть пути. Важно не то, что вы оступились, а то, что готовы продолжить.

Возможные причины:
• Слишком амбициозные цели
• Недостаток подготовки
• Внешние обстоятельства

Рекомендации:
1. Проанализируйте триггеры
2. Скорректируйте план
3. Начните с малого
4. Отслеживайте прогресс

Каждая попытка делает вас сильнее.
""",
    
    'habit_advice': """
<b>Советы по привычкам</b>

Эффективное формирование привычек:

1. <b>Начинайте с малого</b>
   Лучше 5 минут каждый день, чем час раз в неделю

2. <b>Привязывайте к существующим</b>
   Новая привычка после уже устоявшейся

3. <b>Создавайте триггеры</b>
   Время, место, предыдущее действие

4. <b>Отслеживайте прогресс</b>
   Визуальный прогресс мотивирует

5. <b>Будьте терпеливы</b>
   21-66 дней для формирования

Фокусируйтесь на процессе, а не на результате.
"""
}


# === ГЛАВНОЕ МЕНЮ АССИСТЕНТА ===



@router.message(F.text == "💬 Ассистент", StateFilter(default_state))
async def handle_assistant_menu(message: Message, state: FSMContext):
    """Обработчик кнопки Ассистент из главного меню"""
    # Проверяем наличие профиля для корректного отображения меню
    from database.firestore_db import FirestoreDB
    from database.assistant_profile_db import AssistantProfileDB
    
    db = FirestoreDB()
    profile_db = AssistantProfileDB(db.db)
    
    # Проверяем профиль пользователя
    profile = await profile_db.get_profile(message.from_user.id)
    
    # Определяем текст приветствия
    if not profile or not profile.onboarding.completed:
        welcome_text = (
            "<b>💬 ИИ-ассистент</b>\n\n"
            "Я помогу вам:\n"
            "- 🎯 Создать персональный план достижения целей\n"
            "- ⚡ Быстро решить типовые задачи\n"
            "- 💭 Ответить на любые вопросы\n"
            "- 📊 Отслеживать ваш прогресс\n\n"
            "Для начала нужно пройти быструю настройку."
        )
    else:
        welcome_text = (
            "<b>💬 ИИ-ассистент</b>\n\n"
            "Я помогу вам:\n"
            "- 🎯 Управлять вашим планом\n"
            "- ⚡ Быстро решить типовые задачи\n"
            "- 💭 Ответить на любые вопросы\n"
            "- 📊 Отслеживать ваш прогресс\n\n"
            "Выберите, что вас интересует:"
        )
    
    await message.answer(
        welcome_text,
        reply_markup=get_assistant_menu_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "assistant_menu")
async def show_assistant_menu(callback: CallbackQuery):
    """Показывает главное меню ассистента с проверкой наличия плана"""
    
    # Импортируем необходимые модули для проверки плана
    from handlers import assistant_onboarding
    
    # Получаем БД через функцию из assistant_onboarding
    _, profile_db = assistant_onboarding.get_db()
    
    # Проверяем наличие плана у пользователя
    has_plan = False
    if profile_db:
        profile = await profile_db.get_profile(callback.from_user.id)
        has_plan = profile and profile.plan is not None
    
    # Проверяем, есть ли API ключ
    if not openai_assistant.has_api_key():
        text = ASSISTANT_MESSAGES['demo_mode'] + "\n\n" + ASSISTANT_MESSAGES['welcome']
    else:
        text = ASSISTANT_MESSAGES['welcome']
    
    # Создаем клавиатуру
    builder = InlineKeyboardBuilder()
    
    # Если есть план, добавляем кнопку "Открыть мой план"
    if has_plan:
        builder.row(
            InlineKeyboardButton(
                text="📋 Посмотреть мой план",
                callback_data="ai_show_plan"
            )
        )
        # Добавляем отдельную кнопку для создания нового плана
        builder.row(
            InlineKeyboardButton(
                text="🔄 Создать новый план",
                callback_data="ai_create_new_plan"
            )
        )
    else:
        # Если плана нет - только кнопка создания
        builder.row(
            InlineKeyboardButton(
                text="🎯 Создать персональный план",
                callback_data="ai_assistant_start"
            )
        )
    
    # Быстрые сценарии
    builder.row(
        InlineKeyboardButton(
            text="⚡ Быстрые сценарии",
            callback_data="quick_scenarios"
        )
    )
    
    # Свободный чат
    builder.row(
        InlineKeyboardButton(
            text="💬 Свободный чат",
            callback_data="free_chat"
        )
    )
    
    # История и статистика
    builder.row(
        InlineKeyboardButton(
            text="📜 История",
            callback_data="chat_history"
        ),
        InlineKeyboardButton(
            text="📊 Статистика",
            callback_data="assistant_stats"
        )
    )
    
    # Выход
    builder.row(
        InlineKeyboardButton(
            text="❌ Закрыть",
            callback_data="exit_assistant"
        )
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()


# === ВЫБОР СЦЕНАРИЯ ===

@router.callback_query(F.data == "choose_scenario")
async def show_scenarios(callback: CallbackQuery):
    """Показывает список готовых сценариев"""
    await callback.message.edit_text(
        "<b>Готовые сценарии</b>\n\n"
        "Выберите, с чем вам помочь:",
        reply_markup=get_scenarios_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("scenario:"))
async def process_scenario(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает выбранный сценарий"""
    scenario = callback.data.split(":")[1]
    user_id = callback.from_user.id
    
    # Показываем индикатор обработки
    await callback.message.edit_text(
        ASSISTANT_MESSAGES['thinking'],
        parse_mode="HTML"
    )
    
    try:
        # Если нет API ключа - используем демо-ответы
        if not openai_assistant.has_api_key():
            await asyncio.sleep(1)  # Имитация задержки
            response_text = DEMO_RESPONSES.get(scenario, "Демо-ответ недоступен.")
        else:
            # Получаем историю диалога
            history = await assistant_db.get_chat_history(user_id)
            
            # Отправляем запрос к OpenAI
            response = await openai_assistant.send_message(
                message="",  # Для сценариев сообщение не нужно
                context=history,
                scenario=scenario
            )
            
            if response['success']:
                response_text = response['content']
                
                # Сохраняем в историю
                await assistant_db.add_message(
                    user_id,
                    "assistant",
                    response_text,
                    scenario=scenario
                )
                
                # Начисляем очки за использование ассистента (раз в день)
                last_use = await assistant_db.get_last_use_date(user_id)
                today = datetime.now(timezone.utc).date()
                
                if not last_use or last_use.date() < today:
                    await gamification_db.add_points(
                        user_id,
                        5,
                        'assistant_daily_use',
                        {'scenario': scenario}
                    )
                    await assistant_db.update_last_use_date(user_id)
            else:
                response_text = ASSISTANT_MESSAGES['error_api']
        
        # Отправляем ответ
        await callback.message.edit_text(
            response_text,
            reply_markup=get_back_to_scenarios_keyboard(),
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Ошибка при обработке сценария: {e}")
        await callback.message.edit_text(
            ASSISTANT_MESSAGES['error_api'],
            reply_markup=get_back_to_scenarios_keyboard(),
            parse_mode="HTML"
        )
    
    await callback.answer()


# === СВОБОДНЫЙ ЧАТ ===

@router.callback_query(F.data == "free_chat")
async def start_free_chat(callback: CallbackQuery, state: FSMContext):
    """Начинает режим свободного общения"""
    # Сначала отправляем сообщение о режиме чата с inline клавиатурой
    await callback.message.edit_text(
        ASSISTANT_MESSAGES['chat_mode'],
        reply_markup=get_chat_mode_keyboard(),  # Используем inline клавиатуру
        parse_mode="HTML"
    )
    
    # Затем отправляем обычную клавиатуру отдельным сообщением
    await callback.message.answer(
        "Для выхода из режима чата используйте кнопку ниже:",
        reply_markup=get_exit_keyboard()  # Теперь ReplyKeyboardMarkup отправляется правильно
    )
    
    # Устанавливаем состояние чата
    await state.set_state(AssistantStates.chat_mode)
    
    await callback.answer()

@router.callback_query(F.data == "ai_create_plan")
async def redirect_to_onboarding(callback: CallbackQuery, state: FSMContext):
    """Перенаправление на онбординг при нажатии 'Создать персональный план'"""
    from handlers import assistant_onboarding
    await assistant_onboarding.start_ai_onboarding(callback, state)


@router.callback_query(F.data == "ai_create_new_plan")
async def handle_create_new_plan(callback: CallbackQuery, state: FSMContext):
    """Обработчик для создания нового плана (с удалением старого)"""
    # Получаем БД
    from handlers import assistant_onboarding
    _, profile_db = assistant_onboarding.get_db()
    
    if not profile_db:
        await callback.answer("⚠️ База данных временно недоступна", show_alert=True)
        return
    
    # Проверяем наличие существующего плана
    profile = await profile_db.get_profile(callback.from_user.id)
    
    if profile and profile.plan:
        # Если план есть, спрашиваем подтверждение
        await callback.message.edit_text(
            "<b>⚠️ Создание нового плана</b>\n\n"
            "У вас уже есть активный план.\n"
            "При создании нового плана текущий будет удалён.\n\n"
            "Хотите продолжить?",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ Да, создать новый",
                        callback_data="ai_confirm_new_plan"
                    ),
                    InlineKeyboardButton(
                        text="❌ Нет, оставить текущий",
                        callback_data="assistant_menu"
                    )
                ]
            ]),
            parse_mode="HTML"
        )
    else:
        # Если плана нет, сразу начинаем онбординг
        from handlers import assistant_onboarding
        await assistant_onboarding.start_ai_onboarding(callback, state)
    
    await callback.answer()


@router.callback_query(F.data == "ai_confirm_new_plan")
async def handle_confirm_new_plan(callback: CallbackQuery, state: FSMContext):
    """Подтверждение создания нового плана с удалением старого"""
    # Получаем БД
    from handlers import assistant_onboarding
    _, profile_db = assistant_onboarding.get_db()
    
    if not profile_db:
        await callback.answer("⚠️ База данных временно недоступна", show_alert=True)
        return
    
    try:
        # Удаляем старый план
        success = await profile_db.delete_plan(callback.from_user.id)
        
        if success:
            await callback.message.edit_text(
                "<b>✅ Старый план удалён</b>\n\n"
                "Сейчас начнется создание нового плана...",
                parse_mode="HTML"
            )
            
            # Небольшая задержка для лучшего UX
            import asyncio
            await asyncio.sleep(1)
            
            # Очищаем состояние и запускаем онбординг заново
            await state.clear()
            from handlers import assistant_onboarding
            await assistant_onboarding.restart_onboarding_confirmed(callback, state)
        else:
            await callback.answer("Ошибка при удалении плана", show_alert=True)
            
    except Exception as e:
        logger.error(f"Ошибка при создании нового плана: {e}", exc_info=True)
        await callback.answer("Произошла ошибка", show_alert=True)


@router.message(AssistantStates.chat_mode)
async def process_chat_message(message: Message, state: FSMContext):
    """Обрабатывает сообщения в режиме чата"""
    user_id = message.from_user.id
    user_message = message.text
    
    # Проверяем команду выхода
    if user_message.lower() in ['выход', 'стоп', 'отмена', '/stop']:
        await state.clear()
        await message.answer(
            "Режим чата завершен.",
            reply_markup=get_main_menu_keyboard()
        )
        return
    
    # Показываем, что бот печатает
    typing_msg = await message.answer(ASSISTANT_MESSAGES['thinking'])
    
    try:
        # Если нет API ключа - даем стандартный ответ
        if not openai_assistant.has_api_key():
            await asyncio.sleep(1)
            response_text = (
                "В демо-режиме доступны только готовые сценарии.\n\n"
                "Для полноценного общения необходим API ключ OpenAI."
            )
        else:
            # Сохраняем сообщение пользователя
            await assistant_db.add_message(user_id, "user", user_message)
            
            # Получаем историю
            history = await assistant_db.get_chat_history(user_id)
            
            # Отправляем запрос к OpenAI
            response = await openai_assistant.send_message(
                message=user_message,
                context=history
            )
            
            if response['success']:
                # Используем 'response' вместо 'content' (или оба для совместимости)
                response_text = response.get('response') or response.get('content', '')
                
                # Сохраняем ответ ассистента
                await assistant_db.add_message(
                    user_id,
                    "assistant",
                    response_text
                )
            else:
                response_text = ASSISTANT_MESSAGES['error_api']
        
        # Удаляем сообщение "печатает..."
        await typing_msg.delete()
        
        # Отправляем ответ
        await message.answer(
            response_text,
            reply_markup=get_chat_mode_keyboard(),
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Ошибка в чате: {e}")
        await typing_msg.delete()
        await message.answer(
            ASSISTANT_MESSAGES['error_api'],
            reply_markup=get_chat_mode_keyboard(),
            parse_mode="HTML"
        )


# === ИСТОРИЯ ЧАТА ===

@router.callback_query(F.data == "chat_history")
async def show_chat_history(callback: CallbackQuery):
    """Показывает историю чата"""
    user_id = callback.from_user.id
    
    try:
        # Получаем историю
        history = await assistant_db.get_chat_history(user_id, limit=10)
        
        if not history:
            text = "<b>История чата</b>\n\n"
            text += "История пуста. Начните диалог с ассистентом."
        else:
            text = "<b>История чата</b>\n\n"
            text += "Последние сообщения:\n\n"
            
            for msg in history[-5:]:  # Показываем последние 5
                role = "Вы" if msg['role'] == 'user' else "Ассистент"
                content = msg['content'][:100] + "..." if len(msg['content']) > 100 else msg['content']
                text += f"<b>{role}:</b> {content}\n\n"
        
        await callback.message.edit_text(
            text,
            reply_markup=get_assistant_menu_keyboard(),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Ошибка при показе истории: {e}")
        await callback.answer(ERROR_MESSAGES['unknown_error'], show_alert=True)
    
    await callback.answer()


# === ОЧИСТКА ИСТОРИИ ===

@router.callback_query(F.data == "clear_history")
async def confirm_clear_history(callback: CallbackQuery):
    """Запрашивает подтверждение очистки истории"""
    await callback.message.edit_text(
        "<b>Очистка истории</b>\n\n"
        "Вы уверены, что хотите очистить всю историю диалогов?\n"
        "Это действие нельзя отменить.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="Да, очистить", callback_data="confirm_clear_history"),
                InlineKeyboardButton(text="Отмена", callback_data="assistant_menu")
            ]
        ]),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "confirm_clear_history")
async def clear_history(callback: CallbackQuery):
    """Очищает историю чата"""
    user_id = callback.from_user.id
    
    try:
        success = await assistant_db.clear_history(user_id)
        
        if success:
            await callback.answer("История очищена", show_alert=True)
            await callback.message.edit_text(
                ASSISTANT_MESSAGES['welcome'],
                reply_markup=get_assistant_menu_keyboard(),
                parse_mode="HTML"
            )
        else:
            await callback.answer("Не удалось очистить историю", show_alert=True)
    except Exception as e:
        logger.error(f"Ошибка при очистке истории: {e}")
        await callback.answer(ERROR_MESSAGES['unknown_error'], show_alert=True)


# === ВЫХОД ИЗ ЧАТА ===

@router.callback_query(F.data == "exit_chat", StateFilter(AssistantStates.chat_mode))
async def exit_chat_mode(callback: CallbackQuery, state: FSMContext):
    """Выход из режима чата"""
    await state.clear()
    
    await callback.message.edit_text(
        "Режим чата завершен.\n\n" + ASSISTANT_MESSAGES['welcome'],
        reply_markup=get_assistant_menu_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


# === ВОЗВРАТ В МЕНЮ ===

@router.callback_query(F.data == "exit_assistant")
async def exit_assistant(callback: CallbackQuery, state: FSMContext):
    """Выход из ассистента в главное меню"""
    await state.clear()  # Очищаем состояние
    
    await callback.message.delete()  # Удаляем сообщение с меню ассистента
    
    await callback.message.answer(
        "Выберите действие:",
        reply_markup=get_main_menu_keyboard()
    )
    
    await callback.answer("Вы вышли из ассистента")

@router.callback_query(F.data == "ai_assistant_start")
async def start_ai_planning(callback: CallbackQuery, state: FSMContext):
    """Начало создания персонального плана - переадресация на онбординг"""
    # Импортируем обработчик из assistant_onboarding
    from handlers import assistant_onboarding
    await assistant_onboarding.start_ai_onboarding(callback, state)


@router.callback_query(F.data == "quick_scenarios")
async def show_quick_scenarios(callback: CallbackQuery):
    """Показывает быстрые сценарии"""
    scenarios = [
        ("📅 План на день", "scenario_day_plan"),
        ("💪 Мотивация", "scenario_motivation"),
        ("🎯 Постановка цели", "scenario_goal_setting"),
        ("⏰ Управление временем", "scenario_time_management"),
        ("🧘 Антистресс", "scenario_stress_relief")
    ]
    
    builder = InlineKeyboardBuilder()
    for text, callback_data in scenarios:
        builder.row(InlineKeyboardButton(text=text, callback_data=callback_data))
    
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="assistant_menu"))
    
    await callback.message.edit_text(
        "⚡ <b>Быстрые сценарии</b>\n\n"
        "Выберите, что вам нужно прямо сейчас:",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()



# === ОБРАБОТЧИКИ СЦЕНАРИЕВ ===

@router.callback_query(F.data.startswith("scenario_"))
async def handle_scenario(callback: CallbackQuery):
    """Обработчик быстрых сценариев"""
    scenario_type = callback.data.replace("scenario_", "")
    
    scenarios_responses = {
        "day_plan": (
            "📅 <b>План на день</b>\n\n"
            "Для эффективного дня:\n"
            "1. Начните с самой важной задачи\n"
            "2. Делайте перерывы каждые 45-90 минут\n"
            "3. Запланируйте время для отдыха\n"
            "4. Завершите день подведением итогов\n\n"
            "Хотите, чтобы я помог составить детальный план?"
        ),
        "motivation": (
            "💪 <b>Мотивация</b>\n\n"
            "Помните: каждый маленький шаг приближает вас к цели!\n\n"
            "✨ Вы уже проделали большой путь\n"
            "🎯 Ваши усилия не напрасны\n"
            "🚀 Продолжайте двигаться вперед\n\n"
            "Что конкретно вас сейчас беспокоит?"
        ),
        "goal_setting": (
            "🎯 <b>Постановка цели</b>\n\n"
            "Эффективная цель должна быть:\n"
            "• Конкретной\n"
            "• Измеримой\n"
            "• Достижимой\n"
            "• Актуальной\n"
            "• Ограниченной по времени\n\n"
            "Расскажите о вашей цели, и я помогу её сформулировать!"
        ),
        "time_management": (
            "⏰ <b>Управление временем</b>\n\n"
            "Попробуйте эти техники:\n"
            "• Метод Помодоро (25 мин работы + 5 мин отдых)\n"
            "• Матрица Эйзенхауэра (важное/срочное)\n"
            "• Правило 2 минут (делайте сразу)\n"
            "• Блокировка времени в календаре\n\n"
            "Какая проблема со временем вас беспокоит?"
        ),
        "stress_relief": (
            "🧘 <b>Антистресс</b>\n\n"
            "Быстрые способы снять стресс:\n"
            "• Дыхание 4-7-8 (вдох-задержка-выдох)\n"
            "• 5-минутная прогулка\n"
            "• Запишите 3 вещи, за которые благодарны\n"
            "• Растяжка или легкая зарядка\n\n"
            "Что вызывает у вас стресс сейчас?"
        )
    }
    
    response = scenarios_responses.get(scenario_type, "Сценарий в разработке")
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="💬 Обсудить подробнее", callback_data="free_chat"))
    builder.row(InlineKeyboardButton(text="◀️ К сценариям", callback_data="quick_scenarios"))
    builder.row(InlineKeyboardButton(text="🏠 В меню", callback_data="assistant_menu"))
    
    await callback.message.edit_text(
        response,
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()


# Для корректного импорта
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton 
from aiogram.utils.keyboard import InlineKeyboardBuilder



