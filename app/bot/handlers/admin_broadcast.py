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

@router.message(F.text.regexp(r"^/set_tier(\s|$)"))
async def set_tier_cmd(message: Message):
    # صلاحية
    if message.from_user.id != ADMIN_ID:
        return await message.answer("❌ ليس لديك صلاحية استخدام هذا الأمر.")

    parts = (message.text or "").strip().split()
    db = db_session()
    try:
        tg_id = None
        tier = None

        # 1) بالرد على رسالة المستخدم: /set_tier 1..4
        if message.reply_to_message and len(parts) == 2:
            tier = parts[1]
            tg_id = message.reply_to_message.from_user.id

        # 2) تمـرير كِلاهما: /set_tier <tg_id> <1..4>
        elif len(parts) == 3:
            tg_id = int(parts[1])
            tier = parts[2]
        else:
            return await message.answer(
                "الاستخدام:\n"
                "• بالرد على المستخدم: /set_tier 1..4\n"
                "• أو: /set_tier <tg_id> <1..4>"
            )

        # تحقق من المرتبة
        try:
            tier = int(tier)
        except:
            return await message.answer("المرتبة يجب أن تكون رقماً بين 1 و 4.")
        if tier not in (1, 2, 3, 4):
            return await message.answer("القيم المسموحة: 1 أو 2 أو 3 أو 4.")

        # جلب المستخدم وتحديثه
        u = db.query(User).filter(User.tg_id == tg_id).first()
        if not u:
            return await message.answer(f"لم أجد مستخدماً بـ tg_id={tg_id}.")

        u.user_type = tier
        db.add(u)
        db.commit()

        await message.answer(f"تم ضبط مرتبة {u.name} (tg_id={tg_id}) إلى {tier}.")
    finally:
        db.close()

@router.message(F.text.regexp(r"^/get_tier(\s|$)"))
async def get_tier_cmd(message: Message):
    if message.from_user.id != ADMIN_ID:
        return await message.answer("❌ ليس لديك صلاحية استخدام هذا الأمر.")

    parts = (message.text or "").strip().split()
    db = db_session()
    try:
        tg_id = None

        # 1) بالرد على المستخدم
        if message.reply_to_message and len(parts) == 1:
            tg_id = message.reply_to_message.from_user.id

        # 2) بتمرير tg_id: /get_tier <tg_id>
        elif len(parts) == 2:
            tg_id = int(parts[1])
        else:
            return await message.answer(
                "الاستخدام:\n"
                "• بالرد على المستخدم: /get_tier\n"
                "• أو: /get_tier <tg_id>"
            )

        u = db.query(User).filter(User.tg_id == tg_id).first()
        if not u:
            return await message.answer(f"❌ لم أجد مستخدماً بـ tg_id={tg_id}.")

        await message.answer(
            f"👤 المستخدم: {u.name}\n"
            f"🆔 tg_id: {tg_id}\n"
            f"📊 المرتبة الحالية: {u.user_type}"
        )
    finally:
        db.close()
