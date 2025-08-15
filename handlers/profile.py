"""
Обработчики для профиля и геймификации
"""
from typing import List
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import StateFilter
from aiogram.fsm.state import default_state
from datetime import datetime, timezone
import logging

from database.firestore_db import FirestoreDB
from database.gamification_db import GamificationDB
from keyboards.profile import (
    get_profile_menu_keyboard, get_achievements_keyboard, get_stats_keyboard,
    get_achievement_categories_keyboard, get_back_to_profile_keyboard
)
from keyboards.main_menu import get_main_menu_keyboard
from utils.achievements import ACHIEVEMENTS, get_achievement_message, get_rarity_color
from utils.messages import ERROR_MESSAGES

# Создаем роутер
router = Router()
logger = logging.getLogger(__name__)

# Инициализируем базу данных
db = FirestoreDB()
gamification_db = GamificationDB(db.db)


# === ГЛАВНОЕ МЕНЮ ПРОФИЛЯ ===

@router.message(F.text == "👤 Профиль", StateFilter(default_state))
async def handle_profile_menu(message: Message):
    """Обработчик кнопки Профиль из главного меню"""
    await show_user_profile(message.from_user.id, message.answer)


@router.callback_query(F.data == "view_profile")
async def handle_profile_callback(callback: CallbackQuery):
    """Показ профиля по callback"""
    await show_user_profile(callback.from_user.id, callback.message.edit_text)
    await callback.answer()


@router.callback_query(F.data == "refresh_profile")
async def refresh_profile(callback: CallbackQuery):
    """Обновление профиля"""
    await show_user_profile(callback.from_user.id, callback.message.edit_text)
    await callback.answer("✅ Профиль обновлен!")


