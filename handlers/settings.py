"""
Обработчики для раздела настроек
"""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

from database.firestore_db import FirestoreDB
from database.settings_db import SettingsDB
from keyboards.settings import get_settings_keyboard
from keyboards.main_menu import get_main_menu_keyboard

logger = logging.getLogger(__name__)
router = Router()


async def show_settings_menu(message: Message):
    """Показать меню настроек"""
    try:
        # Получаем экземпляр БД
        db = FirestoreDB()
        settings_db = SettingsDB(db.db)
        
        # Получаем текущие настройки
        user_id = str(message.from_user.id)
        settings = settings_db.get_settings(user_id)
        
        # Формируем текст
        notifications_status = "Включены" if settings['notifications_enabled'] else "Выключены"
        theme_names = {
            'system': 'System',
            'light': 'Light', 
            'dark': 'Dark'
        }
        current_theme = theme_names.get(settings['theme'], 'System')
        
        text = (
            "⚙️ <b>Настройки</b>\n\n"
            f"🔔 Уведомления: <b>{notifications_status}</b>\n"
            f"🎨 Тема: <b>{current_theme}</b>\n\n"
            "<i>Тема применится в Mini App</i>"
        )
        
        await message.answer(
            text,
            reply_markup=get_settings_keyboard(settings),
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Ошибка показа настроек: {e}", exc_info=True)
        await message.answer(
            "❌ Произошла ошибка при загрузке настроек",
            reply_markup=get_main_menu_keyboard()
        )


# Обработчик команды /settings
@router.message(Command("settings"))
async def settings_command(message: Message):
    """Обработчик команды /settings"""
    await show_settings_menu(message)


# Обработчик кнопки из меню
@router.message(F.text == "⚙ Настройки")
async def settings_button(message: Message):
    """Обработчик кнопки Настройки из главного меню"""
    await show_settings_menu(message)


# Переключение уведомлений
@router.callback_query(F.data == "toggle_notifications")
async def toggle_notifications_handler(callback: CallbackQuery):
    """Переключить уведомления вкл/выкл"""
    try:
        # Получаем БД
        db = FirestoreDB()
        settings_db = SettingsDB(db.db)
        
        user_id = str(callback.from_user.id)
        
        # Переключаем
        new_value = settings_db.toggle_notifications(user_id)
        
        # Получаем все настройки для обновления клавиатуры
        settings = settings_db.get_settings(user_id)
        
        # Обновляем сообщение
        notifications_status = "Включены" if new_value else "Выключены"
        theme_names = {
            'system': 'System',
            'light': 'Light',
            'dark': 'Dark'
        }
        current_theme = theme_names.get(settings['theme'], 'System')
        
        text = (
            "⚙️ <b>Настройки</b>\n\n"
            f"🔔 Уведомления: <b>{notifications_status}</b>\n"
            f"🎨 Тема: <b>{current_theme}</b>\n\n"
            "<i>Тема применится в Mini App</i>"
        )
        
        await callback.message.edit_text(
            text,
            reply_markup=get_settings_keyboard(settings),
            parse_mode="HTML"
        )
        
        # Отвечаем коротким уведомлением
        await callback.answer(f"Уведомления: {notifications_status}")
        
    except Exception as e:
        logger.error(f"Ошибка переключения уведомлений: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка", show_alert=True)


# Установка темы
@router.callback_query(F.data.startswith("set_theme:"))
async def set_theme_handler(callback: CallbackQuery):
    """Установить тему"""
    try:
        # Извлекаем тему из callback_data
        theme = callback.data.split(":")[1]
        
        # Получаем БД
        db = FirestoreDB()
        settings_db = SettingsDB(db.db)
        
        user_id = str(callback.from_user.id)
        
        # Обновляем тему
        updated_settings = settings_db.update_settings(
            user_id,
            {'theme': theme}
        )
        
        # Обновляем сообщение
        notifications_status = "Включены" if updated_settings['notifications_enabled'] else "Выключены"
        theme_names = {
            'system': 'System',
            'light': 'Light',
            'dark': 'Dark'
        }
        current_theme = theme_names.get(theme, 'System')
        
        text = (
            "⚙️ <b>Настройки</b>\n\n"
            f"🔔 Уведомления: <b>{notifications_status}</b>\n"
            f"🎨 Тема: <b>{current_theme}</b>\n\n"
            "<i>Тема применится в Mini App</i>"
        )
        
        await callback.message.edit_text(
            text,
            reply_markup=get_settings_keyboard(updated_settings),
            parse_mode="HTML"
        )
        
        # Отвечаем коротким уведомлением
        await callback.answer(f"Тема сохранена: {current_theme} (применится в Mini App)")
        
    except Exception as e:
        logger.error(f"Ошибка установки темы: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка", show_alert=True)


# Возврат в главное меню
@router.callback_query(F.data == "settings_back_to_main")
async def back_to_main_handler(callback: CallbackQuery):
    """Вернуться в главное меню"""
    try:
        await callback.message.delete()
        await callback.message.answer(
            "Выберите действие:",
            reply_markup=get_main_menu_keyboard()
        )
    except Exception as e:
        logger.error(f"Ошибка возврата в меню: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка", show_alert=True)

@router.callback_query(F.data == "toggle_notifications")
async def toggle_notifications_handler(callback: CallbackQuery):
    """Переключить уведомления вкл/выкл"""
    try:
        # Получаем БД
        logger.info("Начинаем переключение уведомлений...")
        db = FirestoreDB()
        logger.info("FirestoreDB создан")
        
        settings_db = SettingsDB(db.db)
        logger.info("SettingsDB создан")
        
        user_id = str(callback.from_user.id)
        logger.info(f"User ID: {user_id}")
        
        # Переключаем
        new_value = settings_db.toggle_notifications(user_id)
        logger.info(f"Новое значение: {new_value}")
        
        # Получаем все настройки для обновления клавиатуры
        settings = settings_db.get_settings(user_id)
        logger.info(f"Настройки получены: {settings}")
        
        # Обновляем сообщение
        notifications_status = "Включены" if new_value else "Выключены"
        theme_names = {
            'system': 'System',
            'light': 'Light',
            'dark': 'Dark'
        }
        current_theme = theme_names.get(settings['theme'], 'System')
        
        text = (
            "⚙️ <b>Настройки</b>\n\n"
            f"🔔 Уведомления: <b>{notifications_status}</b>\n"
            f"🎨 Тема: <b>{current_theme}</b>\n\n"
            "<i>Тема применится в Mini App</i>"
        )
        
        await callback.message.edit_text(
            text,
            reply_markup=get_settings_keyboard(settings),
            parse_mode="HTML"
        )
        
        # Отвечаем коротким уведомлением
        await callback.answer(f"Уведомления: {notifications_status}")
        
    except Exception as e:
    # Выводим ошибку прямо в чат для отладки
      error_text = f"Тип: {type(e).__name__}\nТекст: {str(e)}\nАтрибуты: {dir(e)}"
    logger.error(f"ОТЛАДКА: {error_text}")
    
    # Показываем детали пользователю временно
    await callback.answer(error_text[:200], show_alert=True)
    
    # Также отправим в чат для лучшей видимости
    await callback.message.answer(f"<pre>ОТЛАДКА ОШИБКИ:\n{error_text}</pre>", parse_mode="HTML")