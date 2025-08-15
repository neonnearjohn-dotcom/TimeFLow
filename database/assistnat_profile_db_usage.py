"""
Примеры использования AssistantProfileDB
"""
import asyncio
from datetime import datetime, date, timedelta, timezone
from typing import Dict, Any
import uuid

# Импорт базы данных
from database.firestore_db import FirestoreDB
from database.assistant_profile_db import AssistantProfileDB

# Импорт моделей
from models.ai_profile import (
    AIProfile, CategoryType, DayTask, Checkpoint,
    TaskStatus, ThemeType
)


async def example_onboarding_flow(profile_db: AssistantProfileDB, telegram_id: int):
    """Пример процесса онбординга"""
    
    print(f"=== Пример онбординга для пользователя {telegram_id} ===")
    
    # 1. Создаем профиль если его нет
    profile = await profile_db.get_profile(telegram_id)
    if not profile:
        await profile_db.create_profile(telegram_id)
        print("✓ Создан новый профиль")
    
    # 2. Сохраняем ответы по одному
    await profile_db.save_onboarding_answer(telegram_id, "goal_type", "exam")
    print("✓ Сохранен тип цели")
    
    await profile_db.save_onboarding_answer(telegram_id, "exam_name", "ЕГЭ по математике")
    print("✓ Сохранено название экзамена")
    
    await profile_db.save_onboarding_answer(telegram_id, "exam_date", "2024-06-15")
    print("✓ Сохранена дата экзамена")
    
    await profile_db.save_onboarding_answer(telegram_id, "current_level", 65)
    print("✓ Сохранен текущий уровень")
    
    # 3. Завершаем онбординг
    answers = {
        "goal_type": "exam",
        "exam_name": "ЕГЭ по математике",
        "exam_date": "2024-06-15",
        "current_level": 65,
        "target_score": 85,
        "study_materials": ["Учебник Мордковича", "Сборник ФИПИ"],
        "weak_topics": ["Тригонометрия", "Параметры"]
    }
    
    constraints = {
        "daily_time_minutes": 180,
        "working_days": [1, 2, 3, 4, 5, 6],
        "study_hours_per_day": 3,
        "preferred_study_time": "evening",
        "max_session_minutes": 90
    }
    
    success = await profile_db.finalize_onboarding(
        telegram_id, 
        "exam", 
        answers, 
        constraints
    )
    
    if success:
        print("✓ Онбординг завершен успешно")
    
    return success


async def example_plan_creation(profile_db: AssistantProfileDB, telegram_id: int):
    """Пример создания и сохранения плана"""
    
    print(f"\n=== Создание плана для пользователя {telegram_id} ===")
    
    # Создаем структуру плана
    plan = {
        "type": "exam",
        "horizon_days": 30,
        "days": [
            {
                "id": str(uuid.uuid4()),
                "day_number": 1,
                "title": "Диагностический тест",
                "description": "Решить полный вариант ЕГЭ",
                "duration_minutes": 180,
                "priority": 1,
                "status": "pending"
            },
            {
                "id": str(uuid.uuid4()),
                "day_number": 2,
                "title": "Анализ результатов",
                "description": "Разобрать ошибки, составить план",
                "duration_minutes": 60,
                "priority": 1,
                "status": "pending"
            },
            {
                "id": str(uuid.uuid4()),
                "day_number": 3,
                "title": "Тригонометрия: базовые формулы",
                "description": "Повторить основные тригонометрические формулы",
                "duration_minutes": 90,
                "priority": 1,
                "status": "pending"
            }
        ],
        "checkpoints": [
            {
                "id": str(uuid.uuid4()),
                "day_number": 7,
                "title": "Неделя 1: Базовые темы",
                "description": "Проверка усвоения базовых тем",
                "criteria": [
                    "Решено 50+ задач",
                    "Пройдены базовые темы",
                    "Средний балл > 70%"
                ],
                "status": "pending"
            }
        ],
        "buffer_days": [
            {
                "day_number": 8,
                "reason": "Восстановление",
                "activities": ["Легкое повторение", "Просмотр видео"]
            }
        ]
    }
    
    # Сохраняем план
    success = await profile_db.save_plan(telegram_id, plan)
    
    if success:
        print("✓ План успешно сохранен")
        print(f"  - Дней: {len(plan['days'])}")
        print(f"  - Чекпоинтов: {len(plan['checkpoints'])}")
        print(f"  - Буферных дней: {len(plan['buffer_days'])}")
    
    return plan


