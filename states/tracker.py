"""
FSM состояния для модуля трекинга привычек
"""
from aiogram.fsm.state import State, StatesGroup


class HabitCreationStates(StatesGroup):
    """Состояния для создания новой привычки"""
    
    # Выбор типа привычки (полезная/вредная) или из пресетов
    choosing_habit_type = State()
    
    # Ожидание названия привычки
    waiting_for_name = State()
    
    # Ожидание описания привычки
    waiting_for_description = State()
    
    # Ожидание желаемой частоты (для полезных привычек)
    waiting_for_frequency = State()
    
    # Ожидание эмодзи/иконки
    waiting_for_emoji = State()


class BadHabitStates(StatesGroup):
    """Состояния для работы с вредными привычками"""
    
    # Подтверждение сброса счетчика
    confirming_reset = State()