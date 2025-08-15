"""
Примеры использования моделей профиля ИИ-ассистента
"""
from datetime import datetime, date, timedelta
from typing import Dict, Any
import uuid

from models.ai_profile import (
    AIProfile, CategoryType, ThemeType, TaskStatus,
    DayTask, Checkpoint, BufferDay,
    OnboardingData, PlanData, ConstraintsData,
    RiskItem, ProgressData, PreferencesData,
    ExamOnboardingAnswers, SkillOnboardingAnswers,
    HabitOnboardingAnswers, HealthOnboardingAnswers,
    TimeOnboardingAnswers
)
from models.ai_constraints import (
    ExamConstraints, SkillConstraints, HabitConstraints,
    HealthConstraints, TimeConstraints,
    TimeSlot, EnergyLevel, Commitment
)


def create_exam_profile_example() -> AIProfile:
    """Пример профиля для подготовки к экзамену"""
    
    # Онбординг для экзамена
    exam_answers = ExamOnboardingAnswers(
        exam_name="ЕГЭ по математике",
        exam_date=date.today() + timedelta(days=30),
        current_level=65,
        target_score=85,
        study_materials=["Учебник Мордковича", "Сборник задач ФИПИ"],
        weak_topics=["Тригонометрия", "Параметры"]
    )
    
    onboarding = OnboardingData(
        completed=True,
        answers=exam_answers.dict(),
        completed_at=datetime.now()
    )
    
    # План подготовки
    days = [
        DayTask(
            id=str(uuid.uuid4()),
            day_number=1,
            title="Диагностический тест",
            description="Решить полный вариант ЕГЭ для оценки уровня",
            duration_minutes=180,
            priority=1,
            status=TaskStatus.PENDING
        ),
        DayTask(
            id=str(uuid.uuid4()),
            day_number=2,
            title="Тригонометрия: основы",
            description="Повторить основные формулы и тождества",
            duration_minutes=90,
            priority=1,
            status=TaskStatus.PENDING
        )
    ]
    
    checkpoints = [
        Checkpoint(
            id=str(uuid.uuid4()),
            day_number=7,
            title="Неделя 1: Базовые темы",
            description="Проверка усвоения базовых тем",
            criteria=[
                "Решено 50+ задач",
                "Пройдены все базовые темы",
                "Средний балл на тестах > 70%"
            ],
            status=TaskStatus.PENDING
        )
    ]
    
    buffer_days = [
        BufferDay(
            day_number=8,
            reason="Восстановление после интенсивной недели",
            activities=["Легкое повторение", "Просмотр видео-разборов"]
        )
    ]
    
    plan = PlanData(
        type=CategoryType.EXAM,
        horizon_days=30,
        days=days,
        checkpoints=checkpoints,
        buffer_days=buffer_days
    )
    
    # Ограничения
    exam_constraints = ExamConstraints(
        exam_date=date.today() + timedelta(days=30),
        study_hours_per_day=3,
        break_days=[],
        preferred_study_time="вечер",
        max_session_minutes=90,
        min_break_minutes=15,
        blocked_topics_per_day=2
    )
    
    constraints = ConstraintsData(
        daily_time_minutes=180,
        working_days=[1, 2, 3, 4, 5, 6],
        exam_constraints=exam_constraints.dict()
    )
    
    # Риски
    risks = [
        RiskItem(
            id=str(uuid.uuid4()),
            title="Выгорание от интенсивной подготовки",
            probability=0.4,
            impact=4,
            mitigation="Регулярные дни отдыха и смена активности",
            category="mental_health"
        ),
        RiskItem(
            id=str(uuid.uuid4()),
            title="Недостаточно времени на сложные темы",
            probability=0.3,
            impact=3,
            mitigation="Приоритизация сложных тем в начале подготовки",
            category="planning"
        )
    ]
    
    # Создание профиля
    profile = AIProfile(
        active_category=CategoryType.EXAM,
        onboarding=onboarding,
        plan=plan,
        constraints=constraints,
        risks=risks,
        progress=ProgressData(days_done=0, completion_rate=0.0),
        preferences=PreferencesData(
            theme=ThemeType.LIGHT,
            notifications_enabled=True,
            reminder_time="19:00",
            language="ru"
        )
    )
    
    return profile


