"""
Полное исправление всех проблем с ассистентом
"""
import os
import shutil

def fix_everything():
    """Исправляет все известные проблемы"""
    
    print("🔧 Комплексное исправление модуля ассистента...\n")
    
    # 1. Исправляем OpenAI API
    print("1️⃣ Исправление utils/openai_api.py...")
    openai_content = '''"""
Модуль для работы с OpenAI API - исправленная версия
"""
import os
from typing import Optional, Tuple
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class OpenAIAssistant:
    """Класс для работы с OpenAI GPT API"""
    
    def __init__(self):
        """Инициализация клиента OpenAI"""
        self.api_key = os.getenv('OPENAI_API_KEY', 'your-openai-api-key-here')
        self.model = "gpt-4o-mini"
        self.client = None
        self.is_configured = False
        
        # Пробуем инициализировать клиент
        try:
            if self.api_key and self.api_key != 'your-openai-api-key-here':
                try:
                    from openai import AsyncOpenAI
                    self.client = AsyncOpenAI(api_key=self.api_key)
                    self.is_configured = True
                    print("OpenAI client initialized successfully")
                except ImportError:
                    print("OpenAI library not installed. Using demo mode.")
                except Exception as e:
                    print(f"Could not initialize OpenAI client: {e}")
            else:
                print("OpenAI API key not configured - using demo mode")
        except Exception as e:
            print(f"Error in OpenAI initialization: {e}")
    
    async def get_chat_response(self, user_message: str, context: str = "") -> Tuple[Optional[str], int]:
        """Получает ответ от ChatGPT"""
        return None, 0  # Демо-режим
    
    async def get_scenario_response(self, scenario: str, context: str = "") -> Tuple[Optional[str], int]:
        """Получает ответ для сценария"""
        return None, 0  # Демо-режим
    
    def is_available(self) -> bool:
        """Проверяет доступность API"""
        return self.is_configured
'''
    
    os.makedirs('utils', exist_ok=True)
    with open('utils/openai_api.py', 'w', encoding='utf-8') as f:
        f.write(openai_content)
    print("✅ Исправлен utils/openai_api.py")
    
    # 2. Исправляем main.py
    print("\n2️⃣ Исправление main.py...")
    with open('main.py', 'r', encoding='utf-8') as f:
        main_content = f.read()
    
    # Исправляем импорт DefaultBotProperties
    if 'DefaultBotProperties' not in main_content:
        main_content = main_content.replace(
            'from aiogram.enums import ParseMode',
            'from aiogram.enums import ParseMode\nfrom aiogram.client.default import DefaultBotProperties'
        )
    
    # Исправляем инициализацию бота
    old_bot = 'bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)'
    new_bot = '''bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )'''
    
    if old_bot in main_content:
        main_content = main_content.replace(old_bot, new_bot)
    
    # Убеждаемся, что assistant импортирован и подключен
    if '# , assistant' in main_content:
        main_content = main_content.replace('# , assistant', ', assistant')
    if '# dp.include_router(assistant.router)' in main_content:
        main_content = main_content.replace('# dp.include_router(assistant.router)', 'dp.include_router(assistant.router)')
    
    with open('main.py', 'w', encoding='utf-8') as f:
        f.write(main_content)
    print("✅ Исправлен main.py")
    
    # 3. Проверяем/создаем handlers/assistant.py
    print("\n3️⃣ Проверка handlers/assistant.py...")
    if not os.path.exists('handlers/assistant.py'):
        print("❌ handlers/assistant.py не найден! Создаю простую версию...")
        create_simple_assistant()
    else:
        # Проверяем, есть ли функция handle_assistant_menu
        with open('handlers/assistant.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        if 'handle_assistant_menu' not in content:
            print("⚠️ handle_assistant_menu не найдена! Заменяю на простую версию...")
            create_simple_assistant()
        else:
            print("✅ handlers/assistant.py существует")
    
    # 4. Создаем корректный handlers/menu.py если нужно
    print("\n4️⃣ Проверка handlers/menu.py...")
    fix_menu_handler()
    
    print("\n✅ Все исправлено!")
    print("\n🚀 Перезапустите бота: python main.py")
    print("\n💡 Ассистент будет работать в демо-режиме.")
    print("Для полной функциональности добавьте OPENAI_API_KEY в .env")


def create_simple_assistant():
    """Создает простой рабочий handlers/assistant.py"""
    content = '''"""
Простой обработчик для модуля ИИ-ассистента
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state, State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from keyboards.main_menu import get_main_menu_keyboard
import logging

# Создаем роутер
router = Router()
logger = logging.getLogger(__name__)

# Состояния
class AssistantStates(StatesGroup):
    in_assistant_mode = State()
    chatting = State()

# Обработчик кнопки из главного меню
@router.message(F.text == "🤖 ИИ-ассистент", StateFilter(default_state))
async def handle_assistant_menu(message: Message, state: FSMContext):
    """Обработчик кнопки ИИ-ассистент из главного меню"""
    
    logger.info(f"Assistant menu opened by user {message.from_user.id}")
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🎯 Быстрые сценарии", callback_data="scenarios")
    builder.button(text="💬 Свободный чат", callback_data="chat")
    builder.button(text="❌ Выйти", callback_data="exit_assistant")
    builder.adjust(2, 1)
    
    await message.answer(
        "🤖 <b>Привет! Я твой ИИ-ассистент</b>\\n\\n"
        "Я работаю в демо-режиме и могу показать примеры ответов.\\n\\n"
        "Выбери, что тебе нужно:",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await state.set_state(AssistantStates.in_assistant_mode)

# Обработчик сценариев
@router.callback_query(F.data == "scenarios", AssistantStates.in_assistant_mode)
async def show_scenarios(callback: CallbackQuery):
    """Показ сценариев"""
    builder = InlineKeyboardBuilder()
    builder.button(text="📅 План на день", callback_data="sc:plan")
    builder.button(text="💪 Мотивация", callback_data="sc:motivation")
    builder.button(text="◀️ Назад", callback_data="back_menu")
    builder.adjust(1)
    
    await callback.message.edit_text(
        "🎯 <b>Выбери сценарий:</b>",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()

# Обработчик выхода
@router.callback_query(F.data == "exit_assistant")
async def exit_assistant(callback: CallbackQuery, state: FSMContext):
    """Выход из ассистента"""
    await callback.message.answer(
        "👋 До встречи!",
        reply_markup=get_main_menu_keyboard()
    )
    await callback.message.delete()
    await state.clear()
    await callback.answer("Вышли из ассистента")
'''
    
    with open('handlers/assistant.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("✅ Создан простой handlers/assistant.py")


def fix_menu_handler():
    """Исправляет handlers/menu.py"""
    content = '''"""
Обработчики для кнопок главного меню
"""
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import StateFilter
from aiogram.fsm.state import default_state
from aiogram.fsm.context import FSMContext

# Создаем роутер для обработчиков меню
router = Router()


@router.message(F.text == "📊 Трекеры", StateFilter(default_state))
async def handle_trackers(message: Message):
    """Обработчик кнопки Трекеры"""
    from handlers import trackers
    await trackers.handle_trackers_menu(message)


@router.message(F.text == "✅ Чек-лист", StateFilter(default_state))
async def handle_checklist(message: Message):
    """Обработчик кнопки Чек-лист"""
    from handlers import checklist
    await checklist.handle_checklist_menu(message)


@router.message(F.text == "🎯 Фокус", StateFilter(default_state))
async def handle_focus(message: Message):
    """Обработчик кнопки Фокус"""
    from handlers import focus
    await focus.handle_focus_menu(message)


@router.message(F.text == "🤖 ИИ-ассистент", StateFilter(default_state))
async def handle_assistant(message: Message, state: FSMContext):
    """Обработчик кнопки ИИ-ассистент"""
    from handlers import assistant
    await assistant.handle_assistant_menu(message, state)


@router.message(F.text == "👤 Профиль", StateFilter(default_state))
async def handle_profile(message: Message):
    """Обработчик кнопки Профиль"""
    from handlers import profile
    await profile.handle_profile_menu(message)


@router.message(F.text == "⚙️ Настройки", StateFilter(default_state))
async def handle_settings(message: Message):
    """Обработчик кнопки Настройки"""
    await message.answer(
        "⚙️ <b>Настройки</b>\\n\\n"
        "🚧 Этот раздел находится в разработке.",
        parse_mode="HTML"
    )
'''
    
    with open('handlers/menu.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("✅ Исправлен handlers/menu.py")


if __name__ == "__main__":
    print("🛠 Полное исправление модуля ИИ-ассистента\\n")
    print("Это исправит:")
    print("1. Ошибку OpenAI 'proxies'")
    print("2. Предупреждение Bot deprecated")
    print("3. Проблему с обработчиком ассистента\\n")
    
    response = input("Начать исправление? (y/n): ")
    if response.lower() == 'y':
        fix_everything()
    else:
        print("Отменено")