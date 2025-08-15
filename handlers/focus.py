"""
Обработчики для модуля фокусировки (Помодоро)
Полностью интегрирован с новым FocusService
"""
import logging
from datetime import datetime, timezone
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from aiogram.fsm.state import default_state
from aiogram.filters import Command

# Импорты из новых модулей
from services.focus_service import FocusService, SessionType
from states.focus import FocusStates
from keyboards.focus import (
    get_focus_menu_keyboard,
    get_session_control_keyboard,
    get_duration_presets_keyboard,
    get_focus_settings_keyboard,
    get_stats_period_keyboard
)
from keyboards.main_menu import get_main_menu_keyboard

logger = logging.getLogger(__name__)
router = Router()

# 👉 Глобальная ссылка, которую заполнит main.py после создания сервиса
focus_service: FocusService | None = None

def _get_focus_service() -> FocusService:
    """Получает FocusService из глобальной переменной"""
    assert focus_service is not None, "FocusService не инициализирован"
    return focus_service

# ДОБАВЛЕНО: Хранилище для связи сообщений с сессиями
session_messages = {}


# === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===

def create_progress_bar(elapsed: int, total: int, length: int = 20) -> str:
    """
    Создает визуальный прогресс-бар для таймера
    ДОБАВЛЕНО: Новая функция для отображения прогресса
    """
    if total == 0:
        return "▱" * length
    
    filled = int(length * elapsed / total)
    empty = length - filled
    
    bar = "▰" * filled + "▱" * empty
    percentage = int(100 * elapsed / total)
    
    return f"[{bar}] {percentage}%"


