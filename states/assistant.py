"""
FSM состояния для модуля ИИ-ассистента
"""
from aiogram.fsm.state import State, StatesGroup


class AssistantStates(StatesGroup):
    chat_mode = State()
    """Состояния для работы с ИИ-ассистентом"""
    
    # Пользователь в режиме ассистента
    in_assistant_mode = State()
    
    # Пользователь в режиме свободного чата
    chatting = State()
    
    # Ожидание ответа от ИИ (опционально)
    waiting_response = State()