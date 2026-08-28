import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

import db

BOT_TOKEN = os.getenv("BOT_TOKEN")

dp = Dispatcher()


@dp.message(CommandStart())
async def start_handler(message: Message) -> None:
    await message.answer(
        f"Привет, {message.from_user.first_name}!\n\n"
        "Что умею:\n"
        "/sqlite — проверить локальную SQLite\n"
        "/postgres — проверить Postgres по DATABASE_URL"
    )


@dp.message(Command("sqlite"))
async def sqlite_handler(message: Message) -> None:
    try:
        count = await db.sqlite_add_visit(message.from_user.id)
    except Exception as e:
        await message.answer(f"SQLite: ошибка\n{type(e).__name__}: {e}")
        return

    await message.answer(
        f"SQLite ок, файл {db.SQLITE_PATH}\nЗаписей по вам: {count}"
    )


@dp.message(Command("postgres"))
async def postgres_handler(message: Message) -> None:
    try:
        count, version = await db.postgres_add_visit(message.from_user.id)
    except Exception as e:
        await message.answer(f"Postgres: ошибка\n{type(e).__name__}: {e}")
        return

    await message.answer(
        f"Postgres ок\n{version.split(' on ')[0]}\nЗаписей по вам: {count}"
    )


async def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("Не задана переменная окружения BOT_TOKEN")

    await db.init_sqlite()
    await db.init_postgres()
    if not db.DATABASE_URL:
        logging.warning("DATABASE_URL не задан, команда /postgres работать не будет")

    bot = Bot(token=BOT_TOKEN)
    try:
        await dp.start_polling(bot)
    finally:
        await db.close_postgres()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
