"""
Состояния FSM для онбординга ИИ-ассистента
"""
from aiogram.fsm.state import State, StatesGroup


class AssistantOnboardingStates(StatesGroup):
    """Состояния онбординга ИИ-ассистента"""
    
    # Основные состояния
    choosing_category = State()          # Выбор категории
    answering_questions = State()        # Ответы на вопросы
    setting_constraints = State()        # Установка ограничений
    reviewing_summary = State()          # Просмотр итогов
    
    # Специфичные состояния для категорий
    exam_questions = State()             # Вопросы для экзамена
    skill_questions = State()            # Вопросы для навыка
    habit_questions = State()            # Вопросы для привычки
    health_questions = State()           # Вопросы для здоровья
    time_questions = State()             # Вопросы для времени
    
    # Состояния ввода текста
    waiting_for_text = State()           # Ожидание текстового ответа
    waiting_for_number = State()         # Ожидание числового ответа
    waiting_for_date = State()           # Ожидание даты
    waiting_for_time = State()           # Ожидание времени
    waiting_for_list = State()           # Ожидание списка (через запятую)
    
    # Финальные состояния
    confirming_data = State()            # Подтверждение данных
    completed = State()                  # Онбординг завершен
    viewing_generated_plan = State()   