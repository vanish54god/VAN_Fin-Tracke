import asyncio
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart

import database as db

# Загружаем переменные из .env файла
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

# Создаём объекты бота и диспетчера
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Обработчик команды /start
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    telegram_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name

    existing_user = db.get_user(telegram_id)

    if existing_user is None:
        db.add_user(telegram_id, username)
        user = db.get_user(telegram_id)
        db.add_default_categories(user[0])  # user[0] — это id из таблицы users
        await message.answer(
            f"Привет, {username}! Я твой финансовый трекер.\n"
            f"Зарегистрировал тебя и создал базовые категории. Погнали копить и отслеживать финансы!"
        )
    else:
        await message.answer(f"С возвращением, {username}!")

# Обработчик любого текстового сообщения (кроме команд)
@dp.message()
async def echo(message: types.Message):
    await message.answer(f"Ты написал: {message.text}")

# Точка входа — запуск бота
async def main():
    db.init_db()  # убеждаемся, что таблицы существуют перед запуском
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())