def create_habit_profile_example() -> AIProfile:
    """Пример профиля для формирования привычки"""
    
    # Онбординг для привычки
    habit_answers = HabitOnboardingAnswers(
        habit_name="Медитация",
        habit_type="создать",
        current_frequency="никогда",
        target_frequency="ежедневно",
        triggers=["После пробуждения", "Перед сном"],
        obstacles=["Забываю", "Нет времени", "Отвлекаюсь"]
    )
    
    onboarding = OnboardingData(
        completed=True,
        answers=habit_answers.dict()
    )
    
    # План формирования привычки (21 день)
    days = []
    for i in range(1, 22):
        days.append(DayTask(
            id=str(uuid.uuid4()),
            day_number=i,
            title=f"Медитация день {i}",
            description="5 минут медитации" if i <= 7 else "10 минут медитации",
            duration_minutes=5 if i <= 7 else 10,
            priority=1,
            status=TaskStatus.PENDING
        ))
    
    checkpoints = [
        Checkpoint(
            id=str(uuid.uuid4()),
            day_number=7,
            title="Первая неделя",
            description="Закрепление базовой практики",
            criteria=["Выполнено 6 из 7 дней", "Комфортно с 5-минутной практикой"],
            status=TaskStatus.PENDING
        ),
        Checkpoint(
            id=str(uuid.uuid4()),
            day_number=21,
            title="Привычка сформирована",
            description="21 день регулярной практики",
            criteria=["Выполнено минимум 18 из 21 дня", "Медитация стала естественной"],
            status=TaskStatus.PENDING
        )
    ]
    
    plan = PlanData(
        type=CategoryType.HABIT,
        horizon_days=21,
        days=days,
        checkpoints=checkpoints
    )
    
    # Ограничения для привычки
    habit_constraints = HabitConstraints(
        start_small=True,
        initial_frequency="daily",
        reminder_times=["07:00", "22:00"],
        max_skip_days=1,
        environmental_changes=["Подготовить место для медитации", "Установить приложение"]
    )
    
    constraints = ConstraintsData(
        daily_time_minutes=10,
        habit_constraints=habit_constraints.dict()
    )
    
    return AIProfile(
        active_category=CategoryType.HABIT,
        onboarding=onboarding,
        plan=plan,
        constraints=constraints
    )


def profile_to_firestore_example():
    """Пример сохранения профиля в Firestore"""
    profile = create_exam_profile_example()
    
    # Преобразование в формат Firestore
    firestore_data = profile.to_firestore()
    
    # Пример сохранения (псевдокод)
    # db.collection('users').document(telegram_id).set({
    #     'ai_profile': firestore_data
    # })
    
    return firestore_data


def profile_from_firestore_example(data: Dict[str, Any]) -> AIProfile:
    """Пример загрузки профиля из Firestore"""
    # Преобразование данных из Firestore
    profile = AIProfile.from_firestore(data)
    return profile


def update_progress_example(profile: AIProfile):
    """Пример обновления прогресса"""
    # Отметить задачу как выполненную
    if profile.plan and profile.plan.days:
        first_task = profile.plan.days[0]
        first_task.status = TaskStatus.COMPLETED
        first_task.completed_at = datetime.now()
        
        # Обновить общий прогресс
        profile.progress.days_done += 1
        profile.progress.last_checkin = datetime.now()
        profile.progress.streak_current += 1
        
        # Пересчитать процент выполнения
        total_days = len(profile.plan.days)
        completed_days = sum(1 for day in profile.plan.days if day.status == TaskStatus.COMPLETED)
        profile.progress.completion_rate = completed_days / total_days if total_days > 0 else 0
    
    return profile


# Примеры запросов к Firestore
def firestore_queries_examples():
    """Примеры запросов для работы с профилями"""
    
    # 1. Получить профиль пользователя
    # profile_doc = db.collection('users').document(telegram_id).get()
    # if profile_doc.exists:
    #     ai_profile_data = profile_doc.to_dict().get('ai_profile')
    #     profile = AIProfile.from_firestore(ai_profile_data)
    
    # 2. Обновить только прогресс
    # db.collection('users').document(telegram_id).update({
    #     'ai_profile.progress': profile.progress.dict()
    # })
    
    # 3. Добавить новую задачу в план
    # new_task = DayTask(...)
    # db.collection('users').document(telegram_id).update({
    #     'ai_profile.plan.days': firestore.ArrayUnion([new_task.dict()])
    # })
    
    # 4. Получить всех пользователей с активным планом экзамена
    # users = db.collection('users').where('ai_profile.active_category', '==', 'exam').get()
    
    pass


if __name__ == "__main__":
    # Тестирование создания профилей
    exam_profile = create_exam_profile_example()
    print(f"Создан профиль для экзамена: {exam_profile.active_category}")
    print(f"План на {exam_profile.plan.horizon_days} дней")
    print(f"Задач: {len(exam_profile.plan.days)}")
    print(f"Чекпоинтов: {len(exam_profile.plan.checkpoints)}")
    
    # Тестирование преобразования
    firestore_data = exam_profile.to_firestore()
    print(f"\nДанные для Firestore: {list(firestore_data.keys())}")
    
    # Тестирование обратного преобразования
    restored_profile = AIProfile.from_firestore(firestore_data)
    print(f"\nВосстановленный профиль: {restored_profile.active_category}")