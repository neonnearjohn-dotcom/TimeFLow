"""
Обработчики для кнопок главного меню
"""
import stat
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import StateFilter
from aiogram.fsm.state import default_state
from aiogram.fsm.context import FSMContext

from handlers.assistant import ASSISTANT_MESSAGES
from keyboards.assistant import get_assistant_menu_keyboard

# Создаем роутер для обработчиков меню
router = Router()


@router.message(F.text == "Трекеры", StateFilter(default_state))
async def handle_trackers(message: Message):
    """Обработчик кнопки Трекеры"""
    from handlers import trackers
    await trackers.handle_tracker_menu(message)


@router.message(F.text == "Чек-лист", StateFilter(default_state))
async def handle_checklist(message: Message):
    """Обработчик кнопки Чек-лист"""
    from handlers import checklist
    await checklist.handle_checklist_menu(message)


@router.message(F.text == "Фокус", StateFilter(default_state))
async def handle_focus(message: Message):
    """Обработчик кнопки Фокус"""
    from handlers import focus
    await focus.handle_focus_menu(message)


@router.message(F.text == "🤖 ИИ-ассистент", StateFilter(default_state))
async def handle_assistant_menu(message: Message):
    """Обработчик кнопки ИИ-ассистент"""
    await message.answer(
        ASSISTANT_MESSAGES['welcome'],
        reply_markup=get_assistant_menu_keyboard()  # Без параметра, по умолчанию has_plan=False
    )
    from handlers import assistant
    await assistant.handle_assistant_menu(message, stat)


@router.message(F.text == "Профиль", StateFilter(default_state))
async def handle_profile(message: Message):
    """Обработчик кнопки Профиль"""
    from handlers import profile
    await profile.handle_profile_menu(message)


@router.message(F.text == "Настройки", StateFilter(default_state))
async def handle_settings(message: Message):
    """Обработчик кнопки Настройки"""
    from handlers import settings
    await settings.show_settings_menu(message)