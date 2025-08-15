"""
Исправление работы OpenAI API через прокси для России
"""
import os

print("=== НАСТРОЙКА OPENAI С ПРОКСИ ===\n")

# 1. Создаем исправленный utils/openai_api.py
openai_api_content = '''"""
Модуль для работы с OpenAI API (с поддержкой прокси для России)
"""
import os
import logging
from typing import Dict, List, Optional
import httpx
from dotenv import load_dotenv

# Проверяем наличие библиотеки openai
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("⚠️ Библиотека openai не установлена. Установите: pip install openai")

load_dotenv()
logger = logging.getLogger(__name__)


class OpenAIAssistant:
    """Класс для работы с OpenAI GPT-4o-mini через прокси"""
    
    def __init__(self):
        """Инициализация клиента OpenAI"""
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.proxy_url = os.getenv('PROXY_URL')  # Например: http://proxy.example.com:8080
        self.model = "gpt-4o-mini"
        self.client = None
        self.is_configured = False
        
        if not OPENAI_AVAILABLE:
            logger.warning("OpenAI library not installed")
            return
            
        if self.api_key and self.api_key != "ваш_ключ_api_от_openai":
            try:
                # Создаем клиента с кастомным HTTP клиентом для прокси
                if self.proxy_url:
                    # Используем httpx с прокси
                    http_client = httpx.AsyncClient(
                        proxies=self.proxy_url,
                        timeout=30.0
                    )
                    self.client = openai.AsyncOpenAI(
                        api_key=self.api_key,
                        http_client=http_client
                    )
                    logger.info(f"OpenAI client initialized with proxy: {self.proxy_url}")
                else:
                    # Без прокси (для тех, кто не в России)
                    self.client = openai.AsyncOpenAI(api_key=self.api_key)
                    logger.info("OpenAI client initialized without proxy")
                    
                self.is_configured = True
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
                self.is_configured = False
        else:
            logger.warning("OpenAI API key not found in .env file")
    
    def get_system_prompt(self) -> str:
        """Базовый системный промпт для ассистента"""
        return """Ты - дружелюбный ИИ-ассистент в телеграм-боте для управления временем и привычками.
        Твоя задача - помогать пользователям с планированием, мотивацией и развитием полезных привычек.
        
        Правила общения:
        1. Отвечай на русском языке
        2. Используй дружелюбный и поддерживающий тон
        3. Добавляй эмодзи для выразительности
        4. Давай конкретные и практичные советы
        5. Будь кратким, но информативным (не более 200 слов на ответ)
        6. Поддерживай и мотивируй пользователя
        """
    
    def get_scenario_prompt(self, scenario: str) -> str:
        """Получить промпт для конкретного сценария"""
        prompts = {
            'plan_day': """Помоги пользователю составить эффективный план на день.
                Задай уточняющие вопросы о его задачах и приоритетах.
                Предложи структурированный план с временными блоками.
                Используй матрицу Эйзенхауэра для приоритизации.""",
            
            'motivation': """Создай короткое мотивирующее сообщение.
                Напомни пользователю о его силе и возможностях.
                Используй позитивные утверждения и вдохновляющие метафоры.
                Завершай призывом к действию.""",
            
            'analyze_failure': """Помоги пользователю проанализировать неудачу или срыв.
                Будь эмпатичным и поддерживающим.
                Помоги найти причины и извлечь уроки.
                Предложи конкретные шаги для восстановления.""",
            
            'habit_advice': """Дай совет по формированию или улучшению привычек.
                Используй научно обоснованные методики.
                Предложи конкретные техники и стратегии.
                Помоги сделать привычку проще и приятнее."""
        }
        return prompts.get(scenario, "")
    
    async def send_message(
        self,
        message: str,
        context: Optional[List[Dict]] = None,
        scenario: Optional[str] = None,
        max_tokens: int = 500
    ) -> Dict:
        """
        Отправить сообщение к OpenAI API
        """
        
        # Если API не настроен, возвращаем демо-ответ
        if not self.is_configured or not OPENAI_AVAILABLE:
            return {
                'success': False,
                'response': self._get_demo_response(scenario or 'default'),
                'error': 'API не настроен или недоступен из вашего региона',
                'is_demo': True
            }
        
        try:
            # Формируем сообщения для API
            messages = [
                {"role": "system", "content": self.get_system_prompt()}
            ]
            
            # Добавляем промпт сценария, если указан
            if scenario:
                scenario_prompt = self.get_scenario_prompt(scenario)
                if scenario_prompt:
                    messages.append({"role": "system", "content": scenario_prompt})
            
            # Добавляем контекст предыдущих сообщений
            if context:
                messages.extend(context[-10:])  # Берем последние 10 сообщений
            
            # Добавляем текущее сообщение пользователя
            messages.append({"role": "user", "content": message})
            
            # Отправляем запрос к OpenAI
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.7,
                top_p=0.9,
                frequency_penalty=0.3,
                presence_penalty=0.3
            )
            
            # Извлекаем ответ
            assistant_response = response.choices[0].message.content
            
            return {
                'success': True,
                'response': assistant_response,
                'usage': {
                    'prompt_tokens': response.usage.prompt_tokens,
                    'completion_tokens': response.usage.completion_tokens,
                    'total_tokens': response.usage.total_tokens
                }
            }
            
        except Exception as e:
            logger.error(f"Error in OpenAI API: {e}", exc_info=True)
            
            # Возвращаем демо-ответ при ошибке
            return {
                'success': False,
                'response': self._get_demo_response(scenario or 'default'),
                'error': str(e),
                'is_demo': True
            }
    
    def _get_demo_response(self, scenario: str) -> str:
        """Получить демо-ответ для тестирования без API ключа"""
        demo_responses = {
            'plan_day': """📅 **План на день (демо)**
                
Утро (9:00-12:00):
• ✅ Самая важная задача дня
• ☕ Перерыв 15 мин
• 📧 Разбор почты

День (12:00-17:00):
• 🍽 Обед
• 🎯 Фокус-сессии по 25 мин
• 📞 Звонки и встречи

Вечер (17:00-21:00):
• 🏃 Физическая активность
• 📚 Время для обучения
• 🧘 Отдых и восстановление

💡 Совет: Начните с самого сложного!""",
            
            'motivation': """💪 **Мотивация дня (демо)**
                
Каждый новый день - это новая возможность стать лучшей версией себя! 

🌟 Помни: ты уже проделал большой путь, и каждый маленький шаг приближает тебя к цели.

Сегодня ты можешь:
• Сделать что-то, что откладывал
• Улучшить одну привычку
• Помочь кому-то

Вперёд к новым достижениям! 🚀""",
            
            'default': """🤖 **Ассистент работает в демо-режиме**
                
Для полноценной работы нужно:
1. Получить API ключ OpenAI
2. Настроить прокси (для России)
3. Добавить в .env файл:
   - OPENAI_API_KEY=ваш_ключ
   - PROXY_URL=адрес_прокси

А пока используйте другие функции бота! 😊"""
        }
        
        return demo_responses.get(scenario, demo_responses['default'])


# Глобальный экземпляр ассистента
try:
    assistant = OpenAIAssistant()
except Exception as e:
    logger.error(f"Could not initialize OpenAI assistant: {e}")
    # Создаем заглушку
    class DummyAssistant:
        def __init__(self):
            self.is_configured = False
        
        async def send_message(self, *args, **kwargs):
            return {
                'success': False,
                'response': "🤖 Ассистент временно недоступен. Попробуйте позже.",
                'is_demo': True
            }
    
    assistant = DummyAssistant()
'''

# Сохраняем файл
os.makedirs("utils", exist_ok=True)
with open("utils/openai_api.py", "w", encoding="utf-8") as f:
    f.write(openai_api_content)

print("✅ Создан utils/openai_api.py с поддержкой прокси")

# 2. Обновляем .env файл
print("\n📝 Добавьте в файл .env:")
print("PROXY_URL=http://your-proxy-server:port")
print("# Или для SOCKS5:")
print("PROXY_URL=socks5://your-proxy-server:port")

print("\n💡 Рекомендуемые прокси-сервисы для OpenAI:")
print("1. Bright Data (brightdata.com)")
print("2. SmartProxy (smartproxy.com)")
print("3. Webshare (webshare.io)")
print("4. Ваш собственный VPS с прокси")

print("\n✅ Готово!")