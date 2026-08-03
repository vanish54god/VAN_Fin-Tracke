from aiogram.utils.keyboard import InlineKeyboardBuilder

def type_keyboard():
    """Клавиатура выбора: трата или доход"""
    builder = InlineKeyboardBuilder()
    builder.button(text="💸 Трата", callback_data="type_expense")
    builder.button(text="💰 Доход", callback_data="type_income")
    builder.adjust(2)  # 2 кнопки в один ряд
    return builder.as_markup()

def categories_keyboard(categories):
    """Клавиатура со списком категорий. categories — результат db.get_categories()"""
    builder = InlineKeyboardBuilder()
    for cat in categories:
        # cat = (id, user_id, name, type)
        builder.button(text=cat[2], callback_data=f"cat_{cat[0]}")
    builder.adjust(2)
    return builder.as_markup()