"""
Обработчики для модуля трекинга привычек
"""
from typing import Dict, List
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from datetime import datetime
import logging

from database.firestore_db import FirestoreDB
from database.tracker_db import TrackerDB
from database.gamification_db import GamificationDB
from keyboards.tracker import (
    get_tracker_menu_keyboard, get_habit_type_keyboard, get_habits_list_keyboard,
    get_habit_detail_keyboard, get_bad_habit_detail_keyboard, get_preset_habits_keyboard,
    get_frequency_keyboard, get_confirmation_keyboard, get_cancel_keyboard
)
from keyboards.main_menu import get_main_menu_keyboard
from states.tracker import HabitCreationStates, BadHabitStates
from utils.messages import ERROR_MESSAGES
from utils.achievements import POINTS_TABLE
from handlers.profile import show_new_achievements

# Создаем роутер
router = Router()
logger = logging.getLogger(__name__)

# Инициализируем базу данных
db = FirestoreDB()
tracker_db = TrackerDB(db.db)
gamification_db = GamificationDB(db.db)

# Пресеты привычек
PRESET_HABITS = {
    'water': {'name': 'Пить воду', 'description': 'Выпивать 8 стаканов воды в день', 'emoji': '▸'},
    'exercise': {'name': 'Утренняя зарядка', 'description': '15 минут упражнений каждое утро', 'emoji': '▸'},
    'reading': {'name': 'Чтение', 'description': 'Читать минимум 30 минут в день', 'emoji': '▸'},
    'meditation': {'name': 'Медитация', 'description': '10 минут медитации', 'emoji': '▸'},
    'early_rise': {'name': 'Ранний подъем', 'description': 'Вставать в 6:00 утра', 'emoji': '▸'},
    'healthy_food': {'name': 'Здоровое питание', 'description': 'Есть овощи и фрукты каждый день', 'emoji': '▸'},
    'walk': {'name': 'Прогулка', 'description': '10 000 шагов в день', 'emoji': '▸'},
    'journal': {'name': 'Дневник', 'description': 'Вести дневник перед сном', 'emoji': '▸'},
    'planning': {'name': 'Планирование дня', 'description': 'Планировать задачи на следующий день', 'emoji': '▸'},
    'sleep': {'name': 'Режим сна', 'description': 'Ложиться спать до 23:00', 'emoji': '▸'}
}

async def get_user_habits(self, user_id: int) -> List[Dict]:
    """Получает список активных привычек пользователя"""
    try:
        habits_ref = self.db.collection('users').document(str(user_id)) \
                           .collection('habits')
        
        # bugfix: правильный метод для асинхронного firestore
        query = habits_ref.where('is_active', '==', True)
        habits_docs = await query.get()
        
        habits = []
        today = datetime.utcnow().date()
        
        for doc in habits_docs:
            habit_data = doc.to_dict()
            habit_data['id'] = doc.id
            habit_data['habit_id'] = doc.id
            
            # Проверяем, выполнена ли привычка сегодня
            last_completed = habit_data.get('last_completed')
            if last_completed:
                is_completed_today = last_completed.date() == today
            else:
                is_completed_today = False
            
            habit_data['is_completed_today'] = is_completed_today
            habits.append(habit_data)
        
        return habits
        
    except Exception as e:
        logger.error(f"Error getting habits: {e}")
        return []

async def get_user_bad_habits(self, user_id: int) -> List[Dict]:
    """Получает список вредных привычек пользователя"""
    try:
        habits_ref = self.db.collection('users').document(str(user_id)) \
                           .collection('bad_habits')
        
        # bugfix: правильный метод для асинхронного firestore
        query = habits_ref.where('is_active', '==', True)
        habits_docs = await query.get()
        
        habits = []
        
        for doc in habits_docs:
            habit_data = doc.to_dict()
            habit_data['id'] = doc.id
            habit_data['habit_id'] = doc.id
            
            # Рассчитываем дни воздержания
            if habit_data.get('last_reset'):
                last_reset = habit_data['last_reset']
                days_without = (datetime.utcnow() - last_reset).days
            else:
                created_at = habit_data.get('created_at', datetime.utcnow())
                days_without = (datetime.utcnow() - created_at).days
            
            habit_data['days_without'] = days_without
            habits.append(habit_data)
        
        logger.info(f"Found {len(habits)} bad habits for user {user_id}")
        return habits
        
    except Exception as e:
        logger.error(f"Error getting bad habits for user {user_id}: {e}")
        return []

