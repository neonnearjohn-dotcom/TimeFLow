"""
Модели данных для профиля ИИ-ассистента
"""
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, date
from enum import Enum
from pydantic import BaseModel, Field, validator


# Перечисления для типов
class CategoryType(str, Enum):
    """Типы категорий планирования"""
    EXAM = "exam"           # Подготовка к экзамену
    SKILL = "skill"         # Развитие навыка
    HABIT = "habit"         # Формирование привычки
    HEALTH = "health"       # Здоровье и фитнес
    TIME = "time"           # Тайм-менеджмент


class ThemeType(str, Enum):
    """Типы тем интерфейса"""
    SYSTEM = "system"
    LIGHT = "light"
    DARK = "dark"


class TaskStatus(str, Enum):
    """Статус выполнения задачи"""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


# DTO для элементов плана
class DayTask(BaseModel):
    """Задача на день"""
    id: str = Field(..., description="Уникальный ID задачи")
    day_number: int = Field(..., ge=1, description="Номер дня в плане")
    title: str = Field(..., description="Название задачи")
    description: Optional[str] = Field(None, description="Описание задачи")
    duration_minutes: Optional[int] = Field(None, ge=1, description="Длительность в минутах")
    priority: int = Field(1, ge=1, le=3, description="Приоритет: 1-высокий, 2-средний, 3-низкий")
    status: TaskStatus = Field(TaskStatus.PENDING, description="Статус выполнения")
    completed_at: Optional[datetime] = Field(None, description="Время выполнения")
    notes: Optional[str] = Field(None, description="Заметки пользователя")
    
    class Config:
        use_enum_values = True


class Checkpoint(BaseModel):
    """Контрольная точка плана"""
    id: str = Field(..., description="Уникальный ID чекпоинта")
    day_number: int = Field(..., ge=1, description="День чекпоинта")
    title: str = Field(..., description="Название чекпоинта")
    description: Optional[str] = Field(None, description="Описание")
    criteria: List[str] = Field(default_factory=list, description="Критерии успеха")
    status: TaskStatus = Field(TaskStatus.PENDING, description="Статус")
    achieved_at: Optional[datetime] = Field(None, description="Время достижения")
    feedback: Optional[str] = Field(None, description="Обратная связь от ИИ")
    
    class Config:
        use_enum_values = True


class BufferDay(BaseModel):
    """Буферный день для восстановления"""
    day_number: int = Field(..., ge=1, description="Номер дня")
    reason: str = Field(..., description="Причина буферного дня")
    activities: List[str] = Field(default_factory=list, description="Рекомендуемые активности")


# Основные компоненты профиля
class OnboardingData(BaseModel):
    """Данные онбординга"""
    completed: bool = Field(False, description="Завершен ли онбординг")
    answers: Dict[str, Any] = Field(default_factory=dict, description="Ответы на вопросы")
    completed_at: Optional[datetime] = Field(None, description="Время завершения")
    
    # Типизированные ответы для разных категорий
    @validator('answers')
    def validate_answers(cls, v):
        """Валидация ответов в зависимости от категории"""
        # Здесь можно добавить специфичную валидацию
        return v


class PlanData(BaseModel):
    """План пользователя"""
    type: CategoryType = Field(..., description="Тип плана")
    horizon_days: int = Field(15, ge=7, le=90, description="Горизонт планирования в днях")
    days: List[DayTask] = Field(default_factory=list, description="Задачи по дням")
    checkpoints: List[Checkpoint] = Field(default_factory=list, description="Контрольные точки")
    buffer_days: List[BufferDay] = Field(default_factory=list, description="Буферные дни")
    created_at: datetime = Field(default_factory=datetime.now, description="Дата создания плана")
    updated_at: datetime = Field(default_factory=datetime.now, description="Дата обновления")
    
    class Config:
        use_enum_values = True
    
    @validator('checkpoints')
    def validate_checkpoints(cls, v, values):
        """Проверка, что чекпоинты в пределах горизонта"""
        if 'horizon_days' in values:
            for checkpoint in v:
                if checkpoint.day_number > values['horizon_days']:
                    raise ValueError(f"Чекпоинт на день {checkpoint.day_number} выходит за горизонт плана")
        return v


class ConstraintsData(BaseModel):
    """Ограничения пользователя"""
    # Общие ограничения
    daily_time_minutes: Optional[int] = Field(None, ge=15, le=480, description="Доступное время в день (минуты)")
    working_days: List[int] = Field(default_factory=lambda: [1,2,3,4,5], description="Рабочие дни недели (1-7)")
    
    # Категория-специфичные ограничения
    exam_constraints: Optional[Dict[str, Any]] = Field(None, description="Ограничения для экзаменов")
    skill_constraints: Optional[Dict[str, Any]] = Field(None, description="Ограничения для навыков")
    habit_constraints: Optional[Dict[str, Any]] = Field(None, description="Ограничения для привычек")
    health_constraints: Optional[Dict[str, Any]] = Field(None, description="Ограничения для здоровья")
    time_constraints: Optional[Dict[str, Any]] = Field(None, description="Ограничения для времени")


class RiskItem(BaseModel):
    """Элемент риска"""
    id: str = Field(..., description="ID риска")
    title: str = Field(..., description="Название риска")
    probability: float = Field(..., ge=0, le=1, description="Вероятность (0-1)")
    impact: int = Field(..., ge=1, le=5, description="Влияние (1-5)")
    mitigation: str = Field(..., description="План митигации")
    category: Optional[str] = Field(None, description="Категория риска")


