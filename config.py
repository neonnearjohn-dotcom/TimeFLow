"""Конфигурация бота"""
import os
from utils.env_loader import load_env

load_env()

BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в переменных окружения!")

GOOGLE_APPLICATION_CREDENTIALS = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
if not GOOGLE_APPLICATION_CREDENTIALS:
    raise ValueError("GOOGLE_APPLICATION_CREDENTIALS не найден в переменных окружения!")

FIREBASE_PROJECT_ID = os.getenv('FIREBASE_PROJECT_ID')

