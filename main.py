"""
Главный файл для запуска телеграм-бота
"""
import asyncio
import logging
import sys
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


async def main():
    """
    Основная функция для запуска бота
    """
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
        # Запускаем long polling
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Критическая ошибка в работе бота: {e}", exc_info=True)
    finally:
        # Останавливаем планировщик
        try:
            await focus_scheduler.stop()
            logger.info("Focus планировщик остановлен")
        except Exception as e:
            logger.error(f"Ошибка при остановке планировщика: {e}")
        
        # Корректно закрываем соединение
        await bot.session.close()
        logger.info("Бот остановлен")


if __name__ == "__main__":
    # Запускаем бота
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Бот остановлен пользователем")
    except Exception as e:
        logging.error(f"Неожиданная ошибка: {e}", exc_info=True)