"""
Быстрое исправление модуля ассистента - запуск за 10 секунд
"""
import os

# Исправляем states/assistant.py
states_content = '''"""
FSM состояния для модуля ИИ-ассистента
"""
from aiogram.fsm.state import State, StatesGroup


class AssistantStates(StatesGroup):
    """Состояния для работы с ИИ-ассистентом"""
    
    # Пользователь в режиме ассистента
    in_assistant_mode = State()
    
    # Пользователь в режиме свободного чата
    chatting = State()
    
    # Ожидание ответа от ИИ (опционально)
    waiting_response = State()
'''

# Исправляем utils/openai_api.py
openai_content = '''"""
Модуль для работы с OpenAI API
"""
import os
from typing import Optional, Tuple
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# Проверяем версию OpenAI и используем правильный импорт
try:
    from openai import AsyncOpenAI
    OPENAI_NEW_VERSION = True
except ImportError:
    import openai
    OPENAI_NEW_VERSION = False


class OpenAIAssistant:
    """Класс для работы с OpenAI GPT API"""
    
    def __init__(self):
        """Инициализация клиента OpenAI"""
        self.api_key = os.getenv('OPENAI_API_KEY', 'your-openai-api-key-here')
        self.model = "gpt-4o-mini"
        
        try:
            if self.api_key and self.api_key != 'your-openai-api-key-here':
                if OPENAI_NEW_VERSION:
                    # Новая версия - БЕЗ proxies
                    self.client = AsyncOpenAI(api_key=self.api_key)
                else:
                    # Старая версия
                    openai.api_key = self.api_key
                    self.client = None
                self.is_configured = True
                print("OpenAI client initialized successfully")
            else:
                self.client = None
                self.is_configured = False
                print("OpenAI API key not configured - using demo mode")
        except Exception as e:
            print(f"Failed to initialize OpenAI client: {e}")
            self.client = None
            self.is_configured = False
    
    async def get_chat_response(self, user_message: str, context: str = "") -> Tuple[Optional[str], int]:
        """Получает ответ от ChatGPT"""
        if not self.is_configured:
            return None, 0
        
        try:
            messages = [
                {"role": "system", "content": "Ты дружелюбный помощник по продуктивности. Отвечай кратко, используй эмодзи."},
                {"role": "user", "content": user_message}
            ]
            
            if OPENAI_NEW_VERSION and self.client:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=500
                )
                return response.choices[0].message.content, response.usage.total_tokens
            else:
                # Для старой версии используем синхронный вызов
                response = openai.ChatCompletion.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=500
                )
                return response.choices[0].message.content, response.usage.total_tokens
                
        except Exception as e:
            logger.error(f"Error: {e}")
            return None, 0
    
    async def get_scenario_response(self, scenario: str, context: str = "") -> Tuple[Optional[str], int]:
        """Получает ответ для сценария"""
        prompts = {
            'plan': "Помоги составить план дня по матрице Эйзенхауэра.",
            'motivation': "Создай мотивирующее сообщение.",
            'failure': "Помоги разобрать неудачу и найти решение.",
            'habits': "Дай советы по формированию привычек."
        }
        
        prompt = prompts.get(scenario, "Помоги пользователю.")
        return await self.get_chat_response(prompt, context)
    
    def is_available(self) -> bool:
        """Проверяет доступность API"""
        return self.is_configured
'''

# Создаем/обновляем файлы
os.makedirs('states', exist_ok=True)
os.makedirs('utils', exist_ok=True)

with open('states/assistant.py', 'w', encoding='utf-8') as f:
    f.write(states_content)
print("✅ Исправлен states/assistant.py")

with open('utils/openai_api.py', 'w', encoding='utf-8') as f:
    f.write(openai_content)
print("✅ Исправлен utils/openai_api.py")

print("\n🚀 Готово! Запустите бота: python main.py")