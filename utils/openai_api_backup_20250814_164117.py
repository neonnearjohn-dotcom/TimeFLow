"""
Модуль для работы с OpenAI API
"""
import os
from typing import Optional, Dict, List, Tuple
import logging
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class OpenAIAssistant:
    """Класс для работы с OpenAI API"""
    
    def __init__(self):
        """Инициализация клиента OpenAI"""
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
        self.client = None
        self.is_configured = False
        
        # Системный промпт
        self.system_prompt = """Ты - дружелюбный и профессиональный ассистент по продуктивности в Telegram боте TimeFlow.
        
Твои задачи:
- Помогать с планированием дня и задач
- Давать советы по формированию привычек
- Мотивировать и поддерживать пользователей
- Помогать анализировать проблемы и находить решения
- Отвечать на вопросы о продуктивности и саморазвитии

Стиль общения:
- Дружелюбный и поддерживающий
- Конкретный и практичный
- Используй эмодзи для наглядности
- Давай четкие шаги и рекомендации
- Отвечай на русском языке

Помни: ты часть бота TimeFlow, который помогает отслеживать привычки, управлять задачами и проводить фокус-сессии."""
        
        if self.api_key:
            try:
                self.client = AsyncOpenAI(api_key=self.api_key)
                self.is_configured = True
                logger.info(f"OpenAI клиент инициализирован. Модель: {self.model}")
            except Exception as e:
                logger.error(f"Ошибка инициализации OpenAI клиента: {e}")
                self.is_configured = False
        else:
            logger.warning("OpenAI API ключ не найден в переменных окружения")
            self.is_configured = False
    
    def has_api_key(self) -> bool:
        """Проверяет наличие API ключа"""
        return self.is_configured
    
    def is_available(self) -> bool:
        """Проверяет доступность API"""
        return self.is_configured and self.client is not None
    
    async def get_chat_response(
        self, 
        user_message: str, 
        context: Optional[List[Dict]] = None,
        temperature: float = 0.7,
        max_tokens: int = 500
    ) -> Tuple[Optional[str], int]:
        """
        Получает ответ от ChatGPT
        
        Args:
            user_message: Сообщение пользователя
            context: Контекст разговора (список сообщений)
            temperature: Креативность ответа (0-1)
            max_tokens: Максимальное количество токенов в ответе
            
        Returns:
            Кортеж (ответ, количество использованных токенов)
        """
        if not self.is_configured or not self.client:
            logger.error("OpenAI клиент не настроен")
            return None, 0
        
        try:
            # Формируем сообщения
            messages = [
                {"role": "system", "content": self.system_prompt}
            ]
            
            # Добавляем контекст если есть
            if context:
                # Если context - это список словарей с историей
                if isinstance(context, list):
                    for msg in context[-10:]:  # Берем последние 10 сообщений
                        if isinstance(msg, dict) and 'role' in msg and 'content' in msg:
                            messages.append({
                                "role": msg['role'],
                                "content": msg['content']
                            })
                # Если context - это строка (старый формат)
                elif isinstance(context, str):
                    for line in context.split('\n'):
                        if ': ' in line:
                            role, content = line.split(': ', 1)
                            if role.lower() in ['user', 'assistant']:
                                messages.append({
                                    "role": role.lower(),
                                    "content": content
                                })
            
            # Добавляем текущее сообщение
            messages.append({"role": "user", "content": user_message})
            
            # Делаем запрос к API
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=1,
                frequency_penalty=0.3,
                presence_penalty=0.3
            )
            
            # Извлекаем ответ
            answer = response.choices[0].message.content
            tokens_used = response.usage.total_tokens
            
            logger.info(f"OpenAI ответ получен. Токенов использовано: {tokens_used}")
            return answer, tokens_used
            
        except Exception as e:
            logger.error(f"Ошибка при запросе к OpenAI API: {e}")
            return None, 0
    
    async def get_scenario_response(
        self,
        scenario: str,
        context: Optional[str] = None,
        user_data: Optional[Dict] = None
    ) -> Tuple[Optional[str], int]:
        """
        Получает ответ для конкретного сценария
        
        Args:
            scenario: Тип сценария
            context: Дополнительный контекст
            user_data: Данные о пользователе
            
        Returns:
            Кортеж (ответ, количество токенов)
        """
        # Промпты для разных сценариев
        scenario_prompts = {
            'plan': """Помоги составить эффективный план на день.
            Учитывай:
            - Приоритеты задач
            - Время на отдых
            - Энергетические пики
            - Реалистичные временные рамки
            
            Структурируй ответ по блокам времени.""",
            
            'motivation': """Дай мотивирующий совет на сегодня.
            Включи:
            - Вдохновляющую мысль
            - Конкретное действие
            - Напоминание о прогрессе
            
            Будь позитивным но реалистичным.""",
            
            'failure': """Помоги проанализировать неудачу и извлечь уроки.
            Фокусируйся на:
            - Объективном анализе без самокритики
            - Конкретных уроках
            - Плане действий на будущее
            - Поддержке и мотивации""",
            
            'habits': """Дай совет по работе с привычками.
            Рассмотри:
            - Как начать новую привычку
            - Как не сорваться
            - Систему вознаграждений
            - Отслеживание прогресса"""
        }
        
        # Получаем промпт для сценария
        scenario_prompt = scenario_prompts.get(scenario, "Помоги пользователю с его запросом.")
        
        # Формируем сообщение
        message = f"{scenario_prompt}\n\nКонтекст: {context if context else 'Не указан'}"
        
        if user_data:
            message += f"\n\nДанные о пользователе: {user_data}"
        
        return await self.get_chat_response(message, temperature=0.8)
    
    async def send_message(
        self,
        message: str,
        context: Optional[List[Dict]] = None,
        scenario: Optional[str] = None,
        max_tokens: int = 500
    ) -> Dict[str, any]:
        """
        Универсальный метод для отправки сообщений
        
        Args:
            message: Сообщение пользователя
            context: Контекст/история (список сообщений)
            scenario: Сценарий (если задан)
            max_tokens: Максимум токенов
            
        Returns:
            Словарь с результатом
        """
        if not self.is_configured:
            return {
                'success': False,
                'response': 'OpenAI API не настроен. Добавьте OPENAI_API_KEY в файл .env',
                'error': 'API_NOT_CONFIGURED',
                'is_demo': False
            }
        
        try:
            if scenario:
                # Используем сценарий
                response_text, tokens = await self.get_scenario_response(
                    scenario=scenario,
                    context=message
                )
            else:
                # Обычный чат
                response_text, tokens = await self.get_chat_response(
                    user_message=message,
                    context=context,
                    max_tokens=max_tokens
                )
            
            if response_text:
                return {
                    'success': True,
                    'response': response_text,
                    'content': response_text,  # для совместимости
                    'tokens_used': tokens,
                    'is_demo': False
                }
            else:
                return {
                    'success': False,
                    'response': 'Не удалось получить ответ от AI. Попробуйте позже.',
                    'error': 'NO_RESPONSE',
                    'is_demo': False
                }
                
        except Exception as e:
            logger.error(f"Ошибка в send_message: {e}")
            return {
                'success': False,
                'response': f'Произошла ошибка: {str(e)}',
                'error': str(e),
                'is_demo': False
            }