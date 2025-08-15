"""
Генератор планов для ИИ-ассистента с использованием GPT.
Создает персонализированные планы на основе категории, ответов онбординга и ограничений.
"""
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import uuid
from dataclasses import dataclass
import sys
import os
import json
import logging
import re

# Добавляем корневую папку проекта в путь для импортов
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Импорт моделей из ai_profile.py
from models.ai_profile import (
    PlanData as Plan,
    DayTask,
    Checkpoint,
    BufferDay,
    TaskStatus
)

# Импорт OpenAI API
from utils.openai_api import OpenAIAssistant

logger = logging.getLogger(__name__)
# Устанавливаем уровень логирования для диагностики
logger.setLevel(logging.DEBUG)


def calculate_horizon_days(
    answers: dict,
    constraints: dict,
    category: str,
    default_max: int = 30
) -> int:
    """Вычисляет горизонт планирования на основе входных данных
    
    Args:
        answers: Ответы из онбординга
        constraints: Ограничения пользователя
        category: Категория плана
        default_max: Максимальный горизонт по умолчанию
        
    Returns:
        Количество дней для планирования
    """
    # Приоритет 1: Дедлайн
    if 'deadline' in answers and answers['deadline']:
        try:
            from datetime import datetime
            if isinstance(answers['deadline'], str):
                deadline = datetime.fromisoformat(answers['deadline'])
            else:
                deadline = answers['deadline']
            
            start_date = datetime.now()
            days_until_deadline = (deadline - start_date).days
            
            if days_until_deadline > 0:
                logger.info(f"Горизонт по дедлайну: {days_until_deadline} дней")
                return min(days_until_deadline, default_max)
        except Exception as e:
            logger.warning(f"Не удалось обработать дедлайн: {e}")
    
    # Приоритет 2: Явно указанное количество дней
    if 'horizon_days' in answers and answers['horizon_days']:
        try:
            explicit_days = int(answers['horizon_days'])
            if explicit_days > 0:
                logger.info(f"Явно указанный горизонт: {explicit_days} дней")
                return min(explicit_days, default_max)
        except:
            pass
    
    if 'plan_duration_days' in constraints and constraints['plan_duration_days']:
        try:
            explicit_days = int(constraints['plan_duration_days'])
            if explicit_days > 0:
                logger.info(f"Горизонт из constraints: {explicit_days} дней")
                return min(explicit_days, default_max)
        except:
            pass
    
    # Приоритет 3: Оценка по категории и уровню
    level = answers.get('level', answers.get('current_level', 'начинающий')).lower()
    
    # Базовые оценки по категориям
    category_horizons = {
        'exam': {
            'новичок': 21,
            'начинающий': 21,
            'средний': 14,
            'продвинутый': 10,
            'эксперт': 7
        },
        'skill': {
            'новичок': 30,
            'начинающий': 30,
            'средний': 21,
            'продвинутый': 14,
            'эксперт': 10
        },
        'habit': {
            'новичок': 21,
            'начинающий': 21,
            'средний': 21,
            'продвинутый': 14,
            'эксперт': 14
        },
        'health': {
            'новичок': 14,
            'начинающий': 14,
            'средний': 21,
            'продвинутый': 30,
            'эксперт': 30
        },
        'time': {
            'новичок': 7,
            'начинающий': 7,
            'средний': 14,
            'продвинутый': 21,
            'эксперт': 30
        }
    }
    
    # Получаем оценку для категории
    if category in category_horizons:
        level_key = level
        # Нормализуем уровень
        if level not in category_horizons[category]:
            if 'нович' in level or 'beginner' in level:
                level_key = 'новичок'
            elif 'сред' in level or 'intermediate' in level:
                level_key = 'средний'
            elif 'продвин' in level or 'advanced' in level:
                level_key = 'продвинутый'
            elif 'экспер' in level or 'expert' in level:
                level_key = 'эксперт'
            else:
                level_key = 'начинающий'
        
        estimated_days = category_horizons[category].get(level_key, 15)
        logger.info(f"Оценка горизонта для {category}/{level_key}: {estimated_days} дней")
        return estimated_days
    
    # Дефолт
    logger.info(f"Используем дефолтный горизонт: 15 дней")
    return 15


def validate_plan_constraints(
    plan_json: dict,
    constraints: dict,
    sessions_per_day: Optional[int] = None
) -> Tuple[bool, List[str]]:
    """Валидирует план на соответствие ограничениям
    
    Args:
        plan_json: Сгенерированный план
        constraints: Ограничения пользователя
        sessions_per_day: Количество сессий в день
        
    Returns:
        (успех, список ошибок)
    """
    errors = []
    daily_minutes = constraints.get('daily_minutes', constraints.get('daily_time_minutes', 60))
    no_study_after = constraints.get('no_study_after', '23:59')
    blackout = constraints.get('blackout', [])
    
    # Парсим время ограничения
    try:
        limit_hour, limit_minute = map(int, no_study_after.split(':'))
        limit_time_minutes = limit_hour * 60 + limit_minute
    except:
        limit_time_minutes = 23 * 60 + 59
    
    for day_data in plan_json.get('days', []):
        day_num = day_data.get('day', 0)
        tasks = day_data.get('tasks', [])
        
        # Проверка количества задач
        if sessions_per_day and len(tasks) != sessions_per_day:
            errors.append(f"День {day_num}: {len(tasks)} задач вместо {sessions_per_day}")
        
        # Проверка суммарного времени
        total_minutes = 0
        for task in tasks:
            # Пытаемся извлечь длительность из описания
            activity = task.get('activity', '')
            time_str = task.get('time', '')
            
            # Ищем упоминания минут в активности
            import re
            duration_match = re.search(r'(\d+)\s*мин', activity)
            if duration_match:
                total_minutes += int(duration_match.group(1))
            else:
                # Если не нашли, предполагаем 30 минут по умолчанию
                total_minutes += 30
            
            # Проверка времени начала
            if time_str:
                try:
                    task_hour, task_minute = map(int, time_str.split(':'))
                    task_time_minutes = task_hour * 60 + task_minute
                    
                    if task_time_minutes >= limit_time_minutes:
                        errors.append(f"День {day_num}: задача в {time_str} после ограничения {no_study_after}")
                    
                    # Проверка blackout окон
                    for window in blackout:
                        if '-' in window:
                            try:
                                start, end = window.split('-')
                                start_h, start_m = map(int, start.strip().split(':'))
                                end_h, end_m = map(int, end.strip().split(':'))
                                start_minutes = start_h * 60 + start_m
                                end_minutes = end_h * 60 + end_m
                                
                                if start_minutes <= task_time_minutes <= end_minutes:
                                    errors.append(f"День {day_num}: задача в {time_str} попадает в blackout {window}")
                            except:
                                pass
                except:
                    pass
        
        if total_minutes > daily_minutes:
            errors.append(f"День {day_num}: суммарное время {total_minutes} мин > лимита {daily_minutes} мин")
    
    return len(errors) == 0, errors


