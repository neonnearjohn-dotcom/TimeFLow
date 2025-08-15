"""
Тестовая версия бота без Firestore
"""
import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher, Router, F
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.types import KeyboardButton

# Импортируем конфигурацию
from config import BOT_TOKEN

# Создаем роутер
router = Router()

def get_main_menu_keyboard():
    """Создает клавиатуру главного меню"""
    builder = ReplyKeyboardBuilder()
    
    buttons = [
        KeyboardButton(text="📊 Трекеры"),
        KeyboardButton(text="✅ Чек-лист"),
        KeyboardButton(text="🎯 Фокус"),
        KeyboardButton(text="🤖 Ассистент"),
        KeyboardButton(text="👤 Профиль"),
        KeyboardButton(text="⚙️ Настройки")
    ]
    
    for button in buttons:
        builder.add(button)
    
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

@router.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    await message.answer(
        f"👋 Привет, {message.from_user.full_name}!\n\n"
        f"🔧 <b>Тестовый режим</b> (без базы данных)\n"
        f"Твой Telegram ID: <code>{message.from_user.id}</code>\n\n"
        "Выбери раздел:",
        reply_markup=get_main_menu_keyboard(),
        parse_mode="HTML"
    )

@router.message(F.text == "📊 Трекеры")
async def handle_trackers(message: Message):
    await message.answer(
        "📊 <b>Трекер привычек</b>\n\n"
        "⚠️ В тестовом режиме функции трекера недоступны.\n"
        "Для полной функциональности настройте Firestore.",
        parse_mode="HTML"
    )

@router.message(F.text == "🎯 Фокус")
async def handle_focus(message: Message):
    await message.answer(
        "🎯 <b>Фокус-режим</b>\n\n"
        "⚠️ В тестовом режиме таймер недоступен.\n"
        "Для полной функциональности настройте Firestore.",
        parse_mode="HTML"
    )

@router.message(F.text == "✅ Чек-лист")
async def handle_checklist(message: Message):
    await message.answer("✅ Раздел чек-листов в разработке...")

@router.message(F.text == "🤖 Ассистент")
async def handle_assistant(message: Message):
    await message.answer("🤖 Ассистент в разработке...")

@router.message(F.text == "👤 Профиль")
async def handle_profile(message: Message):
    await message.answer("👤 Профиль в разработке...")

@router.message(F.text == "⚙️ Настройки")
async def handle_settings(message: Message):
    await message.answer("⚙️ Настройки в разработке...")

async def main():
    """Основная функция для запуска бота"""
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    # Инициализация бота
    bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
    dp = Dispatcher(storage=MemoryStorage())
    
    # Подключаем роутер
    dp.include_router(router)
    
    # Удаляем вебхуки и запускаем polling
    await bot.delete_webhook(drop_pending_updates=True)
    
    logger.info("🚀 Тестовый бот запущен (без Firestore)!")
    logger.info(f"Ваш токен: {BOT_TOKEN[:10]}...{BOT_TOKEN[-5:]}")
    
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())