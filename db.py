import os
from datetime import datetime
from pathlib import Path

import aiosqlite
import asyncpg

# На bothost между перезапусками и деплоями переживает только /app/data,
# поэтому файл БД кладём туда, если такая директория есть.
# Имена переменных DATABASE_PATH / DB_PATH — из доки хостинга.
_DEFAULT_SQLITE_PATH = "/app/data/bot.db" if Path("/app/data").is_dir() else "bot.db"

SQLITE_PATH = (
    os.getenv("DATABASE_PATH")
    or os.getenv("DB_PATH")
    or os.getenv("SQLITE_PATH")
    or _DEFAULT_SQLITE_PATH
)
DATABASE_URL = os.getenv("DATABASE_URL")

_pg_pool: asyncpg.Pool | None = None


async def init_sqlite() -> None:
    Path(SQLITE_PATH).parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(SQLITE_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS visits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        await db.commit()


async def sqlite_add_visit(user_id: int) -> int:
    """Пишет визит и возвращает общее число визитов этого пользователя."""
    async with aiosqlite.connect(SQLITE_PATH) as db:
        await db.execute(
            "INSERT INTO visits (user_id, created_at) VALUES (?, ?)",
            (user_id, datetime.now().isoformat(timespec="seconds")),
        )
        await db.commit()
        async with db.execute(
            "SELECT COUNT(*) FROM visits WHERE user_id = ?", (user_id,)
        ) as cursor:
            (count,) = await cursor.fetchone()
    return count


async def init_postgres() -> None:
    """Создаёт пул и таблицу. Молча выходит, если DATABASE_URL не задан."""
    global _pg_pool
    if not DATABASE_URL:
        return

    _pg_pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5)
    async with _pg_pool.acquire() as conn:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS visits (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )


async def close_postgres() -> None:
    if _pg_pool is not None:
        await _pg_pool.close()


async def postgres_add_visit(user_id: int) -> tuple[int, str]:
    """Пишет визит и возвращает (число визитов, версия сервера)."""
    if _pg_pool is None:
        raise RuntimeError("Postgres не подключён: не задан DATABASE_URL")

    async with _pg_pool.acquire() as conn:
        await conn.execute("INSERT INTO visits (user_id) VALUES ($1)", user_id)
        count = await conn.fetchval(
            "SELECT COUNT(*) FROM visits WHERE user_id = $1", user_id
        )
        version = await conn.fetchval("SELECT version()")
    return count, version
