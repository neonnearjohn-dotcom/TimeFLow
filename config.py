"""
Конфигурация бота
"""
import os
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

# Токен бота от @BotFather
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в переменных окружения!")

# Путь к файлу с ключами Firebase (для Firestore)
GOOGLE_APPLICATION_CREDENTIALS = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
if not GOOGLE_APPLICATION_CREDENTIALS:
    raise ValueError("GOOGLE_APPLICATION_CREDENTIALS не найден в переменных окружения!")

# ID проекта Firestore (можно указать явно или получить из credentials)
FIRESTORE_PROJECT_ID = os.getenv('FIRESTORE_PROJECT_ID', None)