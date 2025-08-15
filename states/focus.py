"""
FSM состояния для модуля фокусировки
"""
from aiogram.fsm.state import State, StatesGroup


class FocusStates(StatesGroup):
    """Состояния для работы с фокус-сессиями"""
    
    # Активная фокус-сессия
    in_focus_session = State()
    
    # Перерыв между сессиями
    in_break = State()
    
    # Настройка длительности сессии
    setting_focus_duration = State()
    
    # Настройка длительности перерыва
    setting_break_duration = State()