from aiogram import Router, F
from aiogram.types import Message
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.user import User
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter
import asyncio

router = Router()

ADMIN_ID = 1930157098  # ضع معرفك هنا

def db_session() -> Session:
    return SessionLocal()

@router.message(F.text.startswith("/broadcast"))
async def broadcast(message: Message, bot):
    if message.from_user.id != ADMIN_ID:
        return await message.answer("❌ ليس لديك صلاحية استخدام هذا الأمر.")

    text = message.text.replace("/broadcast", "").strip()
    if not text:
        return await message.answer("⚠️ أرسل الرسالة بعد الأمر، مثال:\n/broadcast أهلاً بالجميع!")

    db = db_session()
    try:
        users = db.query(User.tg_id).all()
        sent, failed = 0, 0

        for (tg_id,) in users:
            try:
                await bot.send_message(tg_id, text)
                sent += 1
            except TelegramForbiddenError:
                failed += 1
            except TelegramRetryAfter as e:
                await asyncio.sleep(e.retry_after)
                await bot.send_message(tg_id, text)
                sent += 1
            except Exception:
                failed += 1

        await message.answer(f"✅ تم الإرسال لـ {sent} مستخدم.\n⚠️ فشل الإرسال لـ {failed} مستخدم.")
    finally:
        db.close()
