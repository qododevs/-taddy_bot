import asyncio
import logging
from aiogram import Bot, Dispatcher
from handlers import router
from database import init_db, ensure_at_least_one_api_key
from utils import reload_api_keys, api_keys_cache  # ← ДОБАВЬ ИМПОРТ
from dotenv import load_dotenv
from character_handlers import router as character_router
from admin_handlers import router as admin_router
from notifier import init_notifier
import os

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

async def main():
    await init_db()

    # Автоматически добавляем начальный ключ, если БД пуста
    default_api_key = os.getenv("DEFAULT_API_KEY")
    if default_api_key:
        await ensure_at_least_one_api_key(default_api_key)
    else:
        print("[WARN] DEFAULT_API_KEY не задан в .env — добавьте ключ через /addkey")

    # 👇 ОБЯЗАТЕЛЬНО: загружаем ключи в кэш перед запуском бота
    await reload_api_keys()
    print(f"[INFO] API-ключи успешно загружены: {len(api_keys_cache)} ключ(ей)")

    bot = Bot(token=BOT_TOKEN)
    init_notifier(bot)
    dp = Dispatcher()

    # dp.include_router(character_router)
    dp.include_router(admin_router)
    dp.include_router(router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())