async def update_session_progress(bot: Bot, session_id: str, remaining_minutes: int):
    """
    Обновляет сообщение с прогрессом сессии
    ДОБАВЛЕНО: Колбек для обновления UI при каждом тике таймера
    """
    if session_id not in session_messages:
        return
    
    msg_info = session_messages[session_id]
    service = _get_focus_service()
    
    if not service:
        return
    
    try:
        # Получаем информацию о сессии
        session = await service.get_session_info(msg_info['user_id'])
        if not session:
            return
        
        # Рассчитываем прошедшее время
        elapsed = session['duration_minutes'] - remaining_minutes
        
        # Формируем прогресс-бар
        progress_bar = create_progress_bar(elapsed, session['duration_minutes'])
        
        # Определяем тип сессии
        session_type = "🎯 Работа" if session['type'] == 'work' else "☕ Перерыв"
        
        # Формируем текст
        text = (
            f"{session_type} - <b>Сессия активна</b>\n\n"
            f"⏱ Длительность: {session['duration_minutes']} минут\n"
            f"{progress_bar}\n"
            f"⏰ Осталось: {remaining_minutes} мин\n"
            f"✅ Пройдено: {elapsed} мин"
        )
        
        # Обновляем сообщение
        await bot.edit_message_text(
            text=text,
            chat_id=msg_info['chat_id'],
            message_id=msg_info['message_id'],
            reply_markup=get_session_control_keyboard(),
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Ошибка обновления прогресса сессии {session_id}: {e}")


# === ГЛАВНОЕ МЕНЮ ФОКУСА ===

@router.message(F.text == "⏱ Фокус")
async def handle_focus_menu(message: Message, state: FSMContext = None):
    """Обработчик кнопки Фокус из главного меню"""
    if state:
        await state.clear()
    await show_focus_menu(message)


async def show_focus_menu(message: Message):
    """Показывает главное меню фокуса"""
    service = _get_focus_service()
    
    # ИЗМЕНЕНО: Убрана временная заглушка, добавлена более информативная диагностика
    if not service:
        logger.error("FocusService не инициализирован при попытке показать меню")
        await message.answer(
            "❌ Ошибка инициализации модуля фокуса.\n"
            "Пожалуйста, перезапустите бота командой /start",
            reply_markup=get_main_menu_keyboard()
        )
        return
    
    user_id = str(message.from_user.id)
    
    try:
        # Проверяем активную сессию
        session = await service.get_session_info(user_id)
        
        if session:
            # Есть активная сессия
            status_emoji = "⏸" if session['status'] == 'paused' else "⏱"
            session_type = "🎯 Работа" if session['type'] == 'work' else "☕ Перерыв"
            
            text = (
                f"{status_emoji} <b>Активная сессия</b>\n\n"
                f"Тип: {session_type}\n"
                f"Статус: {'На паузе' if session['status'] == 'paused' else 'Активна'}\n"
                f"Осталось: {session.get('remaining_minutes', 0)} мин\n"
                f"Прошло: {session.get('elapsed_minutes', 0)} мин"
            )
            
            keyboard = get_session_control_keyboard(
                is_paused=(session['status'] == 'paused')
            )
        else:
            # Нет активной сессии
            settings = await service.db.get_user_settings(user_id)
            stats = await service.db.get_user_stats(user_id)
            
            text = (
                "🎯 <b>Фокус-режим</b>\n\n"
                "Техника Помодоро для продуктивной работы:\n"
                f"• ⏱ {settings['work_duration']} минут работы\n"
                f"• ☕ {settings['short_break_duration']} минут перерыва\n"
                f"• 🌴 {settings['long_break_duration']} минут длинный перерыв\n\n"
                f"🔥 Текущий streak: {stats.get('current_streak', 0)} дней\n"
                f"📊 Сегодня: {stats.get('sessions_today', 0)} сессий"
            )
            
            keyboard = get_focus_menu_keyboard()
    
    except Exception as e:
        logger.error(f"Ошибка при показе меню фокуса: {e}", exc_info=True)
        text = "❌ Произошла ошибка при загрузке меню"
        keyboard = get_main_menu_keyboard()
    
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


# === УПРАВЛЕНИЕ СЕССИЕЙ ===

@router.callback_query(F.data == "start_focus")
async def start_focus_session(callback: CallbackQuery, state: FSMContext):
    """Запускает новую фокус-сессию"""
    service = _get_focus_service()
    
    if not service:
        await callback.answer("Сервис недоступен", show_alert=True)
        return
    
    user_id = str(callback.from_user.id)
    
    try:
        logger.info(f"Пользователь {user_id} запускает фокус-сессию")
        
        # Запускаем сессию через сервис
        session = await service.start_session(user_id)
        
        # Устанавливаем состояние
        await state.set_state(FocusStates.in_focus_session)
        await state.update_data(session_id=session['id'])
        
        # ДОБАВЛЕНО: Сохраняем связь сессии с сообщением для обновления прогресса
        session_messages[session['id']] = {
            'chat_id': callback.message.chat.id,
            'message_id': callback.message.message_id,
            'user_id': user_id
        }
        
        # Формируем текст с прогресс-баром
        progress_bar = create_progress_bar(0, session['duration_minutes'])
        text = (
            f"🎯 <b>Фокус-сессия началась!</b>\n\n"
            f"⏱ Длительность: {session['duration_minutes']} минут\n"
            f"{progress_bar}\n"
            f"⏰ Осталось: {session['duration_minutes']} мин\n\n"
            f"💡 Советы:\n"
            f"• Отключи уведомления\n"
            f"• Сосредоточься на одной задаче\n"
            f"• Не отвлекайся на соцсети"
        )
        
        await callback.message.edit_text(
            text,
            reply_markup=get_session_control_keyboard(),
            parse_mode="HTML"
        )
        
        logger.info(f"Фокус-сессия {session['id']} успешно запущена")
        
    except ValueError as e:
        logger.warning(f"Ошибка при запуске сессии: {e}")
        await callback.answer(str(e), show_alert=True)
    except Exception as e:
        logger.error(f"Неожиданная ошибка при запуске сессии: {e}", exc_info=True)
        await callback.answer("Произошла ошибка. Попробуйте позже.", show_alert=True)
    
    await callback.answer()


@router.callback_query(F.data == "pause_focus", StateFilter(FocusStates.in_focus_session))
async def pause_focus_session(callback: CallbackQuery, state: FSMContext):
    """Ставит сессию на паузу"""
    service = _get_focus_service()
    
    if not service:
        await callback.answer("Сервис недоступен", show_alert=True)
        return
    
    user_id = str(callback.from_user.id)
    
    try:
        logger.info(f"Пользователь {user_id} ставит сессию на паузу")
        
        session = await service.pause_session(user_id)
        
        # ДОБАВЛЕНО: Прогресс-бар при паузе
        progress_bar = create_progress_bar(
            session['completed_minutes'], 
            session['duration_minutes']
        )
        
        text = (
            f"⏸ <b>Сессия на паузе</b>\n\n"
            f"{progress_bar}\n"
            f"Прошло времени: {session['completed_minutes']} мин\n"
            f"Осталось: {session['duration_minutes'] - session['completed_minutes']} мин\n\n"
            f"Нажми 'Продолжить' когда будешь готов"
        )
        
        await callback.message.edit_text(
            text,
            reply_markup=get_session_control_keyboard(is_paused=True),
            parse_mode="HTML"
        )
        
        logger.info(f"Сессия {session['id']} поставлена на паузу")
        
    except ValueError as e:
        logger.warning(f"Ошибка при паузе сессии: {e}")
        await callback.answer(str(e), show_alert=True)
    except Exception as e:
        logger.error(f"Неожиданная ошибка при паузе: {e}", exc_info=True)
        await callback.answer("Произошла ошибка", show_alert=True)
    
    await callback.answer()


@router.callback_query(F.data == "resume_focus", StateFilter(FocusStates.in_focus_session))
async def resume_focus_session(callback: CallbackQuery, state: FSMContext):
    """Возобновляет сессию после паузы"""
    service = _get_focus_service()
    
    if not service:
        await callback.answer("Сервис недоступен", show_alert=True)
        return
    
    user_id = str(callback.from_user.id)
    
    try:
        logger.info(f"Пользователь {user_id} возобновляет сессию")
        
        session = await service.resume_session(user_id)
        
        remaining = session['duration_minutes'] - session['completed_minutes']
        
        # ДОБАВЛЕНО: Восстанавливаем связь сессии с сообщением для обновления прогресса
        session_messages[session['id']] = {
            'chat_id': callback.message.chat.id,
            'message_id': callback.message.message_id,
            'user_id': user_id
        }
        
        # ДОБАВЛЕНО: Прогресс-бар при возобновлении
        progress_bar = create_progress_bar(
            session['completed_minutes'], 
            session['duration_minutes']
        )
        
        text = (
            f"▶️ <b>Сессия возобновлена</b>\n\n"
            f"{progress_bar}\n"
            f"Осталось времени: {remaining} мин\n"
            f"Продолжай работать!"
        )
        
        await callback.message.edit_text(
            text,
            reply_markup=get_session_control_keyboard(),
            parse_mode="HTML"
        )
        
        logger.info(f"Сессия {session['id']} возобновлена")
        
    except ValueError as e:
        logger.warning(f"Ошибка при возобновлении: {e}")
        await callback.answer(str(e), show_alert=True)
    except Exception as e:
        logger.error(f"Неожиданная ошибка при возобновлении: {e}", exc_info=True)
        await callback.answer("Произошла ошибка", show_alert=True)
    
    await callback.answer()


@router.callback_query(F.data == "stop_focus", StateFilter(FocusStates.in_focus_session))
async def stop_focus_session(callback: CallbackQuery, state: FSMContext):
    """Останавливает текущую сессию"""
    service = _get_focus_service()
    
    if not service:
        await callback.answer("Сервис недоступен", show_alert=True)
        return
    
    user_id = str(callback.from_user.id)
    
    try:
        logger.info(f"Пользователь {user_id} останавливает сессию")
        
        # Получаем информацию о сессии перед остановкой
        session = await service.get_session_info(user_id)
        
        if not session:
            await callback.answer("Активная сессия не найдена", show_alert=True)
            await state.clear()
            return
        
        # Останавливаем сессию
        completed_minutes, is_completed = await service.stop_session(user_id, completed=False)
        
        # ДОБАВЛЕНО: Удаляем связь сессии с сообщением
        if session['id'] in session_messages:
            del session_messages[session['id']]
        
        # Очищаем состояние
        await state.clear()
        
        # Формируем сообщение с финальным прогрессом
        progress_bar = create_progress_bar(completed_minutes, session['duration_minutes'])
        
        if is_completed:
            text = (
                f"✅ <b>Сессия завершена!</b>\n\n"
                f"{progress_bar}\n"
                f"Отличная работа! Ты продержался {completed_minutes} минут.\n"
                f"Время сделать перерыв 😊"
            )
        else:
            text = (
                f"⏹ <b>Сессия прервана</b>\n\n"
                f"{progress_bar}\n"
                f"Ты проработал {completed_minutes} минут.\n"
                f"В следующий раз постарайся дойти до конца!"
            )
        
        await callback.message.edit_text(
            text,
            reply_markup=get_focus_menu_keyboard(),
            parse_mode="HTML"
        )
        
        logger.info(f"Сессия {session['id']} остановлена ({'завершена' if is_completed else 'отменена'})")
        
    except ValueError as e:
        logger.warning(f"Ошибка при остановке сессии: {e}")
        await callback.answer(str(e), show_alert=True)
    except Exception as e:
        logger.error(f"Неожиданная ошибка при остановке: {e}", exc_info=True)
        await callback.answer("Произошла ошибка", show_alert=True)
    
    await callback.answer()


# === НАСТРОЙКИ ===

@router.callback_query(F.data == "focus_settings")
async def show_focus_settings(callback: CallbackQuery):
    """Показывает настройки фокуса"""
    service = _get_focus_service()
    
    if not service:
        await callback.answer("Сервис недоступен", show_alert=True)
        return
    
    user_id = str(callback.from_user.id)
    
    try:
        settings = await service.db.get_user_settings(user_id)
        
        # notifications removed - убрано отображение настройки уведомлений
        text = (
            f"⚙️ <b>Настройки фокуса</b>\n\n"
            f"⏱ Рабочая сессия: {settings['work_duration']} мин\n"
            f"☕ Короткий перерыв: {settings['short_break_duration']} мин\n"
            f"🌴 Длинный перерыв: {settings['long_break_duration']} мин\n"
            f"🔄 Авто-перерыв: {'✅ Вкл' if settings['auto_start_break'] else '❌ Выкл'}\n"
            f"🎯 Цель на день: {settings['daily_goal']} сессий"
        )
        
        await callback.message.edit_text(
            text,
            reply_markup=get_focus_settings_keyboard(settings),
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Ошибка при показе настроек: {e}", exc_info=True)
        await callback.answer("Произошла ошибка", show_alert=True)
    
    await callback.answer()


@router.callback_query(F.data.startswith("set_duration:"))
async def set_duration(callback: CallbackQuery):
    """Устанавливает длительность сессий"""
    service = _get_focus_service()
    
    if not service:
        await callback.answer("Сервис недоступен", show_alert=True)
        return
    
    user_id = str(callback.from_user.id)
    _, duration_type = callback.data.split(":")
    
    # Показываем варианты длительности
    if duration_type == "work":
        text = "⏱ <b>Выберите длительность рабочей сессии:</b>"
        presets = [15, 25, 30, 45, 50, 60]
    elif duration_type == "short_break":
        text = "☕ <b>Выберите длительность короткого перерыва:</b>"
        presets = [3, 5, 10, 15]
    else:  # long_break
        text = "🌴 <b>Выберите длительность длинного перерыва:</b>"
        presets = [15, 20, 25, 30]
    
    keyboard = get_duration_presets_keyboard(duration_type, presets)
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("duration:"))
async def save_duration(callback: CallbackQuery):
    """Сохраняет выбранную длительность"""
    service = _get_focus_service()
    
    if not service:
        await callback.answer("Сервис недоступен", show_alert=True)
        return
    
    user_id = str(callback.from_user.id)
    _, duration_type, minutes = callback.data.split(":")
    minutes = int(minutes)
    
    try:
        # Формируем обновление настроек
        settings_update = {}
        if duration_type == "work":
            settings_update['work_duration'] = minutes
            message = f"✅ Рабочая сессия: {minutes} мин"
        elif duration_type == "short_break":
            settings_update['short_break_duration'] = minutes
            message = f"✅ Короткий перерыв: {minutes} мин"
        else:
            settings_update['long_break_duration'] = minutes
            message = f"✅ Длинный перерыв: {minutes} мин"
        
        # Обновляем настройки
        await service.update_settings(user_id, settings_update)
        
        await callback.answer(message)
        
        # Возвращаемся в настройки
        await show_focus_settings(callback)
        
    except Exception as e:
        logger.error(f"Ошибка при сохранении длительности: {e}", exc_info=True)
        await callback.answer("Произошла ошибка", show_alert=True)


# notifications removed - полностью удален обработчик toggle_notifications


@router.callback_query(F.data == "toggle_auto_break")
async def toggle_auto_break(callback: CallbackQuery):
    """Переключает автоматический переход на перерыв"""
    service = _get_focus_service()
    
    if not service:
        await callback.answer("Сервис недоступен", show_alert=True)
        return
    
    user_id = str(callback.from_user.id)
    
    try:
        # Получаем текущие настройки
        settings = await service.db.get_user_settings(user_id)
        new_value = not settings['auto_start_break']
        
        # Обновляем
        await service.update_settings(user_id, {'auto_start_break': new_value})
        
        await callback.answer(
            f"Авто-перерыв {'включен ✅' if new_value else 'выключен ❌'}"
        )
        
        # Обновляем меню настроек
        await show_focus_settings(callback)
        
    except Exception as e:
        logger.error(f"Ошибка при переключении авто-перерыва: {e}", exc_info=True)
        await callback.answer("Произошла ошибка", show_alert=True)


# === СТАТИСТИКА ===

@router.callback_query(F.data == "focus_stats")
async def show_focus_stats(callback: CallbackQuery):
    """Показывает статистику фокус-сессий"""
    service = _get_focus_service()
    
    if not service:
        await callback.answer("Сервис недоступен", show_alert=True)
        return
    
    await callback.message.edit_text(
        "📊 <b>Выберите период для статистики:</b>",
        reply_markup=get_stats_period_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("stats_period:"))
async def show_period_stats(callback: CallbackQuery):
    """Показывает статистику за выбранный период"""
    service = _get_focus_service()
    
    if not service:
        await callback.answer("Сервис недоступен", show_alert=True)
        return
    
    user_id = str(callback.from_user.id)
    _, period = callback.data.split(":")
    
    try:
        # Получаем статистику за период
        stats = await service.get_stats(user_id, period)
        
        # Формируем текст
        period_names = {
            'today': 'Сегодня',
            'week': 'За неделю',
            'month': 'За месяц',
            'all': 'За всё время'
        }
        
        text = f"📊 <b>Статистика {period_names[period]}</b>\n\n"
        text += f"✅ Завершено сессий: {stats['completed_sessions']}\n"
        text += f"⏱ Общее время фокуса: {stats['total_minutes']} мин\n"
        text += f"📈 Средняя продолжительность: {stats['avg_duration']} мин\n"
        text += f"🔥 Текущий streak: {stats['current_streak']} дней\n"
        text += f"🏆 Лучший streak: {stats['best_streak']} дней"
        
        keyboard = InlineKeyboardBuilder()
        keyboard.row(
            InlineKeyboardButton(text="🔙 Назад", callback_data="focus_stats")
        )
        
        await callback.message.edit_text(
            text,
            reply_markup=keyboard.as_markup(),
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Ошибка при показе статистики: {e}", exc_info=True)
        await callback.answer("Произошла ошибка", show_alert=True)
    
    await callback.answer()


# === ПОМОЩЬ ===

@router.callback_query(F.data == "focus_help")
async def show_focus_help(callback: CallbackQuery):
    """Показывает справку по модулю фокуса"""
    text = (
        "❓ <b>Как работает фокус-режим</b>\n\n"
        "🎯 <b>Техника Помодоро</b>\n"
        "• Работай 25 минут без отвлечений\n"
        "• Сделай перерыв 5 минут\n"
        "• После 4 сессий - длинный перерыв\n\n"
        "⏱ <b>Управление таймером</b>\n"
        "• Запусти сессию кнопкой 'Начать'\n"
        "• Можешь поставить на паузу\n"
        "• Или остановить досрочно\n\n"
        "📊 <b>Отслеживай прогресс</b>\n"
        "• Смотри статистику за разные периоды\n"
        "• Поддерживай streak каждый день\n"
        "• Ставь цели и достигай их!"
    )
    
    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="focus")
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=keyboard.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()


# === НАВИГАЦИЯ ===

@router.callback_query(F.data == "focus")
async def back_to_focus_menu(callback: CallbackQuery):
    """Возврат в главное меню фокуса"""
    # Создаем объект Message из callback для переиспользования show_focus_menu
    await show_focus_menu(callback.message)
    await callback.answer()


@router.callback_query(F.data == "back_to_main")
async def back_to_main_menu(callback: CallbackQuery):
    """Возврат в главное меню бота"""
    await callback.message.edit_text(
        "Выберите действие:",
        reply_markup=get_main_menu_keyboard()
    )
    await callback.answer()


# === ОТЛАДОЧНАЯ КОМАНДА ===

@router.message(Command("focus_status"))
async def debug_focus_status(message: Message):
    """Отладочная команда для проверки состояния сервиса"""
    service = _get_focus_service()
    
    if not service:
        await message.answer("❌ FocusService не инициализирован")
        return
    
    user_id = str(message.from_user.id)
    
    try:
        session = await service.get_session_info(user_id)
        active_timers = service.scheduler.get_active_timers()
        
        text = "🔍 <b>Состояние Focus сервиса</b>\n\n"
        text += f"✅ Сервис активен\n"
        text += f"⏱ Активных таймеров: {len(active_timers)}\n\n"
        
        if session:
            text += f"📍 <b>Ваша сессия:</b>\n"
            text += f"ID: {session['id']}\n"
            text += f"Статус: {session['status']}\n"
            text += f"Осталось: {session.get('remaining_minutes', 0)} мин"
        else:
            text += "📍 У вас нет активной сессии"
        
        await message.answer(text, parse_mode="HTML")
        
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")


# Для импорта из других модулей
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
