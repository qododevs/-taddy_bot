from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.enums import ChatAction
from aiogram.exceptions import TelegramBadRequest

from character_handlers import get_character_inline_kb
from database import (
    get_context, update_context, clear_context, increment_stats,
    get_stats, get_all_api_keys, add_api_key
)
from aiogram.enums import ChatAction
from utils import get_ai_response, reload_api_keys, api_keys_cache
from keyboards import get_main_menu
import asyncio
import os
import re

router = Router()

ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(","))) if os.getenv("ADMIN_IDS") else []


def extract_name_and_gender(text: str):
    """
    Извлекает имя и пол из сообщения пользователя.
    Поддерживает фразы: "Рома, мужчина", "Меня зовут Аня", "Я — Саша, пол женский" и т.п.
    """
    text = text.strip().lower()
    name = None
    gender = None

    male_keywords = ["мужчина", "мужской", "парень", "мальчик", "муж", "м", "male", "man", "boy"]
    female_keywords = ["женщина", "женский", "девушка", "девочка", "жен", "ж", "female", "woman", "girl"]

    for word in male_keywords:
        if word in text:
            gender = "мужчина"
            break
    for word in female_keywords:
        if word in text:
            gender = "женщина"
            break

    patterns = [
        r'меня\s+зовут\s+([а-яёa-z]+)',
        r'я\s+([а-яёa-z]+)[\s,\.]',
        r'^([а-яёa-z]+)[\s,]',
        r'это\s+([а-яёa-z]+)',
        r'зовут\s+([а-яёa-z]+)'
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            name = match.group(1).capitalize()
            break

    return name, gender


@router.message(Command("start"))
async def cmd_start(message: Message, bot: Bot):
    user_id = message.from_user.id

    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    await asyncio.sleep(0.3)

    # 👇 ИСПРАВЛЕНО: распаковываем 4 значения
    context, name, gender, character = await get_context(user_id)

    if not context:
        await update_context(user_id, [])

    if name and gender:
        greeting = f"Рад снова тебя видеть, {name}! 🐱\nО чём поговорим сегодня?"
        await message.answer(greeting, reply_markup=get_main_menu(user_id))
    else:
        await message.answer(
            "👋 Привет! Я — Тедди 🐻. Прежде чем начать, выбери, в каком стиле тебе комфортно общаться:",
            reply_markup=get_character_inline_kb()
        )


@router.message(Command("addkey"))
async def cmd_addkey(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ У вас нет прав для выполнения этой команды.")
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("📌 Использование: /addkey ваш_ключ_сюда")
        return

    new_key = args[1].strip()

    if len(new_key) < 10:
        await message.answer("❌ Ключ слишком короткий. Проверьте правильность.")
        return

    try:
        await add_api_key(new_key)
        await message.answer(
            f"✅ Ключ добавлен и установлен как ПЕРВЫЙ в списке использования.\nКлюч: `{new_key[:6]}...`",
            parse_mode="Markdown"
        )

        global api_keys_cache
        api_keys_cache = await get_all_api_keys()
        print(f"[INFO] Кэш ключей обновлён. Теперь {len(api_keys_cache)} ключ(ей).")

    except Exception as e:
        await message.answer(f"❌ Ошибка при добавлении ключа: {str(e)}")
        print(f"[ERROR] addkey: {e}")


@router.message(Command("testkey"))
async def cmd_testkey(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ У вас нет доступа к этой команде.")
        return

    try:
        await reload_api_keys()
        keys = api_keys_cache
        if not keys:
            await message.answer("❌ Ключей нет в базе данных. Добавьте через /addkey")
            return

        first_key_sample = keys[0][:10] + "..." if keys else "нет ключей"
        await message.answer(
            f"✅ Доступно ключей: {len(keys)}\nПример: `{first_key_sample}`",
            parse_mode="Markdown"
        )

    except Exception as e:
        error_msg = f"❌ Ошибка: {str(e)}"
        await message.answer(error_msg)
        print(f"[TESTKEY ERROR] {error_msg}")


@router.message(F.text == "Очистить контекст")
async def clear_ctx(message: Message, bot: Bot):
    user_id = message.from_user.id

    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    await asyncio.sleep(0.3)

    await clear_context(user_id)

    # 👇 ИСПРАВЛЕНО: распаковываем 4 значения
    context, name, gender, character = await get_context(user_id)

    greeting = (
        "✅ Контекст очищен. Можешь начать с чистого листа 💭\n\n"
        "Выбери характер ассистента"
    )

    await message.answer(greeting, reply_markup=get_character_inline_kb())


@router.message(F.text == "Остановить ответ")
async def stop_response(message: Message):
    await message.answer(
        "Я прервал свою мысль. Можешь продолжить, когда будешь готов.",
        reply_markup=get_main_menu(message.from_user.id)
    )


@router.message()
async def handle_message(message: Message, bot: Bot):
    user_id = message.from_user.id
    user_text = message.text

    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    thinking_msg = await message.answer("🐻 Думаю...", reply_markup=None)

    try:
        await asyncio.sleep(0.7)

        # 👇 ИСПРАВЛЕНО: распаковываем 4 значения
        context, name, gender, character = await get_context(user_id)

        if not name or not gender:
            extracted_name, extracted_gender = extract_name_and_gender(user_text)
            if extracted_name:
                name = extracted_name
            if extracted_gender:
                gender = extracted_gender

        await reload_api_keys()

        # Передаём character в get_ai_response
        ai_reply, new_context = await get_ai_response(user_id, user_text, context, name, gender, character)

        await update_context(user_id, new_context, name, gender, character)
        await increment_stats(user_id)

        try:
            await thinking_msg.delete()
        except TelegramBadRequest:
            pass

        await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
        await message.answer(ai_reply, reply_markup=None)

    except Exception as e:
        try:
            await thinking_msg.delete()
        except TelegramBadRequest:
            pass

        await message.answer("Произошла ошибка. Попробуй позже 🙏", reply_markup=get_main_menu(user_id))
        print(f"[ERROR] {e}")