"""
Специфичные типы ограничений для каждой категории
"""

from typing import List, Optional, Dict
from datetime import time, date
from pydantic import BaseModel, Field, validator


class ExamConstraints(BaseModel):
    """Ограничения для подготовки к экзамену"""

    exam_date: date = Field(..., description="Дата экзамена")
    study_hours_per_day: int = Field(..., ge=1, le=12, description="Часов учебы в день")
    break_days: List[date] = Field(default_factory=list, description="Дни без занятий")
    preferred_study_time: Optional[str] = Field(
        None, description="Предпочтительное время (утро/день/вечер)"
    )
    max_session_minutes: int = Field(90, ge=30, le=180, description="Макс. длительность сессии")
    min_break_minutes: int = Field(15, ge=5, le=30, description="Мин. перерыв между сессиями")
    blocked_topics_per_day: int = Field(3, ge=1, le=10, description="Макс. тем в день")


class SkillConstraints(BaseModel):
    """Ограничения для развития навыка"""

    practice_days_per_week: int = Field(..., ge=1, le=7, description="Дней практики в неделю")
    min_session_minutes: int = Field(30, ge=15, le=120, description="Мин. длительность практики")
    equipment_required: List[str] = Field(
        default_factory=list, description="Необходимое оборудование"
    )
    location_constraints: Optional[str] = Field(None, description="Ограничения по месту")
    mentor_availability: Optional[Dict[int, List[str]]] = Field(
        None, description="Доступность ментора"
    )
    budget_monthly: Optional[float] = Field(None, ge=0, description="Месячный бюджет")


class HabitConstraints(BaseModel):
    """Ограничения для формирования привычки"""

    start_small: bool = Field(True, description="Начинать с малого")
    initial_frequency: str = Field("daily", description="Начальная частота")
    reminder_times: List[str] = Field(default_factory=list, description="Времена напоминаний")
    accountability_partner: Optional[str] = Field(None, description="Партнер по подотчетности")
    reward_system: bool = Field(True, description="Использовать систему наград")
    max_skip_days: int = Field(1, ge=0, le=3, description="Макс. пропусков подряд")
    environmental_changes: List[str] = Field(
        default_factory=list, description="Изменения окружения"
    )


class HealthConstraints(BaseModel):
    """Ограничения для здоровья и фитнеса"""

    medical_conditions: List[str] = Field(
        default_factory=list, description="Медицинские ограничения"
    )
    injury_history: List[str] = Field(default_factory=list, description="История травм")
    available_time_slots: Dict[int, List[str]] = Field(
        default_factory=dict, description="Доступное время"
    )
    gym_access: bool = Field(False, description="Доступ в спортзал")
    dietary_restrictions: List[str] = Field(
        default_factory=list, description="Диетические ограничения"
    )
    sleep_schedule: Dict[str, str] = Field(default_factory=dict, description="График сна")
    stress_level: int = Field(5, ge=1, le=10, description="Уровень стресса")
    recovery_days_needed: int = Field(2, ge=1, le=4, description="Дней восстановления в неделю")


class TimeConstraints(BaseModel):
    """Ограничения для тайм-менеджмента"""

    work_hours: Dict[int, Dict[str, str]] = Field(
        default_factory=dict, description="Рабочие часы по дням"
    )
    fixed_commitments: List[Dict[str, any]] = Field(
        default_factory=list, description="Фиксированные обязательства"
    )
    family_time_required: int = Field(120, ge=0, description="Минут на семью в день")
    commute_time_daily: int = Field(0, ge=0, description="Время на дорогу в день (минут)")
    energy_levels: Dict[str, int] = Field(
        default_factory=dict, description="Уровни энергии по времени дня"
    )
    interruption_windows: List[Dict[str, str]] = Field(
        default_factory=list, description="Окна прерываний"
    )
    deep_work_blocks: int = Field(2, ge=1, le=4, description="Блоков глубокой работы в день")
    min_break_between_tasks: int = Field(5, ge=0, le=15, description="Мин. перерыв между задачами")


# Вспомогательные модели для сложных структур
class TimeSlot(BaseModel):
    """Временной слот"""

    start: str = Field(
        ..., pattern="^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$", description="Начало (HH:MM)"
    )
    end: str = Field(..., pattern="^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$", description="Конец (HH:MM)")
    activity: Optional[str] = Field(None, description="Активность")

    @validator("end")
    def validate_end_after_start(cls, v, values):
        """Проверка, что конец после начала"""
        if "start" in values:
            start_h, start_m = map(int, values["start"].split(":"))
            end_h, end_m = map(int, v.split(":"))
            if (end_h * 60 + end_m) <= (start_h * 60 + start_m):
                raise ValueError("Время окончания должно быть после времени начала")
        return v


class EnergyLevel(BaseModel):
    """Уровень энергии"""

    time_period: str = Field(..., description="Период времени")
    level: int = Field(..., ge=1, le=10, description="Уровень энергии (1-10)")
    best_for: List[str] = Field(default_factory=list, description="Лучше всего подходит для")


class Commitment(BaseModel):
    """Фиксированное обязательство"""

    name: str = Field(..., description="Название")
    days: List[int] = Field(..., description="Дни недели (1-7)")
    time_slot: TimeSlot = Field(..., description="Временной слот")
    priority: int = Field(1, ge=1, le=3, description="Приоритет")
    can_reschedule: bool = Field(False, description="Можно ли перенести")


# Фабричная функция для создания ограничений
def create_constraints(category: str, data: Dict[str, any]) -> BaseModel:
    """
    Создает объект ограничений для конкретной категории

    Args:
        category: Тип категории
        data: Данные ограничений

    Returns:
        Объект ограничений соответствующего типа
    """
    constraints_map = {
        "exam": ExamConstraints,
        "skill": SkillConstraints,
        "habit": HabitConstraints,
        "health": HealthConstraints,
        "time": TimeConstraints,
    }

    constraint_class = constraints_map.get(category)
    if not constraint_class:
        raise ValueError(f"Неизвестная категория: {category}")

    return constraint_class(**data)