async def show_user_profile(user_id: int, answer_method):
    """
    Показывает профиль пользователя
    """
    try:
        logger.info(f"Запрос профиля для пользователя {user_id}")
        
        # Проверяем, существует ли пользователь
        user_exists = await db.user_exists(user_id)
        if not user_exists:
            logger.warning(f"Пользователь {user_id} не найден в БД")
            await answer_method(
                "😔 Профиль не найден.\n\n"
                "Выполни любое действие (привычку, фокус-сессию или задачу), чтобы начать!",
                reply_markup=get_main_menu_keyboard()
            )
            return
        
        profile = await gamification_db.get_user_profile(user_id)
        
        if not profile:
            logger.warning(f"Профиль пользователя {user_id} пустой")
            await answer_method(
                "😔 Профиль пока пустой.\n\n"
                "Начни использовать бота, и здесь появится твоя статистика!",
                reply_markup=get_main_menu_keyboard()
            )
            return
        
        # Формируем текст профиля
        text = f"👤 <b>Твой профиль</b>\n\n"
        
        # Основная информация
        text += f"👋 {profile.get('full_name', 'Пользователь')}\n"
        if profile.get('username'):
            text += f"🔗 @{profile['username']}\n"
        
        created_at = profile.get('created_at')
        if created_at:
            from datetime import datetime, timezone 
            days_with_us = (datetime.now(timezone.utc) - created_at).days
            text += f"📅 С нами: {days_with_us} дней\n"
        
        text += "\n"
        
        # Очки
        balance = profile.get('points_balance', 0)
        total_earned = profile.get('total_points_earned', 0)
        text += f"💰 <b>Баланс очков:</b> {balance}\n"
        text += f"💎 <b>Всего заработано:</b> {total_earned}\n\n"
        
        # Достижения
        achievements_count = profile.get('achievements_count', 0)
        text += f"🏆 <b>Достижений получено:</b> {achievements_count}\n\n"
        
        # Лучшие streak'и
        streaks = profile.get('best_streaks', {})
        text += "<b>🔥 Лучшие серии:</b>\n"
        text += f"• Привычки: {streaks.get('habits', 0)} дней\n"
        text += f"• Фокус: {streaks.get('focus', 0)} дней\n"
        text += f"• Чек-лист: {streaks.get('checklist', 0)} дней\n"
        text += f"• Без вредных привычек: {streaks.get('bad_habits', 0)} дней\n\n"
        
        # Общий прогресс
        progress = profile.get('total_progress', {})
        text += "<b>📊 Общий прогресс:</b>\n"
        text += f"• Привычек выполнено: {progress.get('habits_completed', 0)}\n"
        text += f"• Фокус-сессий: {progress.get('focus_sessions', 0)}\n"
        text += f"• Задач выполнено: {progress.get('tasks_completed', 0)}\n"
        text += f"• Часов в фокусе: {progress.get('focus_hours', 0)}\n\n"
        
        # Последние действия
        recent = profile.get('recent_actions', [])
        if recent:
            text += "<b>🕐 Последние действия:</b>\n"
            for action in recent[:3]:
                text += f"• {action['name']} (+{action['points']} очков)\n"
        
        logger.info(f"Профиль пользователя {user_id} успешно сформирован")
        
        await answer_method(
            text,
            reply_markup=get_profile_menu_keyboard(),
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Ошибка при показе профиля для пользователя {user_id}: {str(e)}", exc_info=True)
        await answer_method(
            "😔 Что-то пошло не так при загрузке профиля.\n\n"
            "Попробуй еще раз или обратись к администратору.",
            reply_markup=get_main_menu_keyboard()
        )


# === ДОСТИЖЕНИЯ ===

@router.callback_query(F.data == "view_achievements")
async def show_achievements_menu(callback: CallbackQuery):
    """Показывает меню достижений"""
    user_id = callback.from_user.id
    
    try:
        achievements = await gamification_db.get_user_achievements(user_id)
        
        text = "🏆 <b>Твои достижения</b>\n\n"
        
        if not achievements:
            text += "У тебя пока нет достижений.\n"
            text += "Выполняй задачи, развивай привычки и получай награды! 💪"
        else:
            text += f"Получено достижений: {len(achievements)}\n"
            text += f"Всего доступно: {len(ACHIEVEMENTS)}\n\n"
            
            # Показываем последние 5 достижений
            text += "<b>Последние полученные:</b>\n"
            for ach in achievements[:5]:
                emoji = ach.get('emoji', '🏅')
                name = ach.get('name', 'Достижение')
                rarity = ach.get('rarity', 'common')
                color = get_rarity_color(rarity)
                text += f"{emoji} {color} {name}\n"
            
            if len(achievements) > 5:
                text += f"\n...и еще {len(achievements) - 5} достижений"
        
        await callback.message.edit_text(
            text,
            reply_markup=get_achievements_keyboard(bool(achievements)),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Ошибка при показе достижений: {e}")
        await callback.answer(ERROR_MESSAGES['unknown_error'], show_alert=True)
    
    await callback.answer()


@router.callback_query(F.data == "all_achievements")
async def show_all_achievements(callback: CallbackQuery):
    """Показывает все достижения с категориями"""
    await callback.message.edit_text(
        "🏆 <b>Категории достижений</b>\n\n"
        "Выбери категорию для просмотра:",
        reply_markup=get_achievement_categories_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("ach_cat:"))
async def show_achievements_by_category(callback: CallbackQuery):
    """Показывает достижения по категории"""
    user_id = callback.from_user.id
    category = callback.data.split(":")[1]
    
    try:
        # Получаем достижения пользователя
        user_achievements = await gamification_db.get_user_achievements(user_id)
        user_ach_ids = [ach.get('achievement_id') for ach in user_achievements if 'achievement_id' in ach]
        
        # Фильтруем достижения по категории
        category_achievements = []
        for ach_id, ach_data in ACHIEVEMENTS.items():
            condition_type = ach_data['condition']['type']
            
            # Определяем категорию
            if category == 'habits' and condition_type == 'habit_streak':
                category_achievements.append((ach_id, ach_data))
            elif category == 'focus' and condition_type in ['focus_sessions', 'focus_hours']:
                category_achievements.append((ach_id, ach_data))
            elif category == 'tasks' and condition_type == 'tasks_completed':
                category_achievements.append((ach_id, ach_data))
            elif category == 'bad_habits' and condition_type == 'bad_habit_free':
                category_achievements.append((ach_id, ach_data))
            elif category == 'special' and condition_type in ['special', 'first_action']:
                category_achievements.append((ach_id, ach_data))
        
        # Формируем текст
        category_names = {
            'habits': '🌱 Достижения привычек',
            'focus': '🎯 Достижения фокуса',
            'tasks': '📋 Достижения задач',
            'bad_habits': '💪 Победа над вредными привычками',
            'special': '⭐ Особые достижения'
        }
        
        text = f"<b>{category_names.get(category, 'Достижения')}</b>\n\n"
        
        for ach_id, ach_data in category_achievements:
            emoji = ach_data['emoji']
            name = ach_data['name']
            description = ach_data['description']
            rarity = ach_data['rarity']
            color = get_rarity_color(rarity)
            
            if ach_id in user_ach_ids:
                text += f"✅ {emoji} <b>{name}</b> {color}\n"
            else:
                text += f"🔒 {emoji} <s>{name}</s> {color}\n"
            
            text += f"   <i>{description}</i>\n\n"
        
        await callback.message.edit_text(
            text,
            reply_markup=get_achievement_categories_keyboard(),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Ошибка при показе достижений категории: {e}")
        await callback.answer(ERROR_MESSAGES['unknown_error'], show_alert=True)
    
    await callback.answer()


@router.callback_query(F.data == "achievements_progress")
async def show_achievements_progress(callback: CallbackQuery):
    """Показывает прогресс по достижениям"""
    user_id = callback.from_user.id
    
    try:
        achievements = await gamification_db.get_user_achievements(user_id)
        user_ach_ids = [ach.get('achievement_id') for ach in achievements if 'achievement_id' in ach]
        
        # Считаем по редкости
        rarity_counts = {
            'common': {'total': 0, 'unlocked': 0},
            'rare': {'total': 0, 'unlocked': 0},
            'epic': {'total': 0, 'unlocked': 0},
            'legendary': {'total': 0, 'unlocked': 0}
        }
        
        for ach_id, ach_data in ACHIEVEMENTS.items():
            rarity = ach_data.get('rarity', 'common')
            rarity_counts[rarity]['total'] += 1
            if ach_id in user_ach_ids:
                rarity_counts[rarity]['unlocked'] += 1
        
        text = "📈 <b>Прогресс по достижениям</b>\n\n"
        
        total_unlocked = len(user_ach_ids)
        total_available = len(ACHIEVEMENTS)
        progress_percent = (total_unlocked / total_available * 100) if total_available > 0 else 0
        
        text += f"Общий прогресс: {total_unlocked}/{total_available} ({progress_percent:.1f}%)\n"
        text += f"{'█' * int(progress_percent / 10)}{'░' * (10 - int(progress_percent / 10))}\n\n"
        
        text += "<b>По редкости:</b>\n"
        for rarity, counts in rarity_counts.items():
            color = get_rarity_color(rarity)
            rarity_names = {
                'common': 'Обычные',
                'rare': 'Редкие',
                'epic': 'Эпические',
                'legendary': 'Легендарные'
            }
            name = rarity_names.get(rarity, rarity)
            unlocked = counts['unlocked']
            total = counts['total']
            text += f"{color} {name}: {unlocked}/{total}\n"
        
        # Ближайшие достижения
        text += "\n<b>🎯 Близко к получению:</b>\n"
        # Здесь можно добавить логику показа ближайших достижений
        
        await callback.message.edit_text(
            text,
            reply_markup=get_achievements_keyboard(),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Ошибка при показе прогресса: {e}")
        await callback.answer(ERROR_MESSAGES['unknown_error'], show_alert=True)
    
    await callback.answer()


# === ИСТОРИЯ ОЧКОВ ===

@router.callback_query(F.data == "points_history")
async def show_points_history(callback: CallbackQuery):
    """Показывает историю начисления очков"""
    user_id = callback.from_user.id
    
    try:
        history = await gamification_db.get_points_history(user_id, limit=15)
        balance = await gamification_db.get_points_balance(user_id)
        
        text = f"💰 <b>История очков</b>\n\n"
        text += f"Текущий баланс: {balance} очков\n\n"
        
        if not history:
            text += "История пока пуста.\n"
            text += "Выполняй задачи и получай очки! 💪"
        else:
            text += "<b>Последние начисления:</b>\n"
            
            reason_names = {
                'habit_completed': '✅ Привычка',
                'focus_session_complete': '🎯 Фокус',
                'task_completed': '📋 Задача',
                'achievement_unlocked': '🏆 Достижение',
                'bad_habit_day': '💪 День без вредной привычки',
                'habit_streak_bonus': '🔥 Бонус за streak'
            }
            
            for record in history:
                reason = record.get('reason', '')
                points = record.get('points', 0)
                timestamp = record.get('timestamp')
                
                action_name = reason_names.get(reason, 'Действие')
                
                if timestamp:
                    time_str = timestamp.strftime('%d.%m %H:%M')
                    text += f"{time_str} | {action_name} | +{points}\n"
        
        await callback.message.edit_text(
            text,
            reply_markup=get_back_to_profile_keyboard(),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Ошибка при показе истории очков: {e}")
        await callback.answer(ERROR_MESSAGES['unknown_error'], show_alert=True)
    
    await callback.answer()


# === СТАТИСТИКА ===

@router.callback_query(F.data == "detailed_stats")
async def show_detailed_stats(callback: CallbackQuery):
    """Показывает детальную статистику"""
    await callback.message.edit_text(
        "📊 <b>Детальная статистика</b>\n\n"
        "Выбери тип статистики:",
        reply_markup=get_stats_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "stats_by_module")
async def show_stats_by_module(callback: CallbackQuery):
    """Показывает статистику по модулям"""
    user_id = callback.from_user.id
    
    try:
        profile = await gamification_db.get_user_profile(user_id)
        progress = profile.get('total_progress', {})
        
        text = "📊 <b>Статистика по модулям</b>\n\n"
        
        # Привычки
        text += "🌱 <b>Привычки:</b>\n"
        text += f"• Выполнено: {progress.get('habits_completed', 0)} раз\n"
        text += f"• Лучший streak: {profile.get('best_streaks', {}).get('habits', 0)} дней\n\n"
        
        # Фокус
        text += "🎯 <b>Фокус:</b>\n"
        text += f"• Сессий: {progress.get('focus_sessions', 0)}\n"
        text += f"• Часов в фокусе: {progress.get('focus_hours', 0)}\n"
        text += f"• Лучший streak: {profile.get('best_streaks', {}).get('focus', 0)} дней\n\n"
        
        # Чек-лист
        text += "📋 <b>Чек-лист:</b>\n"
        text += f"• Выполнено задач: {progress.get('tasks_completed', 0)}\n"
        text += f"• Лучший streak: {profile.get('best_streaks', {}).get('checklist', 0)} дней\n\n"
        
        # Вредные привычки
        text += "💪 <b>Воздержание:</b>\n"
        text += f"• Лучший результат: {profile.get('best_streaks', {}).get('bad_habits', 0)} дней\n"
        
        await callback.message.edit_text(
            text,
            reply_markup=get_stats_keyboard(),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Ошибка при показе статистики по модулям: {e}")
        await callback.answer(ERROR_MESSAGES['unknown_error'], show_alert=True)
    
    await callback.answer()


# === ФУНКЦИЯ ДЛЯ ПОКАЗА НОВЫХ ДОСТИЖЕНИЙ ===

async def show_new_achievements(message: Message, achievement_ids: List[str]):
    """
    Показывает уведомления о новых достижениях
    """
    for ach_id in achievement_ids:
        achievement_text = get_achievement_message(ach_id)
        if achievement_text:
            await message.answer(
                achievement_text,
                parse_mode="HTML"
            )