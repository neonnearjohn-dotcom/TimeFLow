"""
Обработчик команды /start и процесса начального опроса
"""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
import logging
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from database.firestore_db import FirestoreDB
from keyboards.main_menu import get_main_menu_keyboard, get_skip_keyboard
from states.onboarding import OnboardingStates
from utils.messages import (
    WELCOME_NEW_USER,
    WELCOME_EXISTING_USER,
    ONBOARDING_QUESTIONS,
    ONBOARDING_COMPLETE,
    ERROR_MESSAGES,
)


# Создаем роутер для обработчиков
router = Router()
logger = logging.getLogger(__name__)

# Инициализируем подключение к базе данных
db = FirestoreDB()


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Обработчик команды /help"""
    help_text = """
<b>📋 Доступные команды:</b>

/start - Перезапустить бота
/help - Показать эту справку
/menu - Открыть главное меню
/onboarding - Настроить персональный план с ИИ

<b>🔹 Основные функции:</b>

📊 <b>Трекеры</b> - отслеживание привычек
- Создавайте полезные привычки
- Отслеживайте вредные привычки
- Следите за прогрессом

⏱ <b>Фокус</b> - техника Помодоро
- Фокус-сессии для продуктивности
- Настраиваемые таймеры
- Фоновые звуки для концентрации

✅ <b>Чек-лист</b> - управление задачами
- Матрица Эйзенхауэра
- Приоритизация задач
- Отслеживание выполнения

💬 <b>Ассистент</b> - ИИ-помощник
- Персональные планы достижения целей
- Быстрые сценарии для типовых задач
- Свободное общение с ИИ

👤 <b>Профиль</b> - ваша статистика
- Достижения и награды
- История активности
- Общий прогресс

<b>💡 Совет:</b> 
Начните с создания персонального плана через /onboarding - ИИ поможет определить цели и создаст пошаговый план их достижения!

<b>🆘 Поддержка:</b>
Если у вас есть вопросы или предложения, напишите @your_support_username
"""

    # Создаем inline клавиатуру с полезными кнопками
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎯 Создать план", callback_data="ai_assistant_start")],
            [
                InlineKeyboardButton(text="📊 Мои трекеры", callback_data="trackers"),
                InlineKeyboardButton(text="⏱ Фокус-сессия", callback_data="focus"),
            ],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")],
        ]
    )

    await message.answer(help_text, reply_markup=keyboard, parse_mode="HTML")


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """
    Обработчик команды /start

    Проверяет, есть ли пользователь в базе:
    - Если нет - запускает процесс начального опроса
    - Если есть - показывает главное меню
    """
    user_id = message.from_user.id
    user_name = message.from_user.full_name

    try:
        # Проверяем, существует ли пользователь в базе
        user_exists = await db.user_exists(user_id)

        if user_exists:
            # Пользователь уже есть - показываем главное меню
            await message.answer(
                WELCOME_EXISTING_USER, reply_markup=get_main_menu_keyboard(), parse_mode="Markdown"
            )
        else:
            # Новый пользователь - создаем запись и начинаем опрос
            user_data = {
                "username": message.from_user.username,
                "full_name": user_name,
                "onboarding_completed": False,
                "points_balance": 0,
                "total_points_earned": 0,
                "achievements_count": 0,
            }

            # Создаем пользователя в базе
            success = await db.create_user(user_id, user_data)

            if success:
                # Отправляем приветствие и первый вопрос
                await message.answer(WELCOME_NEW_USER)
                await message.answer(
                    ONBOARDING_QUESTIONS["goal"],
                    reply_markup=get_skip_keyboard(),
                    parse_mode="Markdown",
                )
                # Устанавливаем состояние ожидания ответа на первый вопрос
                await state.set_state(OnboardingStates.waiting_for_goal)
            else:
                await message.answer(ERROR_MESSAGES["database_error"])

    except Exception as e:
        logger.error(f"Ошибка в обработчике /start для пользователя {user_id}: {e}")
        await message.answer(ERROR_MESSAGES["unknown_error"])


@router.message(OnboardingStates.waiting_for_goal)
async def process_goal_answer(message: Message, state: FSMContext):
    """
    Обработчик ответа на вопрос о главной цели
    """
    user_id = message.from_user.id

    # Сохраняем ответ в состояние FSM
    if message.text != "⏭ Пропустить":
        await state.update_data(goal=message.text)
    else:
        await state.update_data(goal="Не указано")

    # Отправляем следующий вопрос
    await message.answer(
        ONBOARDING_QUESTIONS["habits"], reply_markup=get_skip_keyboard(), parse_mode="Markdown"
    )

    # Переходим к следующему состоянию
    await state.set_state(OnboardingStates.waiting_for_habits)


@router.message(OnboardingStates.waiting_for_habits)
async def process_habits_answer(message: Message, state: FSMContext):
    """
    Обработчик ответа на вопрос о привычках
    """
    user_id = message.from_user.id

    # Сохраняем ответ
    if message.text != "⏭ Пропустить":
        await state.update_data(habits=message.text)
    else:
        await state.update_data(habits="Не указано")

    # Отправляем последний вопрос
    await message.answer(
        ONBOARDING_QUESTIONS["time_problems"],
        reply_markup=get_skip_keyboard(),
        parse_mode="Markdown",
    )

    # Переходим к последнему состоянию
    await state.set_state(OnboardingStates.waiting_for_time_problems)


@router.message(OnboardingStates.waiting_for_time_problems)
async def process_time_problems_answer(message: Message, state: FSMContext):
    """
    Обработчик ответа на вопрос о проблемах с тайм-менеджментом
    """
    user_id = message.from_user.id

    # Сохраняем последний ответ
    if message.text != "⏭ Пропустить":
        await state.update_data(time_problems=message.text)
    else:
        await state.update_data(time_problems="Не указано")

    try:
        # Получаем все ответы из состояния
        user_data = await state.get_data()

        # Формируем словарь с ответами
        answers = {
            "goal": user_data.get("goal", "Не указано"),
            "habits": user_data.get("habits", "Не указано"),
            "time_problems": user_data.get("time_problems", "Не указано"),
        }

        # Сохраняем ответы в базу данных
        success = await db.save_onboarding_answers(user_id, answers)

        if success:
            # Завершаем опрос и показываем главное меню
            await message.answer(
                ONBOARDING_COMPLETE, reply_markup=get_main_menu_keyboard(), parse_mode="Markdown"
            )
        else:
            await message.answer(ERROR_MESSAGES["database_error"])

        # Очищаем состояние FSM
        await state.clear()

    except Exception as e:
        logger.error(f"Ошибка при сохранении ответов опроса для пользователя {user_id}: {e}")
        await message.answer(ERROR_MESSAGES["unknown_error"])
        await state.clear()
