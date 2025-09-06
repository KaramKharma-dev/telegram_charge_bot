from aiogram import Router, F
from aiogram.types import Message
from sqlalchemy.orm import Session
from decimal import Decimal, InvalidOperation

from app.db.session import SessionLocal
from app.repositories.exchange_repo import get_rate, set_rate

router = Router()

ADMIN_ID = 1930157098  # غيّر لمعرفك
DEF_FROM = "SYP"
DEF_TO = "USD"

def db_session() -> Session:
    return SessionLocal()

# أمر جلب السعر
@router.message(F.text.regexp(r"^/get_rate(\s|$)"))
async def get_rate_cmd(message: Message):
    if message.from_user.id != ADMIN_ID:
        return await message.answer("❌ ليس لديك صلاحية.")
    db = db_session()
    try:
        value = get_rate(db, DEF_FROM, DEF_TO)
        if value is None:
            await message.answer("⚠️ لا يوجد سعر مسجل حالياً.")
        else:
            await message.answer(f"💱 1 {DEF_TO} = {value} {DEF_FROM}")
    finally:
        db.close()

# أمر تعديل السعر
@router.message(F.text.regexp(r"^/set_rate(\s|$)"))
async def set_rate_cmd(message: Message):
    if message.from_user.id != ADMIN_ID:
        return await message.answer("❌ ليس لديك صلاحية.")
    parts = (message.text or "").strip().split()
    if len(parts) != 2:
        return await message.answer("الاستخدام: /set_rate <VALUE>")

    try:
        new_value = Decimal(parts[1])
        if new_value <= 0:
            return await message.answer("⚠️ القيمة يجب أن تكون > 0.")
    except (InvalidOperation, ValueError):
        return await message.answer("⚠️ أدخل رقم صالح.")

    db = db_session()
    try:
        set_rate(db, new_value, DEF_FROM, DEF_TO)
        await message.answer(f"✅ تم تحديث السعر إلى {new_value} {DEF_FROM} لكل 1 {DEF_TO}")
    finally:
        db.close()