def validate_plan_json(plan_json: Any) -> Optional[str]:
    """
    Валидация структуры JSON плана
    
    Args:
        plan_json: JSON объект для валидации
        
    Returns:
        None если валидно, иначе строка с описанием ошибки
    """
    if not isinstance(plan_json, dict):
        return f"JSON не является объектом: {type(plan_json)}"
    
    if 'days' not in plan_json:
        return "Отсутствует обязательное поле 'days'"
    
    if not isinstance(plan_json['days'], list):
        return f"Поле 'days' не является списком: {type(plan_json['days'])}"
    
    if len(plan_json['days']) == 0:
        return "Массив 'days' пустой"
    
    # Проверяем структуру каждого дня
    for i, day in enumerate(plan_json['days']):
        if not isinstance(day, dict):
            return f"День {i+1} не является объектом"
        
        if 'day' not in day:
            return f"День {i+1} не содержит поле 'day'"
        
        if 'tasks' not in day:
            return f"День {i+1} не содержит поле 'tasks'"
        
        if not isinstance(day['tasks'], list):
            return f"Поле 'tasks' дня {i+1} не является списком"
        
        if len(day['tasks']) == 0:
            return f"День {i+1} не содержит задач"
        
        # Проверяем структуру каждой задачи
        for j, task in enumerate(day['tasks']):
            if not isinstance(task, dict):
                return f"Задача {j+1} дня {i+1} не является объектом"
            
            if 'time' not in task:
                return f"Задача {j+1} дня {i+1} не содержит поле 'time'"
            
            if 'activity' not in task:
                return f"Задача {j+1} дня {i+1} не содержит поле 'activity'"
            
            # Проверяем формат времени
            time_str = str(task['time'])
            if not re.match(r'^([01]\d|2[0-3]):[0-5]\d$', time_str):
                logger.warning(f"Некорректный формат времени '{time_str}' в задаче {j+1} дня {i+1}")
            
            # Проверяем длину названия активности
            activity = str(task['activity'])
            if len(activity) == 0:
                return f"Пустое название активности в задаче {j+1} дня {i+1}"
            
            if len(activity) > 300:
                logger.warning(f"Слишком длинное название активности ({len(activity)} символов) в задаче {j+1} дня {i+1}")
    
    return None  # Валидация прошла успешно


def parse_or_fix_json(text: str) -> dict:
    """
    Надежный парсер/восстановитель JSON
    
    Args:
        text: Строка с потенциально поврежденным JSON
        
    Returns:
        dict: Распарсенный JSON
        
    Raises:
        json.JSONDecodeError: Если не удалось восстановить JSON
    """
    if not text:
        raise json.JSONDecodeError("Пустой ответ", "", 0)
    
    # Шаг 1: Пытаемся распарсить как есть
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.warning(f"Первая попытка парсинга JSON не удалась: {e}")
        logger.debug(f"Позиция ошибки: строка {e.lineno}, колонка {e.colno}")
        
        # Логируем проблемный фрагмент
        if hasattr(e, 'pos'):
            start = max(0, e.pos - 200)
            end = min(len(text), e.pos + 200)
            logger.debug(f"Проблемный фрагмент (±200 символов от позиции {e.pos}):")
            logger.debug(f"...{text[start:end]}...")
    
    # Шаг 2: Применяем исправления
    fixed_text = text
    fixes_applied = []
    
    # 2.1: Извлекаем JSON из возможных обрамлений
    if '```json' in fixed_text:
        fixed_text = fixed_text.split('```json')[1].split('```')[0]
        fixes_applied.append("removed markdown json block")
    elif '```' in fixed_text:
        fixed_text = fixed_text.split('```')[1].split('```')[0]
        fixes_applied.append("removed markdown block")
    
    # 2.2: Обрезаем до первого { и после последней }
    first_brace = fixed_text.find('{')
    last_brace = fixed_text.rfind('}')
    if first_brace > 0 or (last_brace > 0 and last_brace < len(fixed_text) - 1):
        if first_brace >= 0 and last_brace > first_brace:
            fixed_text = fixed_text[first_brace:last_brace + 1]
            fixes_applied.append("trimmed to JSON boundaries")
    
    # 2.3: Заменяем умные кавычки на обычные
    smart_quotes = [
        ('"', '"'),  # Left double quotation mark
        ('"', '"'),  # Right double quotation mark
        (''', "'"),  # Left single quotation mark
        (''', "'"),  # Right single quotation mark
        ('«', '"'),  # Left-pointing double angle quotation mark
        ('»', '"'),  # Right-pointing double angle quotation mark
    ]
    for smart, regular in smart_quotes:
        if smart in fixed_text:
            fixed_text = fixed_text.replace(smart, regular)
            fixes_applied.append(f"replaced smart quotes ({smart})")
    
    # 2.4: Обрабатываем многоточия
    # Убираем многоточия в массивах (например, [...,] или просто ...)
    fixed_text = re.sub(r'\[\s*\.\.\.\s*,?\s*\]', '[]', fixed_text)
    fixed_text = re.sub(r'\[\s*…\s*,?\s*\]', '[]', fixed_text)
    
    # Убираем отдельно стоящие многоточия как элементы массива
    fixed_text = re.sub(r',\s*\.\.\.\s*,', ',', fixed_text)
    fixed_text = re.sub(r',\s*…\s*,', ',', fixed_text)
    fixed_text = re.sub(r'\[\s*\.\.\.\s*,', '[', fixed_text)
    fixed_text = re.sub(r',\s*\.\.\.\s*\]', ']', fixed_text)
    fixed_text = re.sub(r'\[\s*…\s*,', '[', fixed_text)
    fixed_text = re.sub(r',\s*…\s*\]', ']', fixed_text)
    
    # Убираем многоточия в конце строк перед запятыми или скобками
    fixed_text = re.sub(r'"\.\.\."\s*,\s*\]', '"]', fixed_text)
    fixed_text = re.sub(r'"…"\s*,\s*\]', '"]', fixed_text)
    fixed_text = re.sub(r'\.\.\.\s*,\s*}', '}', fixed_text)
    fixed_text = re.sub(r'…\s*,\s*}', '}', fixed_text)
    fixed_text = re.sub(r'\.\.\.\s*,\s*\]', ']', fixed_text)
    fixed_text = re.sub(r'…\s*,\s*\]', ']', fixed_text)
    
    # Заменяем многоточия в строках на "..." (упрощенный подход без look-behind)
    # Заменяем все standalone многоточия, которые не в строках
    fixed_text = re.sub(r':\s*\.\.\.\s*([,}])', r': "..."\1', fixed_text)
    fixed_text = re.sub(r':\s*…\s*([,}])', r': "..."\1', fixed_text)
    
    if ('...' in text or '…' in text) and fixed_text != text:
        fixes_applied.append("fixed ellipsis")
    
    # 2.5: Убираем trailing commas перед закрывающими скобками
    original_len = len(fixed_text)
    fixed_text = re.sub(r',\s*}', '}', fixed_text)
    fixed_text = re.sub(r',\s*]', ']', fixed_text)
    if len(fixed_text) < original_len:
        fixes_applied.append("removed trailing commas")
    
    # 2.6: Добавляем кавычки вокруг некавыченных ключей
    # Ищем паттерн: слово без кавычек перед двоеточием
    fixed_text = re.sub(r'([{,]\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:', r'\1"\2":', fixed_text)
    if re.search(r'([{,]\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:', text) and not re.search(r'([{,]\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:', fixed_text):
        fixes_applied.append("added quotes to unquoted keys")
    
    # 2.7: Пытаемся распарсить после исправлений
    try:
        if fixes_applied:
            logger.info(f"Применены исправления JSON: {', '.join(fixes_applied)}")
        return json.loads(fixed_text)
    except json.JSONDecodeError as e:
        logger.warning(f"Парсинг после базовых исправлений не удался: {e}")
    
    # Шаг 3: Балансировка скобок
    open_braces = fixed_text.count('{')
    close_braces = fixed_text.count('}')
    open_brackets = fixed_text.count('[')
    close_brackets = fixed_text.count(']')
    
    if open_braces != close_braces or open_brackets != close_brackets:
        logger.info(f"Дисбаланс скобок: {{:{open_braces} }}:{close_braces} [:{open_brackets} ]:{close_brackets}")
        
        # Добавляем недостающие закрывающие скобки
        if open_braces > close_braces:
            fixed_text += '}' * (open_braces - close_braces)
            fixes_applied.append(f"added {open_braces - close_braces} closing braces")
        
        if open_brackets > close_brackets:
            # Проверяем, нужно ли закрыть массив перед закрывающей фигурной скобкой
            if fixed_text.rstrip().endswith('}'):
                fixed_text = fixed_text.rstrip('}')
                fixed_text += ']' * (open_brackets - close_brackets) + '}'
            else:
                fixed_text += ']' * (open_brackets - close_brackets)
            fixes_applied.append(f"added {open_brackets - close_brackets} closing brackets")
    
    # Шаг 4: Финальная попытка парсинга
    try:
        if fixes_applied:
            logger.info(f"Все применённые исправления: {', '.join(fixes_applied)}")
        result = json.loads(fixed_text)
        logger.info("JSON успешно восстановлен после исправлений")
        return result
    except json.JSONDecodeError as e:
        logger.error(f"Не удалось восстановить JSON после всех попыток: {e}")
        logger.error(f"Финальная позиция ошибки: строка {e.lineno}, колонка {e.colno}")
        
        # Логируем проблемный участок финального текста
        if hasattr(e, 'pos'):
            start = max(0, e.pos - 200)
            end = min(len(fixed_text), e.pos + 200)
            logger.error(f"Финальный проблемный фрагмент (±200 символов от позиции {e.pos}):")
            logger.error(f"...{fixed_text[start:end]}...")
        
        # Пробрасываем исключение дальше
        raise


