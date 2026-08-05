import asyncio
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext

import database as db
from states import TransactionForm, SavingsForm
from keyboards import (
    type_keyboard, categories_keyboard,
    savings_list_keyboard, savings_type_keyboard, savings_action_keyboard
)

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

@dp.message(F.text == "/savings")
async def cmd_savings(message: types.Message):
    user = db.get_user(message.from_user.id)
    savings = db.get_savings(user[0])

    if not savings:
        await message.answer(
            "У тебя пока нет накоплений или вложений.",
            reply_markup=savings_list_keyboard(savings)
        )
        return

    total = sum(s[3] for s in savings)  # s[3] — amount
    await message.answer(
        f"Твои накопления и вложения (всего: {total:.2f}):\nВыбери, с чем работать:",
        reply_markup=savings_list_keyboard(savings)
    )

@dp.callback_query(F.data == "saving_new")
async def process_saving_new(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(SavingsForm.entering_title)
    await callback.message.edit_text("Как назовём? Например: «Вклад в банке» или «Акции Apple»")
    await callback.answer()

@dp.callback_query(F.data.startswith("saving_") & ~F.data.startswith("saving_new"))
async def process_saving_select(callback: types.CallbackQuery):
    saving_id = int(callback.data.split("_")[1])
    saving = db.get_saving_by_id(saving_id)

    await callback.message.edit_text(
        f"«{saving[2]}»\nТекущая сумма: {saving[3]:.2f}\nЧто делаем?",
        reply_markup=savings_action_keyboard(saving_id)
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("savaction_"))
async def process_saving_action(callback: types.CallbackQuery, state: FSMContext):
    _, action, saving_id = callback.data.split("_")
    saving_id = int(saving_id)

    await state.set_state(SavingsForm.entering_amount)
    await state.update_data(saving_id=saving_id, action=action)

    verb = "пополнить" if action == "add" else "снять"
    await callback.message.edit_text(f"Сколько хочешь {verb}?")
    await callback.answer()
    
@dp.message(SavingsForm.entering_title)
async def process_saving_title(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text)
    await state.set_state(SavingsForm.choosing_type)
    await message.answer("Это накопление или вложение?", reply_markup=savings_type_keyboard())

@dp.callback_query(SavingsForm.choosing_type, F.data.startswith("savtype_"))
async def process_saving_type(callback: types.CallbackQuery, state: FSMContext):
    saving_type = callback.data.split("_")[1]  # "savings" или "investment"
    data = await state.get_data()

    user = db.get_user(callback.from_user.id)
    saving_id = db.add_saving(user[0], data["title"], saving_type)

    await state.clear()
    await callback.message.edit_text(
        f"Создал «{data['title']}»! Теперь пополни его — введи сумму:"
    )
    await state.set_state(SavingsForm.entering_amount)
    await state.update_data(saving_id=saving_id, action="add")
    await callback.answer()

@dp.message(SavingsForm.entering_amount)
async def process_saving_amount(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text)
    except ValueError:
        await message.answer("Это не похоже на число. Попробуй ещё раз, например: 500")
        return

    data = await state.get_data()
    saving_id = data["saving_id"]
    action = data["action"]  # "add" или "withdraw"

    user = db.get_user(message.from_user.id)
    saving = db.get_saving_by_id(saving_id)

    if action == "withdraw" and amount > saving[3]:  # saving[3] — текущая сумма
        await message.answer(
            f"На счету только {saving[3]:.2f}, не могу снять {amount:.2f}. Введи сумму меньше."
        )
        return

    delta = amount if action == "add" else -amount
    db.update_saving_amount(saving_id, delta)

    # Автоматически создаём связанную транзакцию, чтобы бюджет оставался честным
    category_name = "Накопления" if action == "add" else "Снятие с накоплений"
    category = db.get_category_by_name(user[0], category_name)
    db.add_transaction(
        user_id=user[0],
        category_id=category[0],
        amount=amount,
        description=f"{'Пополнение' if action == 'add' else 'Снятие'}: {saving[2]}"
    )

    await state.clear()
    verb = "Пополнил" if action == "add" else "Снял с"
    await message.answer(f"{verb} «{saving[2]}» на {amount:.2f} ✅")

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