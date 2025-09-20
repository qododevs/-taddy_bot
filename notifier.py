# notifier.py
import os
from aiogram import Bot
from typing import List, Optional

# Глобальный объект бота — будет установлен при старте
_bot_instance: Optional[Bot] = None
_admin_ids: List[int] = []


def init_notifier(bot: Bot):
    """Инициализирует нотификатор — регистрирует бота и админов"""
    global _bot_instance, _admin_ids
    _bot_instance = bot
    admin_ids_str = os.getenv("ADMIN_IDS", "")
    _admin_ids = list(map(int, admin_ids_str.split(","))) if admin_ids_str else []
    print(f"[NOTIFIER] Инициализирован. Админы: {_admin_ids}")


async def notify_admins_of_rate_limit(current_key_index: int, new_key_index: int, total_keys: int):
    """
    Отправляет уведомление администраторам о срабатывании лимита 429
    """
    global _bot_instance, _admin_ids

    if not _bot_instance or not _admin_ids:
        print("[NOTIFIER] Бот или админы не инициализированы — пропускаем уведомление")
        return

    message = (
        f"⚠️ <b>Rate Limit 429</b>\n\n"
        f"Ключ <code>{current_key_index + 1}</code> исчерпал лимит.\n"
        f"Переключились на ключ <code>{new_key_index + 1}</code> из <code>{total_keys}</code>.\n"
        f"Рекомендуется добавить новые ключи через /addkey"
    )

    for admin_id in _admin_ids:
        try:
            await _bot_instance.send_message(admin_id, message, parse_mode="HTML")
            print(f"[NOTIFIER] Отправлено уведомление админу {admin_id}")
        except Exception as e:
            print(f"[NOTIFIER ERROR] Не удалось отправить админу {admin_id}: {e}")