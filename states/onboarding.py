"""
FSM состояния для начального опроса пользователей
"""
from aiogram.fsm.state import State, StatesGroup


class OnboardingStates(StatesGroup):
    """Состояния для процесса начального опроса"""
    
    # Ожидание ответа на вопрос о главной цели
    waiting_for_goal = State()
    
    # Ожидание ответа о привычках/вредных привычках
    waiting_for_habits = State()
    
    # Ожидание ответа о проблемах с тайм-менеджментом
    waiting_for_time_problems = State()