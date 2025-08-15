# Интеграция модуля AssistantProfileDB

## 📋 Обзор

Модуль `AssistantProfileDB` предоставляет полный функционал для работы с профилями ИИ-ассистента в Firestore.

## 🚀 Быстрый старт

### 1. Инициализация

```python
from database.firestore_db import FirestoreDB
from database.assistant_profile_db import AssistantProfileDB

# В начале вашего handler файла
db = FirestoreDB()
profile_db = AssistantProfileDB(db.db)
```

### 2. Основные операции

#### Получение профиля
```python
profile = await profile_db.get_profile(telegram_id)
if not profile:
    # Профиль не существует
    await profile_db.create_profile(telegram_id)
```

#### Процесс онбординга
```python
# Сохранение ответов по одному
await profile_db.save_onboarding_answer(telegram_id, "goal_type", "exam")
await profile_db.save_onboarding_answer(telegram_id, "exam_name", "ЕГЭ")

# Завершение онбординга
answers = {
    "goal_type": "exam",
    "exam_name": "ЕГЭ по математике",
    "exam_date": "2024-06-15",
    "current_level": 65
}

constraints = {
    "daily_time_minutes": 180,
    "study_hours_per_day": 3
}

await profile_db.finalize_onboarding(telegram_id, "exam", answers, constraints)
```

#### Работа с планом
```python
# Сохранение плана
plan = {
    "type": "exam",
    "horizon_days": 30,
    "days": [...],
    "checkpoints": [...],
    "buffer_days": [...]
}

await profile_db.save_plan(telegram_id, plan)
```

#### Обновление прогресса
```python
# Простое обновление
await profile_db.update_progress(telegram_id, {
    "days_done": 5,
    "completion_rate": 0.17
})

# Инкрементальное обновление
await profile_db.update_progress(telegram_id, {
    "increment_days_done": 1,
    "increment_streak": 1
})

# Добавление причины неудачи
await profile_db.update_progress(telegram_id, {
    "add_fail_reason": "Болезнь"
})
```

## 📁 Структура документа в Firestore

```javascript
users/{telegram_id}: {
    ai_profile: {
        active_category: "exam|skill|habit|health|time",
        onboarding: {
            completed: boolean,
            answers: {},
            completed_at: timestamp
        },
        plan: {
            type: string,
            horizon_days: number,
            days: [],
            checkpoints: [],
            buffer_days: [],
            created_at: timestamp,
            updated_at: timestamp
        },
        constraints: {
            daily_time_minutes: number,
            working_days: [],
            exam_constraints: {},
            skill_constraints: {},
            // etc...
        },
        risks: [],
        progress: {
            days_done: number,
            last_checkin: timestamp,
            fail_reasons: [],
            streak_current: number,
            streak_best: number,
            completion_rate: number
        },
        preferences: {
            theme: "system|light|dark",
            notifications_enabled: boolean,
            reminder_time: string,
            language: string
        },
        created_at: timestamp,
        updated_at: timestamp
    },
    updated_at: timestamp
}
```

## 🔌 Интеграция в handlers

### handlers/assistant.py

```python
from database.assistant_profile_db import AssistantProfileDB

# Инициализация
profile_db = AssistantProfileDB(db.db)

@router.callback_query(F.data == "ai_assistant_start")
async def start_ai_assistant(callback: CallbackQuery):
    """Начало работы с ИИ-ассистентом"""
    telegram_id = callback.from_user.id
    
    # Проверяем профиль
    profile = await profile_db.get_profile(telegram_id)
    
    if not profile:
        # Создаем новый профиль и начинаем онбординг
        await profile_db.create_profile(telegram_id)
        await callback.message.edit_text(
            "Добро пожаловать в ИИ-планировщик!",
            reply_markup=get_onboarding_keyboard()
        )
    elif not profile.onboarding.completed:
        # Продолжаем онбординг
        await continue_onboarding(callback, profile)
    elif not profile.plan:
        # Предлагаем создать план
        await suggest_plan_creation(callback, profile)
    else:
        # Показываем текущий прогресс
        await show_current_progress(callback, profile)
```

### handlers/ai_onboarding.py (новый файл)

