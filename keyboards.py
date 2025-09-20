from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
import os

def get_main_menu(user_id: int = None):
    buttons = [
        [KeyboardButton(text="Очистить контекст")],
    ]

    second_row = [KeyboardButton(text="Остановить ответ"), KeyboardButton(text="Характер")]

    ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(","))) if os.getenv("ADMIN_IDS") else []

    if user_id and user_id in ADMIN_IDS:
        second_row.append(KeyboardButton(text="Меню админа"))

    buttons.append(second_row)
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)