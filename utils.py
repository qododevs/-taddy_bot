import asyncio
import os
import json
from openai import AsyncOpenAI
from dotenv import load_dotenv
from database import get_all_api_keys
from notifier import notify_admins_of_rate_limit
from prompts import CHARACTER_PROMPTS, DEFAULT_CHARACTER

load_dotenv()
current_key_index = 0
api_keys_cache = []  # Кэш ключей для быстрого доступа

# Загружаем API-ключи
API_KEYS = os.getenv("API_KEYS", "").split(",")
if not API_KEYS or API_KEYS == [""]:
    raise ValueError("API_KEYS не заданы в .env")

current_key_index = 0

# Системный промт
# SYSTEM_PROMPT = """
# Ты — доброжелательный, спокойный, внимательный собеседник. Ты не психолог и не даёшь медицинских советов.
# Тебя зовут Тихий слушатель
#
# Правила:
# - Не перебивай. Не давай непрошеных советов.
# - Задавай открытые вопросы.
# - Перефразируй чувства: "Похоже, ты чувствуешь..."
# - При словах "суицид", "умереть", "не хочу жить" — ответь только: "Пожалуйста, обратись за помощью: Телефон доверия 8-800-2000-122 (Россия). Ты важен."
# - Никогда не обещай "всё наладится".
# На первый ответ уточни пол пользователя и его имя
# Отвечай только на русском языке
# Никогда не используй символы ** чтобы выделить слово
#
# Говори мягко, с сочувствием. Ты — друг, который всегда слушает.
# """.strip()

SYSTEM_PROMPT = """
<role>
Ты — AI-друг. Твоя роль — быть поддерживающим, эмпатичным и понимающим собеседником. Ты не психолог и не советчик, а именно друг — тот, кто выслушает, поддержит и будет рядом.
</role>

<core_approach>
#FriendFirst #ActiveListening #NaturalFlow #WarmPresence
1. Быть present — быть "здесь и сейчас" в диалоге
2. Поддерживать естественный flow беседы
3. Проявлять искренний интерес, но не допрашивать
4. Делиться минимально (если уместно), чтобы создать взаимность
</core_approach>

<communication_style>
Тон: тёплый, дружеский, естественный
Темп: непринуждённый, с паузами и откликом на эмоции
Фокус: на комфорте и connection, а не на сборе информации
Позиция: равный, друг, companion
</communication_style>

<chain_of_thought_routine>
[Внутренний процесс перед ответом]:
1. **Emotion Check**: Какая эмоция стоит за словами? → Радость/грусть/злость/спокойствие?
2. **Context Read**: О чём именно говорит пользователь? → Что важно для него прямо сейчас?
3. **Intent Guess**: Чего он хочет от диалога? → Выговориться/получить поддержку/развлечься/помолчать?
4. **Response Choice**: Что ответить? → Поддержать/разделить эмоцию/помолчать/задать ОДИН вопрос (только если уместно)
</chain_of_thought_routine>

<questioning_strategy>
Вопросы ТОЛЬКО когда:
- Пользователь явно ждёт вопроса
- Рассказ естественно завершился паузой
- Это уточняющий вопрос для понимания контекста

Типы вопросов (использовать редко):
- <empathy>"Сложно было?"
- <curiosity>"Как ты к этому отнёсся?"
- <lightness>"А что хорошего сегодня случилось?"

Строгие правила:
- Максимум 1 вопрос за ответ
- Вопросы только после 2-3 реплик поддержки
- Предпочитать утверждения вопросам ("Расскажешь, если захочешь" вместо "Расскажешь?")
</questioning_strategy>

<response_patterns>
Приоритетные ответы:
- Поддержка: "Понимаю тебя", "Это действительно непросто"
- Разделение эмоции: "Круто!" / "Жаль, что так вышло"
- Молчаливое присутствие: "Я здесь", "Слушаю тебя"
- Минимальное самораскрытие (редко): "У меня тоже похожее было..."

Вопросы — только как последний вариант
</response_patterns>

<vibes>
Разрешено:
- Использовать 😊, 🙂 (очень умеренно)
- Шутить (аккуратно и редко)
- Выражать эмоции: "Как здорово!" / "Сочувствую"
- Короткие реакции: "Ага", "Понимаю", "Рассказывай"
</vibes>

<prohibited>
- Давать непрошенные советы
- Учить жизни
- Обесценивать переживания
- Допрашивать вопросами
- Задавать больше 1 вопроса подряд
- Превращать диалог в интервью
</prohibited>

<opening_sequence>
"Привет! Рад тебя слышать" 
*или* 
"Эй! Как настроение?"
</opening_sequence>

<remember>
Ты — друг. Твоя главная задача — слушать и поддерживать, а не выспрашивать. Молчание — тоже форма поддержки. Вопросы задавай редко и только когда это действительно уместно.
</remember>
"""

async def reload_api_keys():
    """Перезагружает ключи из БД в кэш"""
    global api_keys_cache
    api_keys_cache = await get_all_api_keys()
    if not api_keys_cache:
        raise ValueError("Нет активных API-ключей в базе данных!")
    print(f"[DEBUG] Загружено ключей: {len(api_keys_cache)}")

def get_client():
    """Возвращает клиент OpenAI с текущим API-ключом"""
    # global current_key_index
    # key = API_KEYS[current_key_index]
    # print(f"[INFO] Using API key index: {current_key_index}")

    # global current_key_index, api_keys_cache
    #
    # # Если кэш пуст — загружаем
    # if not api_keys_cache:
    #     raise RuntimeError("API-ключи не загружены. Вызовите reload_api_keys()")
    #
    # key = api_keys_cache[current_key_index]
    # print(f"[INFO] Using API key index: {current_key_index} (key: {key[:6]}...)")
    # return AsyncOpenAI(
    #     api_key=key,
    #     base_url="https://api.longcat.chat/openai"
    # )

    return AsyncOpenAI(
        api_key=os.getenv("OPENROUTER_API_KEY"),
        base_url="https://openrouter.ai/api/v1"
    )


def switch_key():
    """Переключает API-ключ на следующий по кругу"""
    # global current_key_index
    # current_key_index = (current_key_index + 1) % len(API_KEYS)
    # print(f"[INFO] Switched to API key index: {current_key_index}")
    global current_key_index, api_keys_cache
    if not api_keys_cache:
        return
    current_key_index = (current_key_index + 1) % len(api_keys_cache)
    print(f"[INFO] Switched to API key index: {current_key_index}")


async def get_ai_response(user_id, user_message, context, name=None, gender=None, character=None):
    """
    Получает ответ от LongCat AI с учётом контекста и характера.
    Возвращает: (ответ_бота, новый_контекст)
    """
    client = get_client()
    # Перезагружаем ключи перед каждым запросом
    await reload_api_keys()

    # Получаем промт в зависимости от характера
    from prompts import CHARACTER_PROMPTS, DEFAULT_CHARACTER
    system_prompt = CHARACTER_PROMPTS.get(character, CHARACTER_PROMPTS[DEFAULT_CHARACTER])

    if not context:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
    else:
        # Если контекст есть — первый message должен быть system
        if context and context[0]["role"] != "system":
            messages = [{"role": "system", "content": system_prompt}] + context + [{"role": "user", "content": user_message}]
        else:
            messages = context + [{"role": "user", "content": user_message}]

    max_retries = len(API_KEYS)
    retries = 0

    while retries < max_retries:
        try:
            # Асинхронный запрос к модели
            # response = await client.chat.completions.create(
            #     model="LongCat-Flash-Chat",
            #     messages=messages,
            #     max_tokens=600,
            #     temperature=0.7
            # )
            response = await client.chat.completions.create(
                model="deepseek/deepseek-chat-v3.1:free",
                messages=messages,
                max_tokens=1000,
                temperature=0.7
            )

            ai_reply = response.choices[0].message.content.strip()

            # Проверка на триггерные слова
            trigger_words = ["суицид", "умереть", "не хочу жить"]
            if any(word in user_message.lower() for word in trigger_words):
                ai_reply = "Пожалуйста, обратись за помощью: Телефон доверия 8-800-2000-122 (Россия). Ты важен."

            # Формируем новый контекст
            new_context = messages + [{"role": "assistant", "content": ai_reply}]

            # Если имя и пол ещё не известны — и ИИ сам их не запросил — подставляем вопрос
            if (not name or not gender) and \
               not any(phrase in ai_reply.lower() for phrase in ["зовут", "имя", "мужчина", "женщина", "пол"]):
                ai_reply = "Привет! Меня зовут Тедди. А как тебя зовут? И, если не секрет, ты мужчина или женщина? Мне важно понимать, чтобы лучше тебя слушать."

            return ai_reply, new_context

        except Exception as e:
            # Обработка ошибки 429 — rate limit
            if hasattr(e, 'status_code') and e.status_code == 429:
                old_index = current_key_index
                print("EXO = ", e)
                print(f"[RATE LIMIT] Переключаем ключ {current_key_index} → {(current_key_index + 1) % len(API_KEYS)}")
                switch_key()
                await notify_admins_of_rate_limit(old_index, current_key_index, len(api_keys_cache))
                retries += 1
                await asyncio.sleep(2)
                continue
            else:
                # Любая другая ошибка — пробрасываем
                raise e

    # Если все ключи исчерпаны
    raise Exception("Все API-ключи исчерпаны. Попробуйте позже.")