from aiogram.fsm.state import State, StatesGroup

class AdminState(StatesGroup):
    waiting_for_api_key = State()  # Ожидание ввода API-ключа