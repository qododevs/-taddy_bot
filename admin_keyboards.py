from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_admin_main_menu():
    """Главное админ-меню"""
    buttons = [
        [KeyboardButton(text="Добавить ключ")],
        [KeyboardButton(text="Тест ключей")],
        [KeyboardButton(text="Статистика")],
        [KeyboardButton(text="⬅️ Назад")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


# def get_main_menu_with_admin():
#     """Основное меню с кнопкой 'Меню админа' вместо 'Статистика'"""
#     buttons = [
#         [KeyboardButton(text="Очистить контекст")],
#         [KeyboardButton(text="Остановить ответ"), KeyboardButton(text="Меню админа")]
#     ]
#     return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)