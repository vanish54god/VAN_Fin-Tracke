import asyncio
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart

# Загружаем переменные из .env файла
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

# Создаём объекты бота и диспетчера (диспетчер распределяет входящие сообщения)
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Обработчик команды /start
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer("Привет! Я твой финансовый трекер. Пока умею только повторять твои сообщения.")

# Обработчик любого текстового сообщения (кроме команд)
@dp.message()
async def echo(message: types.Message):
    await message.answer(f"Ты написал: {message.text}")

# Точка входа — запуск бота
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())