async def example_progress_update(profile_db: AssistantProfileDB, telegram_id: int):
    """Пример обновления прогресса"""
    
    print(f"\n=== Обновление прогресса для пользователя {telegram_id} ===")
    
    # 1. Простое обновление полей
    await profile_db.update_progress(telegram_id, {
        "days_done": 3,
        "completion_rate": 0.1,
        "streak_current": 3
    })
    print("✓ Обновлены базовые поля прогресса")
    
    # 2. Инкрементальное обновление
    await profile_db.update_progress(telegram_id, {
        "increment_days_done": 1,
        "increment_streak": 1
    })
    print("✓ Инкрементально обновлены счетчики")
    
    # 3. Добавление причины неудачи
    await profile_db.update_progress(telegram_id, {
        "add_fail_reason": "Не хватило времени на выполнение"
    })
    print("✓ Добавлена причина пропуска")
    
    # 4. Обновление нескольких полей
    await profile_db.update_progress(telegram_id, {
        "completion_rate": 0.15,
        "streak_best": 4,
        "last_checkin": datetime.now(timezone.utc)
    })
    print("✓ Обновлено несколько полей прогресса")


async def example_task_management(profile_db: AssistantProfileDB, telegram_id: int):
    """Пример работы с задачами"""
    
    print(f"\n=== Управление задачами для пользователя {telegram_id} ===")
    
    # Получаем профиль
    profile = await profile_db.get_profile(telegram_id)
    if not profile or not profile.plan:
        print("❌ Профиль или план не найден")
        return
    
    # Берем первую задачу
    if profile.plan.days:
        first_task = profile.plan.days[0]
        task_id = first_task.id
        
        # Обновляем статус задачи
        success = await profile_db.update_task_status(
            telegram_id,
            task_id,
            "completed",
            "Выполнено успешно, все тесты решены"
        )
        
        if success:
            print(f"✓ Задача {first_task.title} отмечена как выполненная")


async def example_preferences_update(profile_db: AssistantProfileDB, telegram_id: int):
    """Пример обновления предпочтений"""
    
    print(f"\n=== Обновление предпочтений для пользователя {telegram_id} ===")
    
    preferences = {
        "theme": "dark",
        "notifications_enabled": True,
        "reminder_time": "19:00",
        "language": "ru"
    }
    
    success = await profile_db.update_preferences(telegram_id, preferences)
    
    if success:
        print("✓ Предпочтения обновлены")
        for key, value in preferences.items():
            print(f"  - {key}: {value}")


async def example_risk_management(profile_db: AssistantProfileDB, telegram_id: int):
    """Пример работы с рисками"""
    
    print(f"\n=== Управление рисками для пользователя {telegram_id} ===")
    
    risk = {
        "id": str(uuid.uuid4()),
        "title": "Выгорание от интенсивной подготовки",
        "probability": 0.4,
        "impact": 4,
        "mitigation": "Регулярные перерывы и смена деятельности",
        "category": "mental_health"
    }
    
    success = await profile_db.add_risk(telegram_id, risk)
    
    if success:
        print("✓ Риск добавлен в профиль")
        print(f"  - {risk['title']}")
        print(f"  - Вероятность: {risk['probability']}")
        print(f"  - Влияние: {risk['impact']}/5")


async def example_full_flow():
    """Полный пример работы с профилем"""
    
    # Инициализация
    db = FirestoreDB()
    profile_db = AssistantProfileDB(db.db)
    
    telegram_id = 123456789  # Тестовый ID
    
    try:
        # 1. Онбординг
        await example_onboarding_flow(profile_db, telegram_id)
        
        # 2. Создание плана
        await example_plan_creation(profile_db, telegram_id)
        
        # 3. Обновление прогресса
        await example_progress_update(profile_db, telegram_id)
        
        # 4. Управление задачами
        await example_task_management(profile_db, telegram_id)
        
        # 5. Обновление предпочтений
        await example_preferences_update(profile_db, telegram_id)
        
        # 6. Добавление рисков
        await example_risk_management(profile_db, telegram_id)
        
        # 7. Финальная проверка
        print("\n=== Финальная проверка профиля ===")
        final_profile = await profile_db.get_profile(telegram_id)
        
        if final_profile:
            print("✓ Профиль успешно загружен")
            print(f"  - Категория: {final_profile.active_category}")
            print(f"  - Онбординг завершен: {final_profile.onboarding.completed}")
            print(f"  - Дней в плане: {len(final_profile.plan.days) if final_profile.plan else 0}")
            print(f"  - Прогресс: {final_profile.progress.days_done} дней")
            print(f"  - Тема: {final_profile.preferences.theme}")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")


# Интеграция с существующими handlers
async def integration_example():
    """Пример интеграции с handlers бота"""
    
    # В handlers/assistant.py можно использовать так:
    
    # from database.firestore_db import FirestoreDB
    # from database.assistant_profile_db import AssistantProfileDB
    
    # db = FirestoreDB()
    # profile_db = AssistantProfileDB(db.db)
    
    # @router.callback_query(F.data == "start_ai_onboarding")
    # async def start_onboarding(callback: CallbackQuery):
    #     telegram_id = callback.from_user.id
    #     
    #     # Создаем профиль если нужно
    #     profile = await profile_db.get_profile(telegram_id)
    #     if not profile:
    #         await profile_db.create_profile(telegram_id)
    #     
    #     # Начинаем онбординг...
    
    pass


if __name__ == "__main__":
    # Запуск примеров
    asyncio.run(example_full_flow())