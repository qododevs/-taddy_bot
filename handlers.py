from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.enums import ChatAction
from aiogram.exceptions import TelegramBadRequest
from database import get_context, update_context, clear_context, increment_stats, get_stats
from utils import get_ai_response
from keyboards import get_main_menu
import asyncio
import os
import re
import datetime

router = Router()

ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(","))) if os.getenv("ADMIN_IDS") else []


def extract_name_and_gender(text: str):
    text = text.strip().lower()
    name = None
    gender = None
    male_keywords = ["мужчина", "мужской", "парень", "мальчик", "муж", "м"]
    female_keywords = ["женщина", "женский", "девушка", "девочка", "жен", "ж"]
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
    context, name, gender, _, _, _ = await get_context(user_id)
    if not context:
        await update_context(user_id, [])
    if name and gender:
        greeting = f"Рад снова тебя видеть, {name}! 🐱\nО чём поговорим сегодня?"
    else:
        greeting = (
            "Привет! 👋 Меня зовут Тихий слушатель — я твой цифровой друг, который всегда готов выслушать.\n\n"
            "А как тебя зовут? И, если не секрет, ты мужчина или женщина? "
            "Мне важно понимать, чтобы лучше тебя слушать 🐱💬"
        )
    await message.answer(greeting, reply_markup=get_main_menu(user_id))


@router.message(F.text == "Очистить контекст")
async def clear_ctx(message: Message, bot: Bot):
    user_id = message.from_user.id
    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    await asyncio.sleep(0.3)
    await clear_context(user_id)
    greeting = (
        "✅ Контекст очищен. Можешь начать с чистого листа 💭\n\n"
        "Привет! 👋 Меня зовут Тихий слушатель — я твой цифровой друг, который всегда готов выслушать.\n\n"
        "А как тебя зовут? И, если не секрет, ты мужчина или женщина? "
        "Мне важно понимать, чтобы лучше тебя слушать 🐱💬"
    )
    await message.answer(greeting, reply_markup=get_main_menu(user_id))


@router.message(F.text == "Остановить ответ")
async def stop_response(message: Message):
    await message.answer("Я прервал свою мысль. Можешь продолжить, когда будешь готов.", reply_markup=get_main_menu(message.from_user.id))


@router.message(F.text == "Статистика")
async def show_stats(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("У вас нет доступа к этой команде.")
        return
    stats = await get_stats()
    if not stats:
        await message.answer("Статистика пуста.")
        return
    text = "📊 Статистика использования:\n\n"
    for row in stats[:10]:
        text += f"ID: {row['user_id']} | Запросов: {row['request_count']} | Последний: {row['last_request']}\n"
    await message.answer(text, reply_markup=get_main_menu(message.from_user.id))


@router.message()
async def handle_message(message: Message, bot: Bot):
    user_id = message.from_user.id
    user_text = message.text

    thinking_msg = await message.answer("🐻 Думаю...", reply_markup=None)

    async def send_deep_thinking():
        await asyncio.sleep(8.0)
        try:
            await bot.send_message(user_id, "🧠 Глубоко думаю... Ещё немного.")
        except Exception as e:
            print(f"[DEEP THINKING] Не удалось отправить: {e}")

    deep_thinking_task = asyncio.create_task(send_deep_thinking())

    try:
        context, name, gender, _, _, _ = await get_context(user_id)

        if not name or not gender:
            extracted_name, extracted_gender = extract_name_and_gender(user_text)
            if extracted_name:
                name = extracted_name
            if extracted_gender:
                gender = extracted_gender

        ai_reply, new_context = await asyncio.wait_for(
            get_ai_response(user_id, user_text, context, name, gender),
            timeout=25.0
        )

        await update_context(user_id, new_context, name, gender)
        await increment_stats(user_id)

        deep_thinking_task.cancel()
        try:
            await deep_thinking_task
        except asyncio.CancelledError:
            pass

        try:
            await thinking_msg.delete()
        except TelegramBadRequest:
            pass

        await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
        await message.answer(ai_reply, reply_markup=get_main_menu(user_id))

    except asyncio.TimeoutError:
        deep_thinking_task.cancel()
        try:
            await deep_thinking_task
        except asyncio.CancelledError:
            pass
        try:
            await thinking_msg.delete()
        except TelegramBadRequest:
            pass
        await message.answer(
            "😔 Извини, я слишком долго думал и не успел сформулировать ответ. "
            "Можешь повторить или сказать иначе?",
            reply_markup=get_main_menu(user_id)
        )
    except Exception as e:
        deep_thinking_task.cancel()
        try:
            await deep_thinking_task
        except asyncio.CancelledError:
            pass
        try:
            await thinking_msg.delete()
        except TelegramBadRequest:
            pass
        await message.answer("Произошла ошибка. Попробуй позже 🙏", reply_markup=get_main_menu(user_id))
        print(f"[ERROR] {e}")