@dataclass
class PlanSlot:
    """Временной слот для задачи в плане"""
    time: str  # Формат "HH:MM-HH:MM"
    task: str  # Описание задачи
    est_min: int  # Оценка времени в минутах


async def generate_plan(
    category: str,  # "exam"|"skill"|"habit"|"health"|"time"
    answers: dict,  # из onboarding.answers
    constraints: dict,  # из ai_profile.constraints
    horizon_days: Optional[int] = None
) -> Plan:
    """
    Генерирует план с использованием GPT на основе входных параметров.
    
    Args:
        category: Категория плана
        answers: Ответы из онбординга
        constraints: Ограничения пользователя
        horizon_days: Горизонт планирования (если None - вычисляется автоматически)
        
    Returns:
        Plan: Сгенерированный план
    """
    # Вычисляем горизонт если не задан
    if horizon_days is None:
        horizon_days = calculate_horizon_days(answers, constraints, category)
    
    # Извлекаем основные ограничения
    daily_minutes = constraints.get('daily_minutes', constraints.get('daily_time_minutes', 60))
    no_study_after = constraints.get('no_study_after', '22:00')
    blackout = constraints.get('blackout', [])
    weekdays_only = constraints.get('weekdays_only', False)
    sessions_per_day = constraints.get('sessions_per_day', answers.get('sessions_per_day', None))
    
    # Используем глобальный экземпляр OpenAI Assistant или создаем новый
    try:
        from utils.openai_api import assistant
        openai_assistant = assistant
    except ImportError:
        logger.warning("Не удалось импортировать OpenAI assistant, создаем новый экземпляр")
        openai_assistant = OpenAIAssistant()
    
    # Проверяем настройку API
    if not openai_assistant.is_configured:
        logger.warning("OpenAI API не настроен, используется детерминированная генерация плана")
        return await generate_plan_deterministic(category, answers, constraints, horizon_days)
    
    if not openai_assistant.has_api_key():
        logger.warning("OpenAI API ключ не найден, используется детерминированная генерация плана")
        return await generate_plan_deterministic(category, answers, constraints, horizon_days)
    
    if not openai_assistant.is_available():
        logger.warning("OpenAI API недоступен, используется детерминированная генерация плана")
        return await generate_plan_deterministic(category, answers, constraints, horizon_days)
    
    # JSON схема для плана
    plan_schema = {
        "name": "timeflow_plan_schema",
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["days"],
            "properties": {
                "days": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["day", "tasks"],
                        "properties": {
                            "day": {"type": "integer", "minimum": 1},
                            "tasks": {
                                "type": "array",
                                "minItems": 1,
                                "items": {
                                    "type": "object",
                                    "additionalProperties": False,
                                    "required": ["time", "activity"],
                                    "properties": {
                                        "time": {
                                            "type": "string",
                                            "pattern": "^([01]\\d|2[0-3]):[0-5]\\d$"
                                        },
                                        "activity": {
                                            "type": "string",
                                            "minLength": 1,
                                            "maxLength": 300
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    
    # Счетчик попыток
    max_attempts = 2
    
    for attempt in range(1, max_attempts + 1):
        logger.info(f"Попытка {attempt}/{max_attempts} генерации плана через GPT")
        
        try:
            # Загружаем промпт из JSON файла
            prompt_config = await load_plan_prompt()
            
            # Подготавливаем данные для промпта
            from datetime import datetime
            prompt_data = {
                'category': category,
                'goal': answers.get('goal', answers.get('goal_type', category)),
                'level': answers.get('level', answers.get('current_level', 'начинающий')),
                'daily_minutes': daily_minutes,
                'sessions_per_day': sessions_per_day if sessions_per_day else '',
                'sessions_per_day_or_default': sessions_per_day if sessions_per_day else 2,
                'no_study_after': no_study_after,
                'blackout': ', '.join(blackout) if blackout else 'нет',
                'weekdays_only': 'да' if weekdays_only else 'нет',
                'start_date': datetime.now().strftime('%Y-%m-%d'),
                'deadline': answers.get('deadline', ''),
                'preferences': json.dumps(answers, ensure_ascii=False, indent=2)
            }
            
            # Форматируем промпт
            user_prompt = prompt_config.get('template_user', '').format(**prompt_data)
            system_prompt = prompt_config.get('system', '')
            
            # Ограничиваем количество дней разумным максимумом
            days_to_generate = min(horizon_days, 30)
            
            # Добавляем информацию о горизонте
            user_prompt += f"\n\nПлан должен содержать ровно {days_to_generate} дней."
            
            # Используем новый метод generate_json_response
            logger.info(f"Запрашиваем план у GPT для категории {category} через generate_json_response")
            logger.debug(f"Промпт для GPT (первые 500 символов): {user_prompt[:500]}...")
            
            # Адаптируем количество токенов в зависимости от количества дней
            max_tokens = min(500 + (days_to_generate * 150), 4000)
            
            # Вызываем новый метод со схемой
            plan_json, finish_reason, tokens_used = await openai_assistant.generate_json_response(
                prompt=user_prompt,
                json_schema=plan_schema if attempt == 1 else None,  # На второй попытке без схемы
                max_tokens=max_tokens,
                temperature=0.2,
                continue_if_truncated=True,
                system_prompt=system_prompt
            )
            
            logger.info(f"Получен ответ: finish_reason={finish_reason}, tokens={tokens_used}")
            
            # Если generate_json_response не смог распарсить, пробуем наш парсер
            if plan_json is None:
                logger.warning("generate_json_response не смог распарсить JSON, пробуем восстановить")
                
                # Попробуем получить сырой ответ через обычный метод для восстановления
                if attempt == max_attempts:
                    # На последней попытке используем детерминированную генерацию
                    return await generate_plan_deterministic(category, answers, constraints, horizon_days)
                continue  # Пробуем еще раз с другими параметрами
            
            # Валидация структуры JSON
            validation_error = validate_plan_json(plan_json)
            if validation_error:
                logger.error(f"Ошибка валидации плана: {validation_error}")
                if attempt == max_attempts:
                    return await generate_plan_deterministic(category, answers, constraints, horizon_days)
                continue  # Пробуем еще раз
            
            # Валидируем ограничения
            is_valid, validation_errors = validate_plan_constraints(
                plan_json,
                constraints,
                sessions_per_day
            )
            
            if not is_valid and attempt == 1:
                logger.warning(f"План не прошел валидацию: {validation_errors}")
                
                # Пытаемся исправить через rectify
                rectify_prompt = prompt_config.get('rectify_prompt', '')
                if rectify_prompt:
                    rectify_data = {
                        'daily_minutes': daily_minutes,
                        'sessions_per_day': sessions_per_day if sessions_per_day else 2,
                        'no_study_after': no_study_after,
                        'blackout': ', '.join(blackout) if blackout else 'нет'
                    }
                    
                    # Добавляем информацию об ошибках
                    for error in validation_errors[:3]:  # Максимум 3 ошибки
                        if 'день' in error.lower():
                            day_match = re.search(r'день\s+(\d+)', error, re.IGNORECASE)
                            if day_match:
                                rectify_data['day_number'] = day_match.group(1)
                            if 'суммарное' in error:
                                time_match = re.search(r'(\d+)\s*мин', error)
                                if time_match:
                                    rectify_data['total_minutes'] = time_match.group(1)
                            break
                    
                    rectify_text = rectify_prompt.format(**rectify_data)
                    rectify_text += f"\n\nПредыдущий план:\n{json.dumps(plan_json, ensure_ascii=False)}"
                    
                    # Пытаемся исправить
                    rectified_json, _, _ = await openai_assistant.generate_json_response(
                        prompt=rectify_text,
                        json_schema=plan_schema,
                        max_tokens=max_tokens,
                        temperature=0.1,
                        system_prompt=system_prompt
                    )
                    
                    if rectified_json:
                        plan_json = rectified_json
                        logger.info("План успешно исправлен через rectify")
            
            # Ограничиваем количество дней если их слишком много
            if len(plan_json['days']) > days_to_generate:
                logger.warning(f"GPT сгенерировал {len(plan_json['days'])} дней вместо {days_to_generate}, обрезаем")
                plan_json['days'] = plan_json['days'][:days_to_generate]
            
            # Если получили меньше дней чем нужно, дополняем план
            actual_days = len(plan_json.get('days', []))
            if actual_days < horizon_days:
                logger.info(f"Получено {actual_days} дней из {horizon_days}, дополняем план")
                # Дополним недостающие дни базовыми задачами
                for day_num in range(actual_days + 1, min(horizon_days + 1, actual_days + 8)):
                    plan_json['days'].append({
                        'day': day_num,
                        'tasks': [
                            {'time': '09:00', 'activity': f'Основная задача дня {day_num}'},
                            {'time': '14:00', 'activity': f'Дополнительная задача дня {day_num}'}
                        ]
                    })
            
            # Преобразуем JSON в модель Plan
            plan = await json_to_plan(plan_json, category, horizon_days)
            
            logger.info(f"План успешно сгенерирован через GPT для категории {category}")
            logger.debug(f"Сгенерировано дней: {len(plan_json.get('days', []))}, задач: {sum(len(d.get('tasks', [])) for d in plan_json.get('days', []))}")
            return plan
            
        except Exception as e:
            logger.error(f"Попытка {attempt}: Ошибка при генерации плана через GPT: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            if attempt == max_attempts:
                return await generate_plan_deterministic(category, answers, constraints, horizon_days)
            continue  # Пробуем еще раз
    
    # Если все попытки исчерпаны
    logger.error("Все попытки генерации плана через GPT исчерпаны")
    return await generate_plan_deterministic(category, answers, constraints, horizon_days)


async def load_plan_prompt() -> Dict[str, Any]:
    """Загружает промпт для генерации плана из JSON файла"""
    try:
        prompt_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'ai_prompts', 'plan_prompts.json')
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        # Пробуем старый файл txt для обратной совместимости
        try:
            prompt_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'plan_promt.txt')
            with open(prompt_path, 'r', encoding='utf-8') as f:
                old_prompt = f.read()
                return {
                    'system': 'Ты — умный и опытный персональный тренер и наставник.',
                    'template_user': old_prompt
                }
        except:
            pass
    except Exception as e:
        logger.error(f"Ошибка загрузки промпта: {e}")
    
    # Возвращаем базовый промпт
    return {
        'system': 'Ты — персональный наставник по продуктивности и обучению.',
        'template_user': """Данные пользователя:
- Категория: {category}
- Минут в день: {daily_minutes}
- Запрет после: {no_study_after}
- Blackout: {blackout}
- Только будни: {weekdays_only}
- Доп. данные: {preferences}

Составь план в формате JSON:
{{
  "days": [
    {{
      "day": 1,
      "tasks": [
        {{"time": "HH:MM", "activity": "описание"}}
      ]
    }}
  ]
}}"""
    }


async def json_to_plan(plan_json: dict, category: str, horizon_days: int) -> Plan:
    """
    Преобразует JSON от GPT в модель Plan
    
    Args:
        plan_json: JSON с планом от GPT
        category: Категория плана
        horizon_days: Горизонт планирования
        
    Returns:
        Plan: Модель плана
    """
    days = []
    checkpoints = []
    buffer_days = []
    
    try:
        # Обрабатываем дни из JSON
        days_data = plan_json.get('days', [])
        
        if not days_data:
            logger.warning("JSON от GPT не содержит дней, используем детерминированную генерацию")
            # Если нет дней, создаем минимальный план
            for day_num in range(1, min(horizon_days + 1, 8)):
                task = DayTask(
                    id=str(uuid.uuid4()),
                    day_number=day_num,
                    title=f"Основная задача дня {day_num}",
                    description="Время: 09:00-10:00",
                    duration_minutes=60,
                    priority=1,
                    status=TaskStatus.PENDING
                )
                days.append(task)
        else:
            for day_data in days_data:
                # Безопасное извлечение данных с проверками
                if not isinstance(day_data, dict):
                    logger.warning(f"Некорректный формат дня: {day_data}")
                    continue
                    
                day_num = day_data.get('day', 1)
                if not isinstance(day_num, int):
                    try:
                        day_num = int(day_num)
                    except (ValueError, TypeError):
                        logger.warning(f"Некорректный номер дня: {day_data.get('day')}")
                        continue
                
                tasks = day_data.get('tasks', [])
                if not isinstance(tasks, list):
                    logger.warning(f"Некорректный формат задач для дня {day_num}")
                    continue
                
                for i, task_data in enumerate(tasks):
                    if not isinstance(task_data, dict):
                        logger.warning(f"Некорректный формат задачи: {task_data}")
                        continue
                        
                    time_str = str(task_data.get('time', '09:00'))
                    activity = str(task_data.get('activity', f'Задача {i+1}'))
                    
                    # Вычисляем длительность из времени если возможно
                    duration = 30  # По умолчанию 30 минут
                    if '-' in time_str:
                        try:
                            start, end = time_str.split('-')
                            start_h, start_m = map(int, start.strip().split(':'))
                            end_h, end_m = map(int, end.strip().split(':'))
                            duration = (end_h * 60 + end_m) - (start_h * 60 + start_m)
                            if duration <= 0 or duration > 240:  # Проверка на адекватность
                                duration = 30
                        except Exception as e:
                            logger.debug(f"Не удалось извлечь длительность из {time_str}: {e}")
                    
                    task = DayTask(
                        id=str(uuid.uuid4()),
                        day_number=day_num,
                        title=activity[:100],  # Ограничиваем длину названия
                        description=f"Время: {time_str}",
                        duration_minutes=duration,
                        priority=1 if i == 0 else 2,  # Первая задача дня - приоритетная
                        status=TaskStatus.PENDING
                    )
                    days.append(task)
        
        # Если план пустой, добавляем хотя бы одну задачу
        if not days:
            logger.warning("План от GPT пустой, добавляем минимальную задачу")
            task = DayTask(
                id=str(uuid.uuid4()),
                day_number=1,
                title="Начало работы над целью",
                description="Время: 09:00-10:00",
                duration_minutes=60,
                priority=1,
                status=TaskStatus.PENDING
            )
            days.append(task)
            
    except Exception as e:
        logger.error(f"Ошибка при обработке JSON от GPT: {e}")
        # В случае ошибки создаем минимальный план
        for day_num in range(1, 4):
            task = DayTask(
                id=str(uuid.uuid4()),
                day_number=day_num,
                title=f"Задача дня {day_num}",
                description="Время: 09:00-10:00",
                duration_minutes=60,
                priority=1,
                status=TaskStatus.PENDING
            )
            days.append(task)
    
    # Добавляем чекпоинты каждые 5 дней
    for day_num in range(5, horizon_days + 1, 5):
        checkpoint = Checkpoint(
            id=str(uuid.uuid4()),
            day_number=day_num,
            title=f"Контрольная точка - День {day_num}",
            description="Оценка прогресса и корректировка плана",
            criteria=[
                f"Выполнено {day_num} дней плана",
                "Оценен текущий прогресс",
                "План скорректирован при необходимости"
            ],
            status=TaskStatus.PENDING
        )
        checkpoints.append(checkpoint)
    
    # Создаем итоговый план
    plan = Plan(
        type=category,
        horizon_days=horizon_days,
        days=days,
        checkpoints=checkpoints,
        buffer_days=buffer_days,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    return plan


async def generate_plan_deterministic(
    category: str,
    answers: dict,
    constraints: dict,
    horizon_days: int = 15
) -> Plan:
    """
    Детерминированная генерация плана (fallback если GPT недоступен)
    """
    # Извлекаем основные ограничения
    daily_minutes = constraints.get('daily_minutes', constraints.get('daily_time_minutes', 60))
    no_study_after = constraints.get('no_study_after', '22:00')
    blackout = constraints.get('blackout', [])
    weekdays_only = constraints.get('weekdays_only', False)
    
    # Создаем дни плана
    days = []
    checkpoints = []
    buffer_days = []
    
    # Начальная дата (сегодня)
    start_date = datetime.now()
    
    for day_num in range(1, horizon_days + 1):
        current_date = start_date + timedelta(days=day_num - 1)
        weekday = current_date.weekday()  # 0 = понедельник, 6 = воскресенье
        
        # Пропускаем выходные если weekdays_only
        if weekdays_only and weekday in [5, 6]:
            # Добавляем как буферный день
            if weekday == 6:  # Воскресенье
                buffer_days.append(BufferDay(
                    day_number=day_num,
                    reason="Выходной день для восстановления",
                    activities=["Легкий обзор материалов", "Отдых"]
                ))
            continue
        
        # Проверяем blackout периоды
        day_name = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][weekday]
        is_blackout = any(
            day_name in period for period in blackout
        )
        
        if is_blackout:
            continue
        
        # Генерируем слоты для дня
        slots = _generate_day_slots(
            category=category,
            day_num=day_num,
            weekday=weekday,
            daily_minutes=daily_minutes,
            no_study_after=no_study_after,
            answers=answers
        )
        
        # Преобразуем слоты в задачи дня
        day_tasks = []
        for i, slot in enumerate(slots):
            task = DayTask(
                id=str(uuid.uuid4()),
                day_number=day_num,
                title=slot.task,
                description=f"Время: {slot.time}",
                duration_minutes=slot.est_min,
                priority=1 if i == 0 else 2,  # Первая задача дня - приоритетная
                status=TaskStatus.PENDING
            )
            day_tasks.append(task)
        
        days.extend(day_tasks)
        
        # Добавляем чекпоинты каждые 4-5 дней
        if day_num % 5 == 0 or (category == "exam" and day_num % 4 == 0):
            checkpoint = _generate_checkpoint(category, day_num, answers)
            checkpoints.append(checkpoint)
        
        # Добавляем буферные дни для восстановления
        if category == "health" and day_num % 3 == 0:
            buffer_days.append(BufferDay(
                day_number=day_num + 1,
                reason="День восстановления после интенсивных тренировок",
                activities=["Растяжка", "Легкая прогулка", "Массаж"]
            ))
    
    # Создаем итоговый план
    plan = Plan(
        type=category,
        horizon_days=horizon_days,
        days=days,
        checkpoints=checkpoints,
        buffer_days=buffer_days[:2],  # Максимум 2 буферных дня
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    return plan


def _generate_day_slots(
    category: str,
    day_num: int,
    weekday: int,
    daily_minutes: int,
    no_study_after: str,
    answers: dict
) -> List[PlanSlot]:
    """Генерирует слоты для конкретного дня"""
    slots = []
    
    # Парсим ограничение по времени
    hour_limit, minute_limit = map(int, no_study_after.split(':'))
    
    # Базовое время начала
    start_hour = 8 if weekday < 5 else 9  # Будни vs выходные
    current_hour = start_hour
    current_minute = 0
    
    # Определяем количество слотов (2-4)
    num_slots = 3 if daily_minutes <= 120 else 4
    if daily_minutes <= 60:
        num_slots = 2
    
    # Время на слот
    minutes_per_slot = daily_minutes // num_slots
    
    # Генерируем слоты по категориям
    if category == "exam":
        slots = _generate_exam_slots(
            day_num, num_slots, minutes_per_slot, 
            current_hour, current_minute, hour_limit
        )
    elif category == "skill":
        slots = _generate_skill_slots(
            day_num, num_slots, minutes_per_slot,
            current_hour, current_minute, hour_limit
        )
    elif category == "habit":
        slots = _generate_habit_slots(
            day_num, num_slots, minutes_per_slot,
            current_hour, current_minute, hour_limit
        )
    elif category == "health":
        slots = _generate_health_slots(
            day_num, num_slots, minutes_per_slot,
            current_hour, current_minute, hour_limit
        )
    elif category == "time":
        slots = _generate_time_slots(
            day_num, num_slots, minutes_per_slot,
            current_hour, current_minute, hour_limit
        )
    
    return slots


def _generate_exam_slots(
    day_num: int, num_slots: int, minutes_per_slot: int,
    start_hour: int, start_minute: int, hour_limit: int
) -> List[PlanSlot]:
    """Генерирует слоты для подготовки к экзамену"""
    slots = []
    current_hour = start_hour
    current_minute = start_minute
    
    # Шаблон: повторение → практика → симуляция
    templates = [
        "Повторение ключевых тем",
        "Решение практических задач",
        "Разбор сложных вопросов",
        "Мини-тест по пройденному"
    ]
    
    # Раз в неделю - полутест
    if day_num % 7 == 0:
        templates[2] = "Пробный экзамен (часть)"
    
    for i in range(num_slots):
        if current_hour >= hour_limit:
            break
            
        template = templates[i % len(templates)]
        end_hour = current_hour
        end_minute = current_minute + minutes_per_slot
        
        # Корректировка времени
        if end_minute >= 60:
            end_hour += end_minute // 60
            end_minute = end_minute % 60
        
        time_str = f"{current_hour:02d}:{current_minute:02d}-{end_hour:02d}:{end_minute:02d}"
        
        slots.append(PlanSlot(
            time=time_str,
            task=template,
            est_min=minutes_per_slot
        ))
        
        # Перерыв между слотами (15 минут)
        current_hour = end_hour
        current_minute = end_minute + 15
        if current_minute >= 60:
            current_hour += 1
            current_minute -= 60
    
    return slots


def _generate_skill_slots(
    day_num: int, num_slots: int, minutes_per_slot: int,
    start_hour: int, start_minute: int, hour_limit: int
) -> List[PlanSlot]:
    """Генерирует слоты для развития навыка"""
    slots = []
    current_hour = start_hour
    current_minute = start_minute
    
    # Цикл: теория → практика → проект → ревью
    cycle_day = (day_num - 1) % 4
    templates = [
        ["Изучение теории", "Просмотр примеров", "Конспектирование"],
        ["Базовые упражнения", "Отработка техники", "Повторение основ"],
        ["Работа над мини-проектом", "Применение навыков", "Творческая практика"],
        ["Анализ результатов", "Работа над ошибками", "Планирование улучшений"]
    ]
    
    day_templates = templates[cycle_day]
    
    for i in range(num_slots):
        if current_hour >= hour_limit:
            break
            
        template = day_templates[i % len(day_templates)]
        end_hour = current_hour
        end_minute = current_minute + minutes_per_slot
        
        if end_minute >= 60:
            end_hour += end_minute // 60
            end_minute = end_minute % 60
        
        time_str = f"{current_hour:02d}:{current_minute:02d}-{end_hour:02d}:{end_minute:02d}"
        
        slots.append(PlanSlot(
            time=time_str,
            task=template,
            est_min=minutes_per_slot
        ))
        
        # Перерыв 10 минут
        current_hour = end_hour
        current_minute = end_minute + 10
        if current_minute >= 60:
            current_hour += 1
            current_minute -= 60
    
    return slots


def _generate_habit_slots(
    day_num: int, num_slots: int, minutes_per_slot: int,
    start_hour: int, start_minute: int, hour_limit: int
) -> List[PlanSlot]:
    """Генерирует слоты для формирования привычки"""
    slots = []
    
    # Утренний якорь (7:00-8:00)
    slots.append(PlanSlot(
        time="07:00-07:30",
        task="Утренний ритуал привычки",
        est_min=30
    ))
    
    # Анти-триггер слот (середина дня)
    if num_slots >= 2:
        slots.append(PlanSlot(
            time="14:00-14:20",
            task="Работа с триггерами и соблазнами",
            est_min=20
        ))
    
    # Вечерний якорь
    if num_slots >= 3:
        slots.append(PlanSlot(
            time="20:00-20:30",
            task="Вечернее закрепление привычки",
            est_min=30
        ))
    
    # План B (короткая альтернатива)
    if num_slots >= 4:
        slots.append(PlanSlot(
            time="12:00-12:10",
            task="Экспресс-версия привычки (план B)",
            est_min=10
        ))
    
    return slots[:num_slots]


def _generate_health_slots(
    day_num: int, num_slots: int, minutes_per_slot: int,
    start_hour: int, start_minute: int, hour_limit: int
) -> List[PlanSlot]:
    """Генерирует слоты для здоровья и фитнеса"""
    slots = []
    current_hour = start_hour
    current_minute = start_minute
    
    # Чередование интенсивности
    intensity_cycle = ["легкий", "средний", "отдых", "средний", "легкий"]
    intensity = intensity_cycle[(day_num - 1) % len(intensity_cycle)]
    
    if intensity == "отдых":
        # День восстановления
        slots.append(PlanSlot(
            time="09:00-09:30",
            task="Легкая растяжка и дыхательные упражнения",
            est_min=30
        ))
        if num_slots >= 2:
            slots.append(PlanSlot(
                time="18:00-18:30",
                task="Вечерняя йога или медитация",
                est_min=30
            ))
    else:
        # Тренировочные дни
        templates = {
            "легкий": ["Разминка и легкое кардио", "Растяжка и восстановление"],
            "средний": ["Силовая тренировка", "Кардио средней интенсивности", "Заминка"]
        }
        
        day_templates = templates[intensity]
        
        for i in range(min(num_slots, len(day_templates))):
            if current_hour >= hour_limit:
                break
                
            template = day_templates[i]
            duration = minutes_per_slot if i < len(day_templates) - 1 else 20
            
            end_hour = current_hour
            end_minute = current_minute + duration
            
            if end_minute >= 60:
                end_hour += end_minute // 60
                end_minute = end_minute % 60
            
            time_str = f"{current_hour:02d}:{current_minute:02d}-{end_hour:02d}:{end_minute:02d}"
            
            slots.append(PlanSlot(
                time=time_str,
                task=f"{template} ({intensity} уровень)",
                est_min=duration
            ))
            
            current_hour = end_hour
            current_minute = end_minute + 15
            if current_minute >= 60:
                current_hour += 1
                current_minute -= 60
    
    return slots


def _generate_time_slots(
    day_num: int, num_slots: int, minutes_per_slot: int,
    start_hour: int, start_minute: int, hour_limit: int
) -> List[PlanSlot]:
    """Генерирует слоты для тайм-менеджмента"""
    slots = []
    
    # Слоты под пики продуктивности
    productivity_slots = [
        PlanSlot(
            time="09:00-10:30",
            task="Глубокая работа (пик продуктивности)",
            est_min=90
        ),
        PlanSlot(
            time="11:00-12:00",
            task="Важные встречи и коммуникации",
            est_min=60
        ),
        PlanSlot(
            time="14:00-15:30",
            task="Фокусная работа (без отвлечений)",
            est_min=90
        ),
        PlanSlot(
            time="16:00-17:00",
            task="Планирование и подведение итогов",
            est_min=60
        )
    ]
    
    # Выбираем нужное количество слотов
    return productivity_slots[:num_slots]


def _generate_checkpoint(category: str, day_num: int, answers: dict) -> Checkpoint:
    """Генерирует контрольную точку для плана"""
    checkpoint_templates = {
        "exam": {
            "title": f"Контроль знаний - День {day_num}",
            "description": "Проверка усвоения материала",
            "criteria": [
                f"Решено 20+ задач",
                f"Пройдены темы недели",
                f"Средний балл на тестах > 70%"
            ]
        },
        "skill": {
            "title": f"Оценка прогресса - День {day_num}",
            "description": "Проверка развития навыка",
            "criteria": [
                f"Выполнен мини-проект",
                f"Освоены базовые техники",
                f"Получена обратная связь"
            ]
        },
        "habit": {
            "title": f"Закрепление привычки - День {day_num}",
            "description": "Оценка формирования привычки",
            "criteria": [
                f"Выполнено {day_num} дней подряд",
                f"Нет пропусков более 1 дня",
                f"Привычка становится автоматической"
            ]
        },
        "health": {
            "title": f"Фитнес-оценка - День {day_num}",
            "description": "Измерение физического прогресса",
            "criteria": [
                f"Выполнены все тренировки недели",
                f"Соблюден режим восстановления",
                f"Улучшены показатели"
            ]
        },
        "time": {
            "title": f"Аудит времени - День {day_num}",
            "description": "Анализ эффективности управления временем",
            "criteria": [
                f"Выполнено 80% запланированного",
                f"Сокращены отвлечения",
                f"Оптимизированы процессы"
            ]
        }
    }
    
    template = checkpoint_templates.get(category, checkpoint_templates["exam"])
    
    return Checkpoint(
        id=str(uuid.uuid4()),
        day_number=day_num,
        title=template["title"],
        description=template["description"],
        criteria=template["criteria"],
        status=TaskStatus.PENDING
    )


# ============= ТЕСТ-ХЕЛПЕР ДЛЯ ПРОВЕРКИ =============

if __name__ == "__main__":
    import asyncio
    
    async def test_plan_generator():
        """Тестовая функция для проверки генератора планов"""
        
        # Пример входных данных
        test_answers = {
            "goal_type": "exam",
            "exam_name": "ЕГЭ по математике",
            "exam_date": "2024-06-15",
            "current_level": 65,
            "target_score": 85,
            "weak_topics": ["Тригонометрия", "Параметры"]
        }
        
        test_constraints = {
            "daily_minutes": 120,  # 2 часа в день
            "no_study_after": "21:00",  # Не заниматься после 21:00
            "blackout": ["Fri evening", "Sat evening"],  # Пятница и суббота вечером заняты
            "weekdays_only": False,  # Можно заниматься и в выходные
            "working_days": [1, 2, 3, 4, 5, 6, 7]
        }
        
        # Тестируем разные категории
        categories = ["exam", "skill", "habit", "health", "time"]
        
        for category in categories:
            print(f"\n{'='*60}")
            print(f"Тестирование категории: {category.upper()}")
            print(f"{'='*60}\n")
            
            # Генерируем план
            plan = await generate_plan(
                category=category,
                answers=test_answers,
                constraints=test_constraints,
                horizon_days=15
            )
            
            # Выводим информацию о плане
            print(f"Тип плана: {plan.type}")
            print(f"Горизонт: {plan.horizon_days} дней")
            print(f"Всего задач: {len(plan.days)}")
            print(f"Чекпоинтов: {len(plan.checkpoints)}")
            print(f"Буферных дней: {len(plan.buffer_days)}")
            
            # Показываем первые 3 дня
            print(f"\nПервые 3 дня плана:")
            print("-" * 40)
            
            for day_num in range(1, 4):
                day_tasks = [task for task in plan.days if task.day_number == day_num]
                if day_tasks:
                    print(f"\nДень {day_num}:")
                    for task in day_tasks:
                        print(f"  • {task.title}")
                        print(f"    {task.description}")
                        print(f"    Длительность: {task.duration_minutes} мин")
            
            # Показываем чекпоинты
            if plan.checkpoints:
                print(f"\nЧекпоинты:")
                print("-" * 40)
                for cp in plan.checkpoints[:2]:
                    print(f"День {cp.day_number}: {cp.title}")
                    for criterion in cp.criteria:
                        print(f"  - {criterion}")
            
            # Проверяем соблюдение ограничений
            print(f"\nПроверка ограничений:")
            print("-" * 40)
            
            # Проверяем daily_minutes
            for day_num in range(1, 8):
                day_tasks = [task for task in plan.days if task.day_number == day_num]
                total_minutes = sum(task.duration_minutes for task in day_tasks)
                print(f"День {day_num}: {total_minutes} минут (лимит: {test_constraints['daily_minutes']})")
                
                if total_minutes > test_constraints['daily_minutes']:
                    print(f"  ⚠️  ПРЕВЫШЕН ЛИМИТ!")
    
    def test_json_recovery():
        """Тестирование функции parse_or_fix_json"""
        
        # Тестовые случаи
        test_cases = [
            # Тест 1: JSON с многоточием и запятой (проблема из задания)
            {
                'name': 'Многоточие с запятой',
                'input': '{"days": [{"day": 1, "tasks": [{"time": "09:00", "activity": "Задача 1"}, {"time": "14:00", "activity": "..."}]}, {"day": 2, "tasks": [...,]}]}',
                'should_fix': True
            },
            
            # Тест 2: Некавыченные ключи
            {
                'name': 'Некавыченные ключи',
                'input': '{days: [{day: 1, tasks: [{time: "09:00", activity: "Test"}]}]}',
                'should_fix': True
            },
            
            # Тест 3: Trailing commas
            {
                'name': 'Trailing commas',
                'input': '{"days": [{"day": 1, "tasks": [{"time": "09:00", "activity": "Test"},],},]}',
                'should_fix': True
            },
            
            # Тест 4: Незакрытые скобки
            {
                'name': 'Незакрытые скобки',
                'input': '{"days": [{"day": 1, "tasks": [{"time": "09:00", "activity": "Test"}]',
                'should_fix': True
            },
            
            # Тест 5: Умные кавычки
            {
                'name': 'Умные кавычки',
                'input': '{"days": [{"day": 1, "tasks": [{"time": "09:00", "activity": "Задача"}]}]}',
                'should_fix': True
            },
            
            # Тест 6: Markdown обертка
            {
                'name': 'Markdown JSON блок',
                'input': '```json\n{"days": [{"day": 1, "tasks": [{"time": "09:00", "activity": "Test"}]}]}\n```',
                'should_fix': True
            },
            
            # Тест 7: Валидный JSON
            {
                'name': 'Валидный JSON',
                'input': '{"days": [{"day": 1, "tasks": [{"time": "09:00", "activity": "Задача 1"}]}]}',
                'should_fix': False
            },
            
            # Тест 8: Специфичная проблема из задания
            {
                'name': 'Expecting property name (line 67 column 7)',
                'input': '''{"days": [
                    {"day": 1, "tasks": [{"time": "09:00", "activity": "Утренняя медитация"}, {"time": "14:00", "activity": "Работа над проектом"}]},
                    {"day": 2, "tasks": [{"time": "09:00", "activity": "Чтение книги"}, {"time": "15:00", "activity": "..."},]},
                    {"day": 3, "tasks": [
                        {"time": "10:00", "activity": "Планирование дня"},
                        ...,
                    ]}
                ]}''',
                'should_fix': True
            }
        ]
        
        passed = 0
        failed = 0
        
        for test in test_cases:
            print(f"\n{'='*40}")
            print(f"Тест: {test['name']}")
            print(f"{'='*40}")
            print(f"Входные данные (первые 100 символов): {test['input'][:100]}...")
            
            try:
                result = parse_or_fix_json(test['input'])
                
                # Проверяем, что результат - валидный словарь
                if isinstance(result, dict) and 'days' in result:
                    print(f"✅ УСПЕХ: JSON успешно {'восстановлен' if test['should_fix'] else 'распарсен'}")
                    print(f"   Получено дней: {len(result.get('days', []))}")
                    
                    # Дополнительная валидация
                    validation_error = validate_plan_json(result)
                    if validation_error:
                        print(f"⚠️  Предупреждение при валидации: {validation_error}")
                    else:
                        print(f"   Валидация пройдена успешно")
                    
                    passed += 1
                else:
                    print(f"❌ ПРОВАЛ: Результат не является валидным планом")
                    failed += 1
                    
            except Exception as e:
                print(f"❌ ПРОВАЛ: {str(e)}")
                failed += 1
        
        print(f"\n{'='*60}")
        print(f"ИТОГИ ТЕСТИРОВАНИЯ parse_or_fix_json:")
        print(f"✅ Успешно: {passed}/{len(test_cases)}")
        print(f"❌ Провалено: {failed}/{len(test_cases)}")
        print(f"{'='*60}")
        
        return passed == len(test_cases)
    
    # Запускаем тест
    asyncio.run(test_plan_generator())
    
    print("\n" + "="*60)
    print("Тестирование завершено!")
    print("="*60)
    
    # Добавляем тестирование parse_or_fix_json
    print("\n" + "="*60)
    print("ТЕСТИРОВАНИЕ parse_or_fix_json")
    print("="*60)
    
    test_json_recovery()