"""
FSM состояния для модуля чек-листа
"""

from aiogram.fsm.state import State, StatesGroup


class TaskCreationStates(StatesGroup):
    """Состояния для создания новой задачи"""

    # Ожидание названия задачи
    waiting_for_title = State()

    # Ожидание описания задачи
    waiting_for_description = State()

    # Выбор приоритета
    waiting_for_priority = State()

    # Установка дедлайна
    waiting_for_deadline = State()


class TaskEditStates(StatesGroup):
    """Состояния для редактирования задачи"""

    # Выбор что редактировать
    selecting_field = State()

    # Ожидание нового названия
    waiting_for_new_title = State()

    # Ожидание нового описания
    waiting_for_new_description = State()

    # Выбор нового приоритета
    waiting_for_new_priority = State()

    # Установка нового дедлайна
    waiting_for_new_deadline = State()