async def get_user_stats(self, user_id: int) -> Dict:
    """Получает общую статистику пользователя"""
    try:
        stats = {
            'active_habits': 0,
            'total_completed': 0,
            'total_streak_days': 0,
            'best_streaks': {},
            'bad_habits_stats': {}
        }
        
        # bugfix: используем существующие методы
        # Статистика полезных привычек
        habits = await self.get_user_habits(user_id)
        stats['active_habits'] = len(habits)
        
        for habit in habits:
            stats['total_completed'] += habit.get('total_completed', 0)
            stats['total_streak_days'] += habit.get('current_streak', 0)
            
            if habit.get('best_streak', 0) > 0:
                stats['best_streaks'][habit.get('name', 'Привычка')] = habit.get('best_streak', 0)
        
        # Статистика вредных привычек
        bad_habits = await self.get_user_bad_habits(user_id)
        for habit in bad_habits:
            stats['bad_habits_stats'][habit.get('name', 'Привычка')] = habit.get('days_without', 0)
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting user stats: {e}")
        return {
            'active_habits': 0,
            'total_completed': 0,
            'total_streak_days': 0,
            'best_streaks': {},
            'bad_habits_stats': {}
        }
    
# === ГЛАВНОЕ МЕНЮ ТРЕКЕРОВ ===

@router.message(F.text == "📊 Трекеры", StateFilter(default_state))
async def handle_tracker_menu(message: Message):
    """Обработчик кнопки Трекеры из главного меню"""
    await message.answer(
        "<b>📊 Трекер привычек</b>\n\n"
        "Отслеживайте прогресс по полезным привычкам и контролируйте воздержание от вредных.\n\n"
        "Выберите действие:",
        reply_markup=get_tracker_menu_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "tracker_menu")
