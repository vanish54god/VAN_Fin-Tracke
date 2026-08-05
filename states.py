from aiogram.fsm.state import State, StatesGroup

class TransactionForm(StatesGroup):
    choosing_type = State()
    choosing_category = State()
    entering_amount = State()
    entering_description = State()
class SavingsForm(StatesGroup):
    entering_title = State()
    choosing_type = State()
    entering_amount = State()    