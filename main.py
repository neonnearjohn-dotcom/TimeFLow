"""
Главный файл для запуска телеграм-бота
"""
import asyncio
import logging
import os
import sys
from venv import logger

from pytest import Config
from config import BOT_TOKEN

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

# База данных
from database.firestore_db import FirestoreDB
from database.focus_db import FocusDB
from database.focus_db_memory import FocusDBMemory

# Focus модули
from services.focus_service import FocusService
from utils.focus_scheduler import focus_scheduler

# Импортируем обработчики
from handlers import start, menu, trackers, focus, checklist, profile, assistant, settings, assistant_onboarding, assistant_plan

from utils.logging import setup_json_logging, get_logger, set_request_id, setup_logging
from utils.notify import make_notifier
from utils.firestore_client import create_firestore_client

import signal
from typing import Optional
from google.cloud import firestore

from services.pomodoro_service import PomodoroService
from tasks.pomodoro_recovery import recovery_pass, start_scheduler

shutdown_event: Optional[asyncio.Event] = None
scheduler_task: Optional[asyncio.Task] = None

setup_json_logging("INFO")
log = get_logger(__name__)
log.info("Starting TimeFlow bot")

def CorrelationMiddleware():
    raise NotImplementedError

async def main():
    """
    Основная функция для запуска бота
    """
    """Основная точка входа приложения."""
    global shutdown_event, scheduler_task
    # Настройка логирования
    log_level = os.getenv("LOG_LEVEL", "INFO")
    setup_logging(level=log_level)
    
    logger.info("Starting TimeFlow Bot")
    
    # Инициализация конфига
    config = Config()
    
    # Инициализация бота
    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    db = create_firestore_client()
    pomodoro_service = PomodoroService(db) if db else None

    # Инициализация диспетчера
    dp = Dispatcher()
    
    # Подключение middleware
    dp.update.middleware(CorrelationMiddleware())
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('bot.log', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    logger = logging.getLogger(__name__)
    
    # Инициализация бота и диспетчера
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML
        )
    )
    
    # Создаем диспетчер с хранилищем состояний в памяти
    dp = Dispatcher(storage=MemoryStorage())
    
    # --- ИНИЦИАЛИЗАЦИЯ FOCUS ---
    try:
        logger.info("Инициализация Focus модуля...")
        
        # Запускаем планировщик
        await focus_scheduler.start()
        logger.info("Focus планировщик запущен")
        
        # Создаем БД с обработкой ошибок Firestore
        try:
            db = FirestoreDB()
            focus_db = FocusDB(db.db)
            logger.info("Focus БД инициализирована с Firestore")
        except Exception as db_error:
            logger.warning(f"Не удалось инициализировать Firestore: {db_error}")
            logger.info("Focus будет работать с данными в памяти (без сохранения)")
            # Используем in-memory версию БД
            focus_db = FocusDBMemory()
        
        # Создаем сервис с поддержкой обновления UI
        focus_service = FocusService(focus_db, focus_scheduler, bot)
        logger.info("FocusService создан с поддержкой обновления UI")
        
        # Восстанавливаем активные сессии после перезапуска
        restored_count = await focus_service.restore_active_sessions()
        logger.info(f"Восстановлено {restored_count} активных сессий")
        
        # 👉 Инъекция сервиса в модуль handlers.focus
        from handlers import focus as focus_handlers
        focus_handlers.focus_service = focus_service
        logger.info("FocusService инъецирован в handlers.focus")

    
        
    except Exception as e:
        logger.error(f"Ошибка инициализации Focus модуля: {e}", exc_info=True)
        focus_service = None
    
    notify = make_notifier(bot)
    if pomodoro_service:
        logger.info("Running Pomodoro recovery pass")
        await recovery_pass(service=pomodoro_service, notify=notify)
        shutdown_event = asyncio.Event()
        scheduler_task = asyncio.create_task(
            start_scheduler(
                service=pomodoro_service,
                notify=notify,
                interval_sec=30,
                shutdown_event=shutdown_event,
            )
        )
    else:
        logger.error("PomodoroService not initialized; skipping scheduler")
    
    # Обработка сигналов для graceful shutdown
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}, initiating shutdown")
        shutdown_event.set()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # --- ПОДКЛЮЧЕНИЕ РОУТЕРОВ ---
    dp.include_router(start.router)
    dp.include_router(menu.router)
    dp.include_router(trackers.router)
    dp.include_router(focus.router)
    dp.include_router(checklist.router)
    dp.include_router(profile.router)
    dp.include_router(assistant.router)
    dp.include_router(settings.router)    
    dp.include_router(assistant_onboarding.router)
    dp.include_router(assistant_plan.router)
    
    # Удаляем вебхуки (если были установлены)
    await bot.delete_webhook(drop_pending_updates=True)
    
    logger.info("Бот запущен и готов к работе!")
    
    try:
        # Запуск polling или webhook в зависимости от ENV
        if config.env == "dev":
            logger.info("Starting in polling mode (dev)")
            await dp.start_polling(bot)
        else:
            logger.info("Starting in webhook mode (prod)")
            # webhook setup будет здесь
            pass
    finally:
        # Graceful shutdown
        logger.info("Shutting down...")
        shutdown_event.set()
        
        if scheduler_task and not scheduler_task.done():
            await scheduler_task
        
        await bot.session.close()
        logger.info("Bot stopped")


if __name__ == "__main__":
    # Запускаем бота
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Бот остановлен пользователем")
    except Exception as e:
        logging.error(f"Неожиданная ошибка: {e}", exc_info=True)