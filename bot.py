import asyncio
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext

import database as db
from states import TransactionForm
from keyboards import type_keyboard, categories_keyboard

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

# Шаг 1: пользователь вызывает команду добавления транзакции
@dp.message(F.text == "/add")
async def cmd_add_transaction(message: types.Message, state: FSMContext):
    await state.set_state(TransactionForm.choosing_type)
    await message.answer("Это трата или доход?", reply_markup=type_keyboard())

# Шаг 2: пользователь нажал кнопку "Трата" или "Доход"
@dp.callback_query(TransactionForm.choosing_type, F.data.startswith("type_"))
async def process_type(callback: types.CallbackQuery, state: FSMContext):
    chosen_type = callback.data.split("_")[1]  # "expense" или "income"
    await state.update_data(type=chosen_type)

    user = db.get_user(callback.from_user.id)
    categories = db.get_categories(user[0], cat_type=chosen_type)

    await state.set_state(TransactionForm.choosing_category)
    await callback.message.edit_text("Выбери категорию:", reply_markup=categories_keyboard(categories))
    await callback.answer()  # убирает "часики" на кнопке в Telegram

# Шаг 3: пользователь выбрал категорию
@dp.callback_query(TransactionForm.choosing_category, F.data.startswith("cat_"))
async def process_category(callback: types.CallbackQuery, state: FSMContext):
    category_id = int(callback.data.split("_")[1])
    await state.update_data(category_id=category_id)

    await state.set_state(TransactionForm.entering_amount)
    await callback.message.edit_text("Введи сумму:")
    await callback.answer()

# Шаг 4: пользователь вводит сумму текстом
@dp.message(TransactionForm.entering_amount)
async def process_amount(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text)
    except ValueError:
        await message.answer("Это не похоже на число. Попробуй ещё раз, например: 500 или 199.99")
        return

    await state.update_data(amount=amount)
    await state.set_state(TransactionForm.entering_description)
    await message.answer("Добавь комментарий (или напиши «-», если не нужен):")

# Шаг 5: пользователь вводит комментарий — и мы сохраняем всё в базу
@dp.message(TransactionForm.entering_description)
async def process_description(message: types.Message, state: FSMContext):
    description = None if message.text.strip() == "-" else message.text

    data = await state.get_data()
    user = db.get_user(message.from_user.id)

    db.add_transaction(
        user_id=user[0],
        category_id=data["category_id"],
        amount=data["amount"],
        description=description
    )

    await state.clear()

    if data["type"] == "expense" and user[3] is not None:  # user[3] — daily_limit
        spent_today = db.get_today_spent(user[0])
        remaining = user[3] - spent_today

        if remaining < 0:
            await message.answer(
                f"Записал! ✅\n"
                f"⚠️ Дневной лимит превышен на {abs(remaining):.2f}"
            )
        else:
            await message.answer(
                f"Записал! ✅\n"
                f"Осталось на сегодня: {remaining:.2f} из {user[3]}"
            )
    else:
        await message.answer("Записал! ✅")

@dp.message(F.text == "/history")
async def cmd_history(message: types.Message):
    user = db.get_user(message.from_user.id)
    transactions = db.get_transactions(user[0], limit=10)

    if not transactions:
        await message.answer("Пока нет ни одной записи. Добавь первую через /add")
        return

    lines = ["Последние операции:\n"]
    for tx in transactions:
        tx_id, amount, category_name, category_type, date, description = tx
        sign = "+" if category_type == "income" else "-"
        line = f"{sign}{amount} — {category_name} ({date[:10]})"
        if description:
            line += f"\n   💬 {description}"
        lines.append(line)

    await message.answer("\n".join(lines))

@dp.message(F.text.startswith("/setlimit"))
async def cmd_set_limit(message: types.Message):
    parts = message.text.split()

    if len(parts) != 2:
        await message.answer("Использование: /setlimit 1500\n(укажи сумму дневного лимита после команды)")
        return

    try:
        limit_amount = float(parts[1])
    except ValueError:
        await message.answer("Это не похоже на число. Пример: /setlimit 1500")
        return

    user = db.get_user(message.from_user.id)
    db.set_daily_limit(user[0], limit_amount)
    await message.answer(f"Дневной лимит установлен: {limit_amount}")

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