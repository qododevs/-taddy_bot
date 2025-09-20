from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from database import get_stats, add_api_key
# from utils import reload_api_keys, api_keys_cache
from admin_keyboards import get_admin_main_menu
from utils import reload_api_keys
from keyboards import get_main_menu
from admin_states import AdminState  # ← ДОБАВЬ ИМПОРТ
import asyncio
from database import get_all_api_keys  # ← ЭТО ДОБАВЬ

router = Router()


# Вспомогательная функция
def get_admin_ids():
    import os
    admin_ids_str = os.getenv("ADMIN_IDS", "")
    if not admin_ids_str:
        return []
    return list(map(int, admin_ids_str.split(",")))


# 👇 Обработчик кнопки "Добавить ключ" — переводит в состояние
@router.message(F.text == "Добавить ключ")
async def start_add_key(message: Message, state: FSMContext):
    if message.from_user.id not in get_admin_ids():
        return
    await message.answer("🔑 Пожалуйста, отправьте API-ключ:")
    await state.set_state(AdminState.waiting_for_api_key)


# 👇 Ловим ключ в состоянии
@router.message(StateFilter(AdminState.waiting_for_api_key))
async def process_api_key(message: Message, state: FSMContext):
    if message.from_user.id not in get_admin_ids():
        await state.clear()
        return

    new_key = message.text.strip()

    if len(new_key) < 10:
        await message.answer("❌ Ключ слишком короткий. Проверьте правильность.")
        return

    try:
        await add_api_key(new_key)
        await message.answer(f"✅ Ключ добавлен и установлен как ПЕРВЫЙ в списке использования.\nКлюч: `{new_key[:6]}...`", parse_mode="Markdown")

        # Обновляем кэш
        global api_keys_cache
        api_keys_cache = await get_all_api_keys()
        print(f"[INFO] Кэш ключей обновлён. Теперь {len(api_keys_cache)} ключ(ей).")

    except Exception as e:
        await message.answer(f"❌ Ошибка при добавлении ключа: {str(e)}")
        print(f"[ERROR] addkey: {e}")

    # Сбрасываем состояние
    await state.clear()
    await message.answer("🔐 Админ-меню:", reply_markup=get_admin_main_menu())


# 👇 Обработчик "Тест ключей"
@router.message(F.text == "Тест ключей")
async def cmd_testkey_button(message: Message):
    if message.from_user.id not in get_admin_ids():
        return
    try:
        await reload_api_keys()
        from utils import api_keys_cache  # ← ИМПОРТИРУЕМ ПОСЛЕ reload
        keys = api_keys_cache
        if not keys:
            await message.answer("❌ Ключей нет в базе данных. Добавьте через «Добавить ключ»")
            return
        first_key_sample = keys[0][:10] + "..." if keys else "нет ключей"
        await message.answer(f"✅ Доступно ключей: {len(keys)}\nПример: `{first_key_sample}`", parse_mode="Markdown")
    except Exception as e:
        error_msg = f"❌ Ошибка: {str(e)}"
        await message.answer(error_msg)
        print(f"[TESTKEY ERROR] {error_msg}")


# 👇 Обработчик "Статистика"
@router.message(F.text == "Статистика")
async def show_stats_from_menu(message: Message):
    if message.from_user.id not in get_admin_ids():
        return

    stats = await get_stats()
    if not stats:
        await message.answer("Статистика пуста.")
        return

    text = "📊 Статистика использования:\n\n"
    for row in stats[:10]:
        text += f"ID: {row['user_id']} | Запросов: {row['request_count']} | Последний: {row['last_request']}\n"

    await message.answer(text, reply_markup=get_admin_main_menu())


# 👇 Обработчик "⬅️ Назад"
@router.message(F.text == "⬅️ Назад")
async def back_to_main(message: Message, state: FSMContext):
    if message.from_user.id not in get_admin_ids():
        return
    await state.clear()  # на всякий случай сбрасываем состояние
    await message.answer("Вы вернулись в главное меню.", reply_markup=get_main_menu(message.from_user.id))


# 👇 Обработчик кнопки "Меню админа"
@router.message(F.text == "Меню админа")
async def open_admin_menu(message: Message):
    if message.from_user.id not in get_admin_ids():
        await message.answer("⛔ У вас нет доступа.")
        return
    await message.answer("🔐 Админ-меню:", reply_markup=get_admin_main_menu())


# 👇 Поддержка команды /addkey (опционально)
@router.message(Command("addkey"))
async def cmd_addkey(message: Message):
    if message.from_user.id not in get_admin_ids():
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
        await message.answer(f"✅ Ключ добавлен и установлен как ПЕРВЫЙ в списке использования.\nКлюч: `{new_key[:6]}...`", parse_mode="Markdown")

        global api_keys_cache
        api_keys_cache = await get_all_api_keys()
        print(f"[INFO] Кэш ключей обновлён. Теперь {len(api_keys_cache)} ключ(ей).")

    except Exception as e:
        await message.answer(f"❌ Ошибка при добавлении ключа: {str(e)}")
        print(f"[ERROR] addkey: {e}")