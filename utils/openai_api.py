"""Модуль для работы с OpenAI API"""

import os
from typing import Optional, Dict, List, Tuple, Any
import logging
import json
import re
import httpx
from utils.env_loader import load_env

load_env()

logger = logging.getLogger(__name__)

# Проверяем наличие OpenAI
try:
    from openai import AsyncOpenAI

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI модуль не установлен. Бот будет работать в демо-режиме.")


class OpenAIAssistant:
    """Класс для работы с OpenAI API"""

    def __init__(self):
        """Инициализация клиента OpenAI"""
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.client = None
        self.is_configured = False
        self._client_closed = False  # Флаг для отслеживания закрытия клиента
        self.proxy = os.getenv("OPENAI_PROXY")

        # Системный промпт
        self.system_prompt = """Ты — встроенный ИИ-ассистент проекта TimeFlow Bot.
Твоя задача — помогать пользователю только по темам, связанным с целями и функционалом приложения:

1.продуктивность

2. планирование

3. привычки (полезные/вредные)

4. фокус и концентрация

5. обучение и развитие навыков

6. здоровье и тайм-менеджмент

7. поддержка в рамках этих тем (мотивация, советы, лайфхаки)

📌 Чёткие правила работы:

1. Отвечай только на вопросы в пределах этих тем.

2. Если вопрос не относится к ним — вежливо, но профессионально отказывай, например:

"К сожалению, я не предназначен для подобных запросов. Моя задача — помогать вам в вопросах продуктивности, планирования и достижения целей."

3. Стиль общения по умолчанию — нейтрально-профессиональный: без лишней эмоциональности, но дружелюбно.

4.Пользователь может менять стиль общения (например, чуть более мотивирующий или более сухой деловой), но:

    никакого подчинения, обращения "хозяин", ролевых игр,

    никакой имитации нецензурной или агрессивной речи.

5. Всегда отвечай чётко, структурировано и по делу.

6. При необходимости можешь уточнять контекст вопроса, чтобы дать максимально полезный ответ.

⚠ Запрещено:

1. Обсуждать или давать советы по темам, не связанным с назначением бота.

2. Генерировать развлекательный или кулинарный контент, который не имеет прямого отношения к целям приложения.

3. Вступать в личные или ролевые переписки.

Помни: ты часть бота TimeFlow, который помогает отслеживать привычки, управлять задачами и проводить фокус-сессии."""

        if self.api_key and OPENAI_AVAILABLE:
            try:
                http_client = (
                    httpx.AsyncClient(proxy=self.proxy) if self.proxy else httpx.AsyncClient()
                )
                self.client = AsyncOpenAI(api_key=self.api_key, http_client=http_client)
                self.is_configured = True
                logger.info(f"OpenAI клиент инициализирован. Модель: {self.model}")
            except Exception as e:
                logger.error(f"Ошибка инициализации OpenAI клиента: {e}")
                self.is_configured = False
                self.client = None
        else:
            if not self.api_key:
                logger.warning("OpenAI API ключ не найден в переменных окружения")
            self.is_configured = False

    def has_api_key(self) -> bool:
        """Проверяет наличие API ключа"""
        return bool(self.api_key)

    def is_available(self) -> bool:
        """Проверяет доступность API"""
        return self.is_configured and not self._client_closed

    async def close(self):
        """Корректно закрывает клиент OpenAI"""
        if self.client and not self._client_closed:
            try:
                # Проверяем, есть ли у клиента метод aclose
                if hasattr(self.client, "aclose"):
                    await self.client.aclose()
                self._client_closed = True
                logger.info("OpenAI клиент закрыт")
            except AttributeError:
                # Если нет метода aclose, просто помечаем как закрытый
                self._client_closed = True
            except Exception as e:
                logger.error(f"Ошибка при закрытии OpenAI клиента: {e}")
                self._client_closed = True

    async def get_chat_response(
        self,
        user_message: str,
        context: Optional[List[Dict]] = None,
        temperature: float = 0.7,
        max_tokens: int = 500,
        system_prompt: Optional[str] = None,
    ) -> Tuple[Optional[str], int]:
        """
        Получает ответ от ChatGPT

        Args:
            user_message: Сообщение пользователя
            context: Контекст разговора (список сообщений)
            temperature: Креативность ответа (0-1)
            max_tokens: Максимальное количество токенов в ответе
            system_prompt: Кастомный системный промпт (если нужен)

        Returns:
            Кортеж (ответ, количество использованных токенов)
        """
        if not self.is_configured:
            logger.error("OpenAI не настроен")
            return None, 0

        if self._client_closed:
            logger.error("OpenAI клиент закрыт")
            return None, 0

        try:
            # Формируем сообщения
            messages = [{"role": "system", "content": system_prompt or self.system_prompt}]

            # Добавляем контекст если есть
            if context:
                # Если context - это список словарей с историей
                if isinstance(context, list):
                    for msg in context[-10:]:  # Берем последние 10 сообщений
                        if isinstance(msg, dict) and "role" in msg and "content" in msg:
                            messages.append({"role": msg["role"], "content": msg["content"]})
                # Если context - это строка (старый формат)
                elif isinstance(context, str):
                    for line in context.split("\n"):
                        if ": " in line:
                            role, content = line.split(": ", 1)
                            if role.lower() in ["user", "assistant"]:
                                messages.append({"role": role.lower(), "content": content})

            # Добавляем текущее сообщение
            messages.append({"role": "user", "content": user_message})

            # Делаем запрос к API
            if not self.client:
                logger.error("OpenAI клиент не инициализирован")
                return None, 0

            # Используем новый клиент
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=1,
                frequency_penalty=0.3,
                presence_penalty=0.3,
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
        self, scenario: str, context: Optional[str] = None, user_data: Optional[Dict] = None
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
            "plan": """Помоги составить эффективный план на день.
            Учитывай:
            - Приоритеты задач
            - Время на отдых
            - Энергетические пики
            - Реалистичные временные рамки
            
            Структурируй ответ по блокам времени.""",
            "motivation": """Дай мотивирующий совет на сегодня.
            Включи:
            - Вдохновляющую мысль
            - Конкретное действие
            - Напоминание о прогрессе
            
            Будь позитивным но реалистичным.""",
            "failure": """Помоги проанализировать неудачу и извлечь уроки.
            Фокусируйся на:
            - Объективном анализе без самокритики
            - Конкретных уроках
            - Плане действий на будущее
            - Поддержке и мотивации""",
            "habits": """Дай совет по работе с привычками.
            Рассмотри:
            - Как начать новую привычку
            - Как не сорваться
            - Систему вознаграждений
            - Отслеживание прогресса""",
        }

        # Получаем промпт для сценария
        scenario_prompt = scenario_prompts.get(scenario, "Помоги пользователю с его запросом.")

        # Формируем сообщение
        message = f"{scenario_prompt}\n\nКонтекст: {context if context else 'Не указан'}"

        if user_data:
            message += f"\n\nДанные о пользователе: {user_data}"

        return await self.get_chat_response(message, temperature=0.8)

    async def generate_json_response(
        self,
        prompt: str,
        json_schema: Optional[Dict] = None,
        max_tokens: int = 4000,
        temperature: float = 0.2,
        continue_if_truncated: bool = True,
        system_prompt: Optional[str] = None,
    ) -> Tuple[Optional[Dict], str, int]:
        """
        Генерирует ответ в формате JSON с строгой схемой

        Args:
            prompt: Промпт для генерации
            json_schema: JSON схема (для response_format)
            max_tokens: Максимум токенов
            temperature: Температура генерации (0.2 для детерминированности)
            continue_if_truncated: Дозагружать ли при обрезке
            system_prompt: Кастомный системный промпт (опционально)

        Returns:
            Кортеж (распарсенный JSON, finish_reason, использованные токены)
        """
        if not self.is_configured or self._client_closed:
            logger.error("OpenAI не настроен или клиент закрыт")
            return None, "error", 0

        try:
            # Используем кастомный или дефолтный системный промпт для JSON
            if system_prompt:
                json_system_prompt = system_prompt
            else:
                json_system_prompt = """You are a JSON API that returns only valid JSON without any additional text.
Your response must be a parseable JSON object.
Do not add comments, explanations, markdown formatting, or any text outside the JSON structure.
Return ONLY the JSON object."""

            messages = [
                {"role": "system", "content": json_system_prompt},
                {"role": "user", "content": prompt},
            ]

            # Подготавливаем параметры запроса
            request_params = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "top_p": 1,
            }

            # Пытаемся использовать строгий JSON режим
            response_format_applied = False

            # Вариант 1: JSON Schema (если схема предоставлена)
            if json_schema:
                try:
                    # Пробуем response_format с json_schema
                    request_params["response_format"] = {
                        "type": "json_schema",
                        "json_schema": json_schema,
                    }
                    response_format_applied = True
                    logger.info("Используем response_format с JSON Schema")
                except Exception as e:
                    logger.warning(f"JSON Schema не поддерживается: {e}")

            # Вариант 2: Простой json_object
            if not response_format_applied:
                try:
                    request_params["response_format"] = {"type": "json_object"}
                    response_format_applied = True
                    logger.info("Используем response_format с json_object")
                except Exception as e:
                    logger.warning(f"response_format не поддерживается: {e}")

            # Делаем запрос
            response = await self.client.chat.completions.create(**request_params)

            content = response.choices[0].message.content
            finish_reason = response.choices[0].finish_reason
            tokens_used = response.usage.total_tokens if hasattr(response, "usage") else 0

            logger.info(
                f"Получен ответ от OpenAI: finish_reason={finish_reason}, tokens={tokens_used}, длина={len(content)}"
            )

            # Обработка обрезки ответа
            if finish_reason == "length" and continue_if_truncated:
                logger.warning("Ответ обрезан по длине, пытаемся дозагрузить...")

                # Пытаемся найти последний полный день в JSON
                try:
                    # Находим позицию последнего закрытого объекта дня
                    last_complete_day = content.rfind("},")
                    if last_complete_day > 0:
                        # Обрезаем до последнего полного дня
                        truncated_json = content[: last_complete_day + 1]

                        # Пытаемся распарсить, чтобы понять сколько дней уже есть
                        partial_data = None
                        try:
                            # Временно закрываем JSON для парсинга
                            test_json = (
                                truncated_json + "]}"
                                if '"days"' in truncated_json
                                else truncated_json + "}"
                            )
                            partial_data = json.loads(test_json)
                            existing_days = len(partial_data.get("days", []))
                        except:
                            existing_days = 0

                        # Запрашиваем продолжение
                        continuation_prompt = f"""Continue the JSON plan from day {existing_days + 1}.
Return ONLY the remaining days in this exact format:
{{"day": {existing_days + 1}, "tasks": [{{"time": "HH:MM", "activity": "..."}}]}},
{{"day": {existing_days + 2}, "tasks": [{{"time": "HH:MM", "activity": "..."}}]}}
Do not repeat previous days. Return only JSON, no other text."""

                        continuation_params = {
                            "model": self.model,
                            "messages": [
                                {"role": "system", "content": json_system_prompt},
                                {"role": "user", "content": continuation_prompt},
                            ],
                            "temperature": temperature,
                            "max_tokens": 2000,
                            "top_p": 1,
                        }

                        if response_format_applied:
                            continuation_params["response_format"] = {"type": "json_object"}

                        continuation_response = await self.client.chat.completions.create(
                            **continuation_params
                        )
                        continuation_content = continuation_response.choices[0].message.content
                        tokens_used += (
                            continuation_response.usage.total_tokens
                            if hasattr(continuation_response, "usage")
                            else 0
                        )

                        # Склеиваем JSON
                        if continuation_content:
                            # Извлекаем только массив days из продолжения
                            try:
                                cont_json = json.loads(continuation_content)
                                if isinstance(cont_json, dict) and "days" in cont_json:
                                    # Добавляем новые дни к существующим
                                    if partial_data:
                                        partial_data["days"].extend(cont_json["days"])
                                        return partial_data, "complete", tokens_used
                            except:
                                pass

                            # Пытаемся склеить как строки
                            content = truncated_json + "," + continuation_content.strip()
                            if not content.endswith("]}"):
                                content = content.rstrip("}]") + "]}"

                        logger.info(f"Дозагрузка завершена, общая длина: {len(content)}")

                except Exception as e:
                    logger.error(f"Ошибка при дозагрузке: {e}")

            # Парсим JSON
            if content:
                # Базовая очистка
                content = content.strip()

                # Убираем markdown блоки если есть
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]

                try:
                    result = json.loads(content)
                    return result, finish_reason, tokens_used
                except json.JSONDecodeError as e:
                    logger.error(f"Ошибка парсинга JSON: {e}")
                    logger.debug(f"Проблемный JSON (первые 500 символов): {content[:500]}")
                    # Будет обработано в plan_generator.py
                    return None, finish_reason, tokens_used

            return None, finish_reason, tokens_used

        except Exception as e:
            logger.error(f"Ошибка в generate_json_response: {e}")
            return None, "error", 0

    async def send_message(
        self,
        message: str,
        context: Optional[List[Dict]] = None,
        scenario: Optional[str] = None,
        max_tokens: int = 500,
        system_prompt: Optional[str] = None,
    ) -> Dict[str, any]:
        """
        Универсальный метод для отправки сообщений

        Args:
            message: Сообщение пользователя
            context: Контекст/история (список сообщений)
            scenario: Сценарий (если задан)
            max_tokens: Максимум токенов
            system_prompt: Кастомный системный промпт

        Returns:
            Словарь с результатом
        """
        # Если API не настроен, возвращаем демо-ответы
        if not self.is_configured:
            return self._get_demo_response(scenario)

        try:
            if scenario:
                # Используем сценарий
                response_text, tokens = await self.get_scenario_response(
                    scenario=scenario, context=message
                )
            else:
                # Обычный чат
                response_text, tokens = await self.get_chat_response(
                    user_message=message,
                    context=context,
                    max_tokens=max_tokens,
                    system_prompt=system_prompt,
                )

            if response_text:
                logger.debug(
                    f"Получен ответ от OpenAI (первые 200 символов): {response_text[:200]}..."
                )
                return {
                    "success": True,
                    "response": response_text,
                    "content": response_text,  # для совместимости
                    "tokens_used": tokens,
                    "is_demo": False,
                }
            else:
                logger.error("Пустой ответ от OpenAI API")
                return {
                    "success": False,
                    "response": "Не удалось получить ответ от AI. Попробуйте позже.",
                    "error": "NO_RESPONSE",
                    "is_demo": False,
                }

        except Exception as e:
            logger.error(f"Ошибка в send_message: {e}")
            return {
                "success": False,
                "response": f"Произошла ошибка: {str(e)}",
                "error": str(e),
                "is_demo": False,
            }

    def _get_demo_response(self, scenario: Optional[str] = None) -> Dict[str, any]:
        """Возвращает демо-ответы когда API недоступен"""
        demo_responses = {
            "plan_day": """📅 **План на день**
                
Утро (9:00-12:00):
• ✅ Выполнить важные задачи
• ☕ Перерыв 15 минут
• 📧 Проверить почту

День (12:00-17:00):
• 🍽 Обед
• 🎯 Фокус-сессии
• 📞 Встречи

Вечер (17:00-21:00):
• 🏃 Активность
• 📚 Обучение
• 🧘 Отдых""",
            "motivation": """💪 **Мотивация дня**
                
Ты способен на большее, чем думаешь!

🌟 Каждый шаг приближает к цели.
🎯 Фокусируйся на главном.
💫 Верь в себя!

Действуй! 🚀""",
            "default": """🤖 **Ассистент в демо-режиме**
                
Для полной функциональности нужно настроить OpenAI API.

А пока используйте другие функции бота:
• 📊 Трекер привычек
• 🎯 Фокус-сессии
• ✅ Чек-лист задач
• 👤 Профиль и достижения""",
        }

        response = demo_responses.get(scenario, demo_responses["default"])

        return {"success": True, "response": response, "is_demo": True}


# Глобальный экземпляр для обратной совместимости
assistant = OpenAIAssistant()