async def show_tracker_menu(callback: CallbackQuery):
    """Показывает главное меню трекера"""
    await callback.message.edit_text(
        "<b>📊 Трекер привычек</b>\n\n"
        "Отслеживайте прогресс по полезным привычкам и контролируйте воздержание от вредных.\n\n"
        "Выберите действие:",
        reply_markup=get_tracker_menu_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


# === СОЗДАНИЕ ПРИВЫЧКИ ===

@router.callback_query(F.data == "add_habit")
async def start_habit_creation(callback: CallbackQuery, state: FSMContext):
    """Начинает процесс создания привычки"""
    await callback.message.edit_text(
        "<b>Создание новой привычки</b>\n\n"
        "Какую привычку вы хотите добавить?",
        reply_markup=get_habit_type_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(HabitCreationStates.choosing_habit_type)
    await callback.answer()


@router.callback_query(F.data.startswith("habit_type:"), HabitCreationStates.choosing_habit_type)
async def process_habit_type(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает выбор типа привычки"""
    habit_type = callback.data.split(":")[1]
    
    if habit_type == "preset":
        await callback.message.edit_text(
            "<b>Выберите привычку из списка:</b>",
            reply_markup=get_preset_habits_keyboard(),
            parse_mode="HTML"
        )
    elif habit_type == "good":
        await state.update_data(habit_type="good")
        await callback.message.answer(
            "<b>Название привычки</b>\n\n"
            "Напишите название для вашей привычки.\n"
            "Например: <i>Утренняя зарядка</i>",
            reply_markup=get_cancel_keyboard(),
            parse_mode="HTML"
        )
        await callback.message.delete()
        await state.set_state(HabitCreationStates.waiting_for_name)
    elif habit_type == "bad":
        await state.update_data(habit_type="bad")
        await callback.message.answer(
            "<b>Вредная привычка</b>\n\n"
            "От какой привычки вы хотите избавиться?\n"
            "Например: <i>Курение</i>",
            reply_markup=get_cancel_keyboard(),
            parse_mode="HTML"
        )
        await callback.message.delete()
        await state.set_state(HabitCreationStates.waiting_for_name)
    
    await callback.answer()


@router.callback_query(F.data.startswith("preset:"), HabitCreationStates.choosing_habit_type)
async def process_preset_selection(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает выбор пресета"""
    preset_key = callback.data.split(":")[1]
    preset = PRESET_HABITS.get(preset_key)
    
    if preset:
        await state.update_data(
            habit_type="good",
            name=preset['name'],
            description=preset['description'],
            emoji=preset['emoji']
        )
        
        await callback.message.answer(
            f"<b>Частота выполнения</b>\n\n"
            f"Привычка: {preset['emoji']} {preset['name']}\n\n"
            f"Как часто вы планируете выполнять эту привычку?",
            reply_markup=get_frequency_keyboard(),
            parse_mode="HTML"
        )
        await callback.message.delete()
        await state.set_state(HabitCreationStates.waiting_for_frequency)
    
    await callback.answer()


@router.message(HabitCreationStates.waiting_for_name)
async def process_habit_name(message: Message, state: FSMContext):
    """Обрабатывает название привычки"""
    if message.text == "Отмена":
        await cancel_creation(message, state)
        return
    
    await state.update_data(name=message.text)
    
    await message.answer(
        "<b>Описание привычки</b>\n\n"
        "Добавьте описание или детали.\n"
        "Например: <i>15 минут упражнений каждое утро</i>\n\n"
        "Или отправьте точку (.) чтобы пропустить.",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(HabitCreationStates.waiting_for_description)


@router.message(HabitCreationStates.waiting_for_description)
async def process_habit_description(message: Message, state: FSMContext):
    """Обрабатывает описание привычки"""
    if message.text == "Отмена":
        await cancel_creation(message, state)
        return
    
    description = message.text if message.text != "." else ""
    await state.update_data(description=description)
    
    # Получаем тип привычки
    data = await state.get_data()
    habit_type = data.get('habit_type', 'good')
    
    if habit_type == 'bad':
        # Для вредной привычки сразу создаем
        await complete_bad_habit_creation(message, state)
    else:
        # Для полезной привычки спрашиваем частоту
        await message.answer(
            "<b>Частота выполнения</b>\n\n"
            "Как часто вы планируете выполнять эту привычку?",
            reply_markup=get_frequency_keyboard(),
            parse_mode="HTML"
        )
        await state.set_state(HabitCreationStates.waiting_for_frequency)


@router.message(HabitCreationStates.waiting_for_frequency)
async def process_habit_frequency(message: Message, state: FSMContext):
    """Обрабатывает частоту привычки"""
    await state.update_data(frequency=message.text)
    
    await message.answer(
        "<b>Выберите символ</b>\n\n"
        "Отправьте эмодзи для этой привычки.\n"
        "Например: ▸ • ◆ ★\n\n"
        "Или отправьте точку (.) для стандартного символа ▸",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(HabitCreationStates.waiting_for_emoji)


@router.message(HabitCreationStates.waiting_for_emoji)
async def process_habit_emoji(message: Message, state: FSMContext):
    """Завершает создание привычки"""
    if message.text == "Отмена":
        await cancel_creation(message, state)
        return
    
    emoji = message.text if message.text != "." else "▸"
    await state.update_data(emoji=emoji)
    
    # Получаем все данные
    data = await state.get_data()
    user_id = message.from_user.id
    
    try:
        # Создаем привычку
        habit_data = {
            'name': data.get('name'),
            'description': data.get('description', ''),
            'frequency': data.get('frequency', 'Ежедневно'),
            'emoji': emoji,
            'is_bad': False
        }
        
        habit_id = await tracker_db.create_habit(user_id, habit_data)
        
        if habit_id:
            await message.answer(
                f"<b>✓ Привычка создана</b>\n\n"
                f"{emoji} {data.get('name')}\n"
                f"Частота: {data.get('frequency', 'Ежедневно')}\n\n"
                f"Привычка добавлена в ваш трекер.",
                reply_markup=get_main_menu_keyboard(),
                parse_mode="HTML"
            )
            
            # Проверяем достижение "Первая привычка"
            new_achievements = await gamification_db.check_and_unlock_achievements(user_id)
            if new_achievements:
                await show_new_achievements(message, new_achievements)
        else:
            await message.answer(ERROR_MESSAGES['database_error'])
        
        await state.clear()
    except Exception as e:
        logger.error(f"Ошибка при создании привычки: {e}")
        await message.answer(ERROR_MESSAGES['unknown_error'])
        await state.clear()


async def complete_bad_habit_creation(message: Message, state: FSMContext):
    """Завершает создание вредной привычки"""
    data = await state.get_data()
    user_id = message.from_user.id
    
    try:
        habit_data = {
            'name': data.get('name'),
            'description': data.get('description', ''),
            'emoji': '▸',
            'is_bad': True  # bugfix: добавлено поле is_bad
        }
        
        habit_id = await tracker_db.create_bad_habit(user_id, habit_data)
        
        if habit_id:
            await message.answer(
                f"<b>✓ Привычка добавлена</b>\n\n"
                f"▸ {data.get('name')}\n\n"
                f"Теперь вы можете отслеживать дни воздержания.",
                reply_markup=get_main_menu_keyboard(),
                parse_mode="HTML"
            )
            # bugfix: добавлен лог успешного создания
            logger.info(f"Created bad habit {habit_id} for user {user_id}")
        else:
            await message.answer(ERROR_MESSAGES['database_error'])
        
        await state.clear()
    except Exception as e:
        logger.error(f"Ошибка при создании вредной привычки: {e}")
        await message.answer(ERROR_MESSAGES['unknown_error'])
        await state.clear()


# === ПРОСМОТР ПРИВЫЧЕК ===

@router.callback_query(F.data == "my_habits")
async def show_my_habits(callback: CallbackQuery):
    """Показывает список полезных привычек"""
    user_id = callback.from_user.id
    
    try:
        habits = await tracker_db.get_user_habits(user_id)
        
        if not habits:
            text = "<b>Мои привычки</b>\n\n"
            text += "У вас пока нет активных привычек.\n\n"
            text += "Создайте первую привычку, чтобы начать отслеживать прогресс."
        else:
            text = "<b>Мои привычки</b>\n\n"
            for habit in habits:
                emoji = habit.get('emoji', '▸')
                name = habit.get('name', 'Без названия')
                streak = habit.get('current_streak', 0)
                is_completed_today = habit.get('is_completed_today', False)
                
                status = "✓" if is_completed_today else "○"
                text += f"{status} {emoji} <b>{name}</b>\n"
                text += f"   Серия: {streak} дней\n\n"
        
        await callback.message.edit_text(
            text,
            reply_markup=get_habits_list_keyboard(habits, "good"),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Ошибка при показе привычек: {e}")
        await callback.answer(ERROR_MESSAGES['unknown_error'], show_alert=True)
    
    await callback.answer()


@router.callback_query(F.data.startswith("habit_detail:"))
async def view_habit_details(callback: CallbackQuery):
    """Показывает детали привычки"""
    user_id = callback.from_user.id
    habit_id = callback.data.split(":")[1]
    
    try:
        habit = await tracker_db.get_habit(user_id, habit_id)
        if not habit:
            await callback.answer("Привычка не найдена", show_alert=True)
            return
        
        emoji = habit.get('emoji', '▸')
        name = habit.get('name', 'Без названия')
        description = habit.get('description', '')
        frequency = habit.get('frequency', 'Ежедневно')
        streak = habit.get('current_streak', 0)
        best_streak = habit.get('best_streak', 0)
        total_completed = habit.get('total_completed', 0)
        is_completed_today = habit.get('is_completed_today', False)
        
        text = f"{emoji} <b>{name}</b>\n\n"
        if description:
            text += f"<i>{description}</i>\n\n"
        
        text += f"Частота: {frequency}\n"
        text += f"Текущая серия: {streak} дней\n"
        text += f"Лучший результат: {best_streak} дней\n"
        text += f"Всего выполнено: {total_completed} раз\n"
        
        if is_completed_today:
            text += "\n✓ Выполнено сегодня"
        
        # bugfix: используем готовую функцию клавиатуры вместо создания builder
        await callback.message.edit_text(
            text,
            reply_markup=get_habit_detail_keyboard(habit_id, is_completed_today),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Ошибка при показе деталей привычки: {e}")
        await callback.answer(ERROR_MESSAGES['unknown_error'], show_alert=True)
    
    await callback.answer()

# === ОТМЕТКА ВЫПОЛНЕНИЯ ===

@router.callback_query(F.data.startswith("complete_habit:"))
async def complete_habit(callback: CallbackQuery):
    """Отмечает привычку как выполненную"""
    user_id = callback.from_user.id
    habit_id = callback.data.split(":")[1]

    logger.info(f"Completing habit {habit_id} for user {user_id}")
    
    try:
        # Отмечаем выполнение в БД
        success, new_streak, best_streak = await tracker_db.complete_habit(user_id, habit_id)
        
        if success:
            # Получаем информацию о привычке
            habit = await tracker_db.get_habit(user_id, habit_id)
            habit_name = habit.get('name', 'Привычка')
            
            # Начисляем очки
            await gamification_db.add_points(
                user_id, 
                POINTS_TABLE['habit_completed'],
                'habit_completed',
                {'habit_id': habit_id, 'habit_name': habit_name}
            )
            
            # Бонус за новый день streak
            if new_streak > 1:
                await gamification_db.add_points(
                    user_id,
                    POINTS_TABLE['habit_streak_bonus'],
                    'habit_streak_bonus',
                    {'habit_id': habit_id, 'streak': new_streak}
                )
            
            # Обновляем сообщение
            await callback.message.edit_text(
                f"<b>✓ Привычка выполнена</b>\n\n"
                f"Привычка: {habit_name}\n"
                f"Текущая серия: {new_streak} {'день' if new_streak == 1 else 'дней'}\n"
                f"Лучший результат: {best_streak} дней\n\n"
                f"Продолжайте поддерживать регулярность.",
                reply_markup=get_habit_detail_keyboard(habit_id, True),
                parse_mode="HTML"
            )
            
            # Проверяем достижения
            new_achievements = await gamification_db.check_and_unlock_achievements(user_id)
            if new_achievements:
                await show_new_achievements(callback.message, new_achievements)
            
            await callback.answer("Отмечено")
        else:
            await callback.answer("Уже выполнено сегодня", show_alert=True)
            
    except Exception as e:
        logger.error(f"Ошибка при выполнении привычки: {e}")
        await callback.answer(ERROR_MESSAGES['unknown_error'], show_alert=True)


# === ВРЕДНЫЕ ПРИВЫЧКИ ===

@router.callback_query(F.data == "bad_habits")
async def show_bad_habits_list(callback: CallbackQuery):
    """Показывает список вредных привычек"""
    user_id = callback.from_user.id
    
    try:
        habits = await tracker_db.get_user_bad_habits(user_id)
        
        if not habits:
            text = "<b>Воздержание от вредных привычек</b>\n\n"
            text += "У вас пока нет вредных привычек для отслеживания.\n\n"
            text += "Добавьте привычку, от которой хотите избавиться."
        else:
            text = "<b>Воздержание от вредных привычек</b>\n\n"
            for habit in habits:
                emoji = habit.get('emoji', '▸')
                name = habit.get('name', 'Без названия')
                days = habit.get('days_without', 0)
                best = habit.get('best_streak', 0)
                
                text += f"{emoji} <b>{name}</b>\n"
                text += f"Без срывов: {days} дней\n"
                text += f"Рекорд: {best} дней\n\n"
        
        await callback.message.edit_text(
            text,
            reply_markup=get_habits_list_keyboard(habits, "bad"),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Ошибка при показе вредных привычек: {e}")
        await callback.answer(ERROR_MESSAGES['unknown_error'], show_alert=True)
    
    await callback.answer()


@router.callback_query(F.data.startswith("bad_habit_detail:"))
async def view_bad_habit_details(callback: CallbackQuery):
    """Показывает детали вредной привычки"""
    user_id = callback.from_user.id
    habit_id = callback.data.split(":")[1]
    
    try:
        habit = await tracker_db.get_bad_habit(user_id, habit_id)
        if not habit:
            await callback.answer("Привычка не найдена", show_alert=True)
            return
        
        emoji = habit.get('emoji', '▸')
        name = habit.get('name', 'Без названия')
        description = habit.get('description', '')
        days = habit.get('days_without', 0)
        best = habit.get('best_streak', 0)
        resets = habit.get('total_resets', 0)
        
        text = f"{emoji} <b>{name}</b>\n\n"
        if description:
            text += f"<i>{description}</i>\n\n"
        
        text += f"<b>Дней без срывов: {days}</b>\n"
        text += f"Лучший результат: {best} дней\n"
        text += f"Количество срывов: {resets}\n"
        
        # Сдержанные мотивационные сообщения
        if days > 0:
            if days < 7:
                text += "\nХорошее начало. Продолжайте."
            elif days < 30:
                text += "\nОтличный прогресс. Держитесь."
            elif days < 90:
                text += "\nВпечатляющий результат."
            else:
                text += "\nВыдающееся достижение."
        
        await callback.message.edit_text(
            text,
            reply_markup=get_bad_habit_detail_keyboard(habit_id),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Ошибка при показе деталей: {e}")
        await callback.answer(ERROR_MESSAGES['unknown_error'], show_alert=True)
    
    await callback.answer()


@router.callback_query(F.data.startswith("reset_bad_habit:"))
async def confirm_reset_bad_habit(callback: CallbackQuery):
    """Запрашивает подтверждение сброса счетчика"""
    habit_id = callback.data.split(":")[1]
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="Да, сбросить", 
            callback_data=f"confirm_reset:{habit_id}"
        ),
        InlineKeyboardButton(
            text="Отмена", 
            callback_data=f"bad_habit_detail:{habit_id}"
        )
    )
    
    await callback.message.edit_text(
        "<b>Подтверждение сброса</b>\n\n"
        "Вы уверены, что хотите сбросить счетчик?\n"
        "Текущий прогресс будет потерян.",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_reset:"))
async def reset_bad_habit(callback: CallbackQuery):
    """Сбрасывает счетчик вредной привычки"""
    user_id = callback.from_user.id
    habit_id = callback.data.split(":")[1]
    
    try:
        success = await tracker_db.reset_bad_habit(user_id, habit_id)
        
        if success:
            await callback.message.edit_text(
                "<b>Счетчик воздержания сброшен</b>\n\n"
                "Не расстраивайтесь. Каждая попытка делает вас сильнее. Начните заново.",
                reply_markup=get_tracker_menu_keyboard(),
                parse_mode="HTML"
            )
            await callback.answer("Счетчик сброшен")
        else:
            await callback.answer("Не удалось сбросить счетчик", show_alert=True)
    except Exception as e:
        logger.error(f"Ошибка при сбросе счетчика: {e}")
        await callback.answer(ERROR_MESSAGES['unknown_error'], show_alert=True)


# === ИСТОРИЯ ПРИВЫЧКИ ===

@router.callback_query(F.data.startswith("habit_history:"))
async def show_habit_history(callback: CallbackQuery):
    """Показывает историю выполнения привычки"""
    user_id = callback.from_user.id
    habit_id = callback.data.split(":")[1]
    
    try:
        habit = await tracker_db.get_habit(user_id, habit_id)
        if not habit:
            await callback.answer("Привычка не найдена", show_alert=True)
            return
        
        history = await tracker_db.get_habit_history(user_id, habit_id, limit=10)
        
        text = f"<b>История: {habit.get('name', 'Привычка')}</b>\n\n"
        
        if not history:
            text += "История пока пуста."
        else:
            text += "Последние отметки:\n\n"
            for record in history:
                date = record.get('completed_at', datetime.utcnow())
                text += f"• {date.strftime('%d.%m.%Y')}\n"
        
        # bugfix: создаем builder ПЕРЕД использованием
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        from aiogram.types import InlineKeyboardButton
        
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text="◀ Назад", 
                callback_data=f"habit_detail:{habit_id}"
            )
        )
        
        await callback.message.edit_text(
            text,
            reply_markup=builder.as_markup(),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Ошибка при показе истории: {e}")
        await callback.answer(ERROR_MESSAGES['unknown_error'], show_alert=True)
    
    await callback.answer()


# === УДАЛЕНИЕ ПРИВЫЧКИ ===

@router.callback_query(F.data.startswith("delete_habit:") | F.data.startswith("delete_bad_habit:"))
async def confirm_delete_habit(callback: CallbackQuery):
    """Запрашивает подтверждение удаления"""
    parts = callback.data.split(":")
    habit_type = "bad" if "bad" in parts[0] else "good"
    habit_id = parts[1]
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="Да, удалить", 
            callback_data=f"confirm_delete:{habit_type}:{habit_id}"
        ),
        InlineKeyboardButton(
            text="Отмена", 
            callback_data=f"{'bad_' if habit_type == 'bad' else ''}habit_detail:{habit_id}"
        )
    )
    
    await callback.message.edit_text(
        "<b>Подтверждение удаления</b>\n\n"
        "Вы уверены, что хотите удалить эту привычку?\n"
        "Вся история будет потеряна.",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_delete:"))
async def delete_habit(callback: CallbackQuery):
    """Удаляет привычку"""
    user_id = callback.from_user.id
    parts = callback.data.split(":")
    habit_type = parts[1]
    habit_id = parts[2]
    
    try:
        if habit_type == "bad":
            success = await tracker_db.delete_bad_habit(user_id, habit_id)
        else:
            success = await tracker_db.delete_habit(user_id, habit_id)
        
        if success:
            await callback.message.edit_text(
                "Привычка удалена.",
                reply_markup=get_tracker_menu_keyboard(),
                parse_mode="HTML"
            )
            await callback.answer("Удалено")
        else:
            await callback.answer("Не удалось удалить привычку", show_alert=True)
    except Exception as e:
        logger.error(f"Ошибка при удалении привычки: {e}")
        await callback.answer(ERROR_MESSAGES['unknown_error'], show_alert=True)


# === СТАТИСТИКА ===

@router.callback_query(F.data == "tracker_stats")
async def show_tracker_stats(callback: CallbackQuery):
    """Показывает статистику трекера"""
    user_id = callback.from_user.id
    
    try:
        stats = await tracker_db.get_user_stats(user_id)
        
        # Добавьте проверки на None
        if not stats:
            stats = {
                'active_habits': 0,
                'total_completed': 0,
                'total_streak_days': 0,
                'best_streaks': {},
                'bad_habits_stats': {}
            }
        
        text = f"<b>📊 Статистика трекера</b>\n\n"
        text += f"<b>Общий прогресс:</b>\n"
        text += f"• Активных привычек: {stats.get('active_habits', 0)}\n"
        text += f"• Всего выполнено: {stats.get('total_completed', 0)}\n"
        text += f"• Общая продолжительность: {stats.get('total_streak_days', 0)} дней\n\n"
        
        # Лучшие результаты с проверкой
        best_streaks = stats.get('best_streaks', {})
        if best_streaks:
            text += "<b>Лучшие результаты:</b>\n"
            for habit_name, streak in best_streaks.items():
                text += f"• {habit_name}: {streak} дней\n"
            text += "\n"
        
        # Воздержание с проверкой
        bad_habits_stats = stats.get('bad_habits_stats', {})
        if bad_habits_stats:
            text += "<b>Воздержание от вредных привычек:</b>\n"
            for habit_name, days in bad_habits_stats.items():
                text += f"• {habit_name}: {days} дней без срывов\n"
        
        await callback.message.edit_text(
            text,
            reply_markup=get_tracker_menu_keyboard(),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Ошибка при показе статистики: {e}")
        await callback.answer("Ошибка при загрузке статистики", show_alert=True)
    
    await callback.answer()


# === ПОМОЩЬ ===

@router.callback_query(F.data == "tracker_help")
async def show_tracker_help(callback: CallbackQuery):
    """Показывает справку по трекеру"""
    text = """<b>Как работает трекер привычек</b>

<b>Полезные привычки:</b>
• Отмечайте выполнение каждый день
• Следите за серией дней (streak)
• Получайте очки за регулярность

<b>Вредные привычки:</b>
• Отслеживайте дни воздержания
• При срыве счетчик обнуляется
• Лучший результат сохраняется

<b>Рекомендации:</b>
• Начните с 1-3 привычек
• Фокусируйтесь на регулярности
• Отмечайте выполнение сразу"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_tracker_menu_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


# === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===

async def cancel_creation(message: Message, state: FSMContext):
    """Отменяет создание привычки"""
    await state.clear()
    await message.answer(
        "Создание привычки отменено.",
        reply_markup=get_main_menu_keyboard()
    )


@router.callback_query(F.data == "cancel_habit_creation")
async def cancel_creation_callback(callback: CallbackQuery, state: FSMContext):
    """Отменяет создание привычки (callback версия)"""
    await state.clear()
    await callback.message.edit_text(
        "Создание привычки отменено.",
        reply_markup=get_tracker_menu_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "back_to_main")
async def back_to_main_menu(callback: CallbackQuery):
    """Возврат в главное меню"""
    await callback.message.answer(
        "Главное меню",
        reply_markup=get_main_menu_keyboard()
    )
    await callback.message.delete()
    await callback.answer()


# Для корректного импорта
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder