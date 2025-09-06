from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from app.db.session import SessionLocal
from app.repositories.exchange_repo import set_rate

router = Router()

class RateFlow(StatesGroup):
    waiting_value = State()

@router.message(F.text == "/set_rate")
async def cmd_set_rate(message: Message, state: FSMContext):
    await message.answer("أرسل سعر الصرف الجديد:")
    await state.set_state(RateFlow.waiting_value)

@router.message(RateFlow.waiting_value)
async def process_rate_value(message: Message, state: FSMContext):
    try:
        new_value = float(message.text.strip())
    except ValueError:
        await message.answer("أدخل رقم صالح.")
        return

    db = SessionLocal()
    set_rate(db, new_value)
    await state.clear()
    await message.answer(f"تم تحديث سعر الصرف إلى {new_value}")