```python
@router.callback_query(F.data.startswith("ai_onboarding_"))
async def handle_onboarding_answer(callback: CallbackQuery, state: FSMContext):
    """Обработка ответов онбординга"""
    telegram_id = callback.from_user.id
    data = callback.data.split("_")
    question_id = data[2]
    answer = data[3]
    
    # Сохраняем ответ
    await profile_db.save_onboarding_answer(telegram_id, question_id, answer)
    
    # Переходим к следующему вопросу или завершаем
    if question_id == "last_question":
        # Собираем все ответы из state
        data = await state.get_data()
        answers = data.get("onboarding_answers", {})
        
        # Завершаем онбординг
        await profile_db.finalize_onboarding(
            telegram_id,
            answers["goal_type"],
            answers,
            build_constraints(answers)
        )
        
        await state.clear()
        await callback.message.edit_text(
            "Отлично! Теперь создам для вас план.",
            reply_markup=get_plan_creation_keyboard()
        )
```

## 🛠 Вспомогательные функции

### Построение ограничений из ответов

```python
def build_constraints(answers: Dict[str, Any]) -> Dict[str, Any]:
    """Преобразует ответы онбординга в ограничения"""
    category = answers.get("goal_type")
    
    base_constraints = {
        "daily_time_minutes": answers.get("available_time", 60),
        "working_days": answers.get("working_days", [1,2,3,4,5])
    }
    
    if category == "exam":
        base_constraints["exam_constraints"] = {
            "exam_date": answers.get("exam_date"),
            "study_hours_per_day": answers.get("study_hours", 2),
            "preferred_study_time": answers.get("preferred_time", "evening")
        }
    elif category == "habit":
        base_constraints["habit_constraints"] = {
            "start_small": True,
            "initial_frequency": answers.get("frequency", "daily"),
            "reminder_times": answers.get("reminder_times", ["09:00"])
        }
    # ... другие категории
    
    return base_constraints
```

### Форматирование прогресса для отображения

```python
def format_progress(profile: AIProfile) -> str:
    """Форматирует прогресс для отображения пользователю"""
    if not profile.plan:
        return "План еще не создан"
    
    progress = profile.progress
    total_days = profile.plan.horizon_days
    
    return f"""
📊 Ваш прогресс:

Выполнено дней: {progress.days_done}/{total_days}
Прогресс: {progress.completion_rate * 100:.0f}%
Текущая серия: {progress.streak_current} дней
Лучшая серия: {progress.streak_best} дней

Следующая задача: {get_next_task(profile)}
"""
```

## ⚠️ Важные моменты

1. **Избегайте циклических импортов**: Импортируйте модели напрямую, а не через промежуточные модули

2. **Обработка ошибок**: Все методы возвращают `bool` или `Optional`, проверяйте результаты:
```python
success = await profile_db.save_plan(telegram_id, plan)
if not success:
    await callback.answer("Ошибка сохранения плана", show_alert=True)
```

3. **Временные метки**: Модуль автоматически добавляет `updated_at` при любом изменении

4. **Инкрементальные обновления**: Используйте специальные ключи для атомарных операций:
- `increment_days_done` - увеличить счетчик дней
- `increment_streak` - увеличить серию
- `add_fail_reason` - добавить причину в массив

## 📊 Мониторинг и отладка

### Логирование
Модуль использует стандартный logger Python:
```python
logger = logging.getLogger(__name__)
```

Все операции логируются с уровнями:
- `INFO` - успешные операции
- `WARNING` - некритичные проблемы
- `ERROR` - ошибки с stack trace

### Проверка целостности данных
```python
async def validate_profile(telegram_id: int) -> bool:
    """Проверяет целостность профиля"""
    profile = await profile_db.get_profile(telegram_id)
    
    if not profile:
        return False
    
    # Проверки целостности
    if profile.plan:
        # Все задачи должны иметь ID
        for task in profile.plan.days:
            if not task.id:
                logger.error(f"Задача без ID в профиле {telegram_id}")
                return False
    
    return True
```

## 🚦 Готовность к production

- ✅ Все методы асинхронные
- ✅ Обработка ошибок
- ✅ Логирование
- ✅ Типизация (type hints)
- ✅ Документация
- ✅ Примеры использования
- ✅ Совместимость с существующей структурой проекта