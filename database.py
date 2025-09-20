import asyncpg
import os
import json
from dotenv import load_dotenv

from prompts import DEFAULT_CHARACTER

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


async def init_db():
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS user_context (
                user_id BIGINT PRIMARY KEY,
                context JSONB NOT NULL DEFAULT '[]',
                name TEXT,
                gender TEXT,
                character TEXT DEFAULT 'neutral',
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)
        try:
            await conn.execute("ALTER TABLE user_context ADD COLUMN character TEXT DEFAULT 'neutral';")
            print("[MIGRATION] Добавлена колонка 'character'")
        except Exception as e:
            if "already exists" in str(e):
                pass  # Колонка уже есть — игнорируем
            else:
                raise e
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS usage_stats (
                id SERIAL PRIMARY KEY,
                user_id BIGINT,
                request_count INT DEFAULT 0,
                last_request TIMESTAMP DEFAULT NOW()
            );
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS api_keys (
                id SERIAL PRIMARY KEY,
                key TEXT UNIQUE NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT NOW(),
                priority INT DEFAULT 0
            );
        """)
    finally:
        await conn.close()


async def get_context(user_id):
    conn = await asyncpg.connect(DATABASE_URL)
    row = await conn.fetchrow("SELECT context, name, gender, character FROM user_context WHERE user_id = $1", user_id)
    await conn.close()
    if row:
        context = json.loads(row['context']) if row['context'] else []
        return context, row['name'], row['gender'], row['character'] or DEFAULT_CHARACTER
    return [], None, None, DEFAULT_CHARACTER


async def update_context(user_id, context, name=None, gender=None, character=None):
    conn = await asyncpg.connect(DATABASE_URL)
    context_json = json.dumps(context, ensure_ascii=False)

    existing = await conn.fetchrow("SELECT 1 FROM user_context WHERE user_id = $1", user_id)
    if existing:
        await conn.execute(
            """UPDATE user_context 
               SET context = $1, name = COALESCE($2, name), gender = COALESCE($3, gender), character = COALESCE($4, character) 
               WHERE user_id = $5""",
            context_json, name, gender, character, user_id
        )
    else:
        await conn.execute(
            """INSERT INTO user_context (user_id, context, name, gender, character) 
               VALUES ($1, $2, $3, $4, COALESCE($5, 'neutral'))""",
            user_id, context_json, name, gender, character
        )
    await conn.close()


async def clear_context(user_id):
    """
    Полностью сбрасывает контекст, имя и пол пользователя.
    """
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute("""
        UPDATE user_context 
        SET context = '[]', name = NULL, gender = NULL 
        WHERE user_id = $1
    """, user_id)
    await conn.close()
    print(f"[DEBUG] Контекст, имя и пол сброшены для user_id={user_id}")  # Для отладки


async def increment_stats(user_id):
    conn = await asyncpg.connect(DATABASE_URL)
    existing = await conn.fetchrow("SELECT 1 FROM usage_stats WHERE user_id = $1", user_id)
    if existing:
        await conn.execute(
            "UPDATE usage_stats SET request_count = request_count + 1, last_request = NOW() WHERE user_id = $1",
            user_id
        )
    else:
        await conn.execute(
            "INSERT INTO usage_stats (user_id, request_count) VALUES ($1, 1)",
            user_id
        )
    await conn.close()


async def get_stats():
    conn = await asyncpg.connect(DATABASE_URL)
    rows = await conn.fetch("SELECT user_id, request_count, last_request FROM usage_stats ORDER BY request_count DESC")
    await conn.close()
    return rows

# ============ УПРАВЛЕНИЕ API-КЛЮЧАМИ ============

async def init_api_keys_table():
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS api_keys (
                id SERIAL PRIMARY KEY,
                key TEXT UNIQUE NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT NOW(),
                priority INT DEFAULT 0
            );
        """)
    finally:
        await conn.close()


async def get_all_api_keys():
    """Возвращает список активных ключей, отсортированных по приоритету (первый — самый приоритетный)"""
    conn = await asyncpg.connect(DATABASE_URL)
    rows = await conn.fetch("""
        SELECT key FROM api_keys 
        WHERE is_active = TRUE 
        ORDER BY priority ASC, created_at ASC
    """)
    await conn.close()
    return [row['key'] for row in rows]


async def add_api_key(new_key: str):
    """Добавляет новый ключ и делает его первым по приоритету"""
    conn = await asyncpg.connect(DATABASE_URL)

    # Получаем текущий минимальный приоритет (самый высокий)
    min_priority = await conn.fetchval("SELECT MIN(priority) FROM api_keys")
    if min_priority is None:
        min_priority = 0
    new_priority = min_priority - 1  # Новый ключ будет выше всех

    # Вставляем ключ
    await conn.execute("""
        INSERT INTO api_keys (key, priority) 
        VALUES ($1, $2)
        ON CONFLICT (key) DO UPDATE 
        SET priority = $2, is_active = TRUE
    """, new_key, new_priority)

    await conn.close()


async def ensure_at_least_one_api_key(default_key: str = None):
    """Гарантирует, что в таблице есть хотя бы один ключ. Если нет — добавляет default_key."""
    if not default_key:
        return

    keys = await get_all_api_keys()
    if not keys:
        print("[INFO] Нет API-ключей в БД. Добавляю ключ по умолчанию...")
        await add_api_key(default_key)
        print(f"[INFO] Ключ '{default_key[:6]}...' добавлен как первый.")