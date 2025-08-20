"""
Тестирование профиля и геймификации
"""
import asyncio
import logging
from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.types import KeyboardButton

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Импортируем конфигурацию
from config import BOT_TOKEN

# Создаем роутер
router = Router()

def get_test_keyboard():
    """Создает тестовую клавиатуру"""
    builder = ReplyKeyboardBuilder()
    
    buttons = [
        KeyboardButton(text="👤 Профиль"),
        KeyboardButton(text="🔍 Проверить БД"),
        KeyboardButton(text="🏆 Тест достижения")
    ]
    
    for button in buttons:
        builder.add(button)
    
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

@router.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    await message.answer(
        f"👋 Привет! Это тестовый режим.\n"
        f"Твой ID: {message.from_user.id}\n\n"
        "Выбери действие:",
        reply_markup=get_test_keyboard()
    )

@router.message(F.text == "🔍 Проверить БД")
async def check_db(message: Message):
    """Проверяет подключение к БД"""
    try:
        from database.firestore_db import FirestoreDB
        db = FirestoreDB()
        
        # Проверяем существование пользователя
        user_exists = await db.user_exists(message.from_user.id)
        
        await message.answer(
            f"✅ Подключение к БД работает!\n"
            f"Пользователь существует: {'Да' if user_exists else 'Нет'}"
        )
    except Exception as e:
        await message.answer(
            f"❌ Ошибка подключения к БД:\n{str(e)}"
        )

@router.message(F.text == "🏆 Тест достижения")
async def test_achievement(message: Message):
    """Тестирует получение достижения"""
    try:
        from database.firestore_db import FirestoreDB
        from database.gamification_db import GamificationDB
        
        db = FirestoreDB()
        gamification_db = GamificationDB(db.db)
        
        # Разблокируем первое достижение
        success = await gamification_db.unlock_achievement(
            message.from_user.id,
            'first_habit'
        )

        if success:
            await message.answer(
                "🎉 Получено достижение 'Первый шаг'!"
            )
        else:
            await message.answer("❌ Не удалось получить достижение")
            
    except Exception as e:
        await message.answer(
            f"❌ Ошибка при получении достижения:\n{str(e)}"
        )

@router.message(F.text == "👤 Профиль")
async def show_profile(message: Message):
    """Показывает профиль с обработкой ошибок"""
    try:
        # Сначала проверим подключение к БД
        from database.firestore_db import FirestoreDB
        from database.gamification_db import GamificationDB
        
        db = FirestoreDB()
        user_exists = await db.user_exists(message.from_user.id)
        
        if not user_exists:
            # Создаем пользователя
            user_data = {
                'username': message.from_user.username,
                'full_name': message.from_user.full_name,
                'achievements_count': 0
            }
            await db.create_user(message.from_user.id, user_data)
            await message.answer("✅ Создан новый профиль!")
        
        # Теперь пробуем показать профиль
        from handlers.profile import show_user_profile
        await show_user_profile(message.from_user.id, message.answer)
        
    except Exception as e:
        await message.answer(
            f"❌ Ошибка при показе профиля:\n"
            f"Тип: {type(e).__name__}\n"
            f"Сообщение: {str(e)}"
        )

async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    
    print("🧪 Тестовый бот запущен!")
    print("Используйте команды для проверки функций")
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())