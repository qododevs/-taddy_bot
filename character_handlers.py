from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database import update_context, get_context
from prompts import CHARACTER_PROMPTS, DEFAULT_CHARACTER
from keyboards import get_main_menu
import asyncio

router = Router()


def get_character_inline_kb():
    buttons = [
        [InlineKeyboardButton(text="😐 Нейтральный", callback_data="char_neutral")],
        [InlineKeyboardButton(text="🤔 Философский", callback_data="char_philosophical")],
        [InlineKeyboardButton(text="😄 Юмористический", callback_data="char_humorous")],
        [InlineKeyboardButton(text="😄 Твоя подруга", callback_data="char_girl")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.callback_query(F.data.startswith("char_"))
async def set_character(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    char_key = callback.data.split("_")[1]  # "neutral", "philosophical", "humorous"

    # Сохраняем выбор в БД
    await update_context(user_id, [], character=char_key)  # контекст не трогаем

    # Получаем актуальные данные
    context, name, gender, character = await get_context(user_id)

    await callback.answer()
    await bot.edit_message_text(
        chat_id=callback.message.chat.id,
        message_id=callback.message.message_id,
        text=f"✅ Характер общения изменён на: {get_character_name(char_key)}\n\nТеперь я буду общаться с тобой в этом стиле.",
        reply_markup=None
    )

    # Отправляем приветствие или возвращаем в меню
    if name and gender:
        greeting = f"Рад снова тебя видеть, {name}! 🐱\nО чём поговорим сегодня?"
    else:
        greeting = (
            "Привет! 👋 Меня зовут Тедди 🐻 — я твой цифровой друг, который всегда готов выслушать.\n\n"
            "А как тебя зовут? И, если не секрет, ты мужчина или женщина? "
            "Мне важно понимать, чтобы лучше тебя слушать."
        )

    await callback.message.answer(greeting, reply_markup=get_main_menu(user_id))


def get_character_name(key: str) -> str:
    names = {
        "neutral": "Нейтральный",
        "philosophical": "Философский",
        "humorous": "Юмористический",
        "girl": "Твоя подруга"
    }
    return names.get(key, "Неизвестный")


@router.message(F.text == "Характер")
async def choose_character(message: Message):
    await message.answer(
        "🎭 Выбери характер общения со мной:",
        reply_markup=get_character_inline_kb()
    )