class ProgressData(BaseModel):
    """Данные о прогрессе"""
    days_done: int = Field(0, ge=0, description="Выполнено дней")
    last_checkin: Optional[datetime] = Field(None, description="Последняя отметка")
    fail_reasons: List[str] = Field(default_factory=list, description="Причины неудач")
    streak_current: int = Field(0, ge=0, description="Текущая серия")
    streak_best: int = Field(0, ge=0, description="Лучшая серия")
    completion_rate: float = Field(0.0, ge=0, le=1, description="Процент выполнения")
    
    @validator('completion_rate')
    def validate_completion_rate(cls, v):
        """Округление процента выполнения"""
        return round(v, 2)


class PreferencesData(BaseModel):
    """Предпочтения пользователя"""
    theme: ThemeType = Field(ThemeType.SYSTEM, description="Тема интерфейса")
    notifications_enabled: bool = Field(True, description="Включены ли уведомления")
    reminder_time: Optional[str] = Field(None, pattern="^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$", description="Время напоминания (HH:MM)")
    language: str = Field("ru", description="Язык интерфейса")
    
    class Config:
        use_enum_values = True


# Главная модель профиля
class AIProfile(BaseModel):
    """Полный профиль ИИ-ассистента"""
    active_category: Optional[CategoryType] = Field(None, description="Активная категория")
    onboarding: OnboardingData = Field(default_factory=OnboardingData, description="Данные онбординга")
    plan: Optional[PlanData] = Field(None, description="Текущий план")
    constraints: ConstraintsData = Field(default_factory=ConstraintsData, description="Ограничения")
    risks: List[RiskItem] = Field(default_factory=list, description="Идентифицированные риски")
    progress: ProgressData = Field(default_factory=ProgressData, description="Прогресс выполнения")
    preferences: PreferencesData = Field(default_factory=PreferencesData, description="Предпочтения")
    created_at: datetime = Field(default_factory=datetime.now, description="Дата создания профиля")
    updated_at: datetime = Field(default_factory=datetime.now, description="Дата обновления")
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    def to_firestore(self) -> Dict[str, Any]:
        """Преобразование в формат для Firestore"""
        data = self.dict()
        # Преобразуем datetime в timestamp для Firestore
        def convert_datetime(obj):
            if isinstance(obj, dict):
                return {k: convert_datetime(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_datetime(item) for item in obj]
            elif isinstance(obj, datetime):
                return obj
            return obj
        
        return convert_datetime(data)
    
    @classmethod
    def from_firestore(cls, data: Dict[str, Any]) -> 'AIProfile':
        """Создание из данных Firestore"""
        return cls(**data)


# Типы для специфичных ответов онбординга
class ExamOnboardingAnswers(BaseModel):
    """Ответы онбординга для экзамена"""
    exam_name: str = Field(..., description="Название экзамена")
    exam_date: date = Field(..., description="Дата экзамена")
    current_level: int = Field(..., ge=0, le=100, description="Текущий уровень подготовки %")
    target_score: Optional[int] = Field(None, description="Целевой балл")
    study_materials: List[str] = Field(default_factory=list, description="Учебные материалы")
    weak_topics: List[str] = Field(default_factory=list, description="Слабые темы")


class SkillOnboardingAnswers(BaseModel):
    """Ответы онбординга для навыка"""
    skill_name: str = Field(..., description="Название навыка")
    current_level: str = Field(..., description="Текущий уровень (новичок/средний/продвинутый)")
    goal_description: str = Field(..., description="Описание цели")
    practice_frequency: str = Field(..., description="Частота практики")
    available_resources: List[str] = Field(default_factory=list, description="Доступные ресурсы")


class HabitOnboardingAnswers(BaseModel):
    """Ответы онбординга для привычки"""
    habit_name: str = Field(..., description="Название привычки")
    habit_type: str = Field(..., description="Тип (создать/избавиться)")
    current_frequency: Optional[str] = Field(None, description="Текущая частота")
    target_frequency: str = Field(..., description="Целевая частота")
    triggers: List[str] = Field(default_factory=list, description="Триггеры")
    obstacles: List[str] = Field(default_factory=list, description="Препятствия")


class HealthOnboardingAnswers(BaseModel):
    """Ответы онбординга для здоровья"""
    health_goal: str = Field(..., description="Цель по здоровью")
    current_metrics: Dict[str, float] = Field(default_factory=dict, description="Текущие метрики")
    target_metrics: Dict[str, float] = Field(default_factory=dict, description="Целевые метрики")
    limitations: List[str] = Field(default_factory=list, description="Ограничения по здоровью")
    preferred_activities: List[str] = Field(default_factory=list, description="Предпочитаемые активности")


class TimeOnboardingAnswers(BaseModel):
    """Ответы онбординга для тайм-менеджмента"""
    main_time_wasters: List[str] = Field(default_factory=list, description="Основные поглотители времени")
    priority_areas: List[str] = Field(default_factory=list, description="Приоритетные области")
    work_schedule: Dict[str, str] = Field(default_factory=dict, description="Рабочий график")
    energy_peaks: List[str] = Field(default_factory=list, description="Пики энергии")
    desired_balance: Dict[str, int] = Field(default_factory=dict, description="Желаемый баланс времени")


# Union тип для всех возможных ответов онбординга
OnboardingAnswersType = Union[
    ExamOnboardingAnswers,
    SkillOnboardingAnswers,
    HabitOnboardingAnswers,
    HealthOnboardingAnswers,
    TimeOnboardingAnswers,
    Dict[str, Any]  # Для обратной совместимости
]