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

def savings_list_keyboard(savings):
    """Клавиатура со списком накоплений + кнопка создания нового"""
    builder = InlineKeyboardBuilder()
    for s in savings:
        # s = (id, user_id, title, amount, type, updated_at)
        builder.button(text=f"{s[2]} — {s[3]}", callback_data=f"saving_{s[0]}")
    builder.button(text="➕ Создать новое", callback_data="saving_new")
    builder.adjust(1)  # по одной кнопке в ряд, для читаемости
    return builder.as_markup()

def savings_type_keyboard():
    """Клавиатура выбора типа: накопление или вложение"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🏦 Накопление", callback_data="savtype_savings")
    builder.button(text="📈 Вложение", callback_data="savtype_investment")
    builder.adjust(2)
    return builder.as_markup()

def savings_action_keyboard(saving_id):
    """Клавиатура выбора действия: пополнить или снять"""
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Пополнить", callback_data=f"savaction_add_{saving_id}")
    builder.button(text="➖ Снять", callback_data=f"savaction_withdraw_{saving_id}")
    builder.adjust(2)
    return builder.as_markup()