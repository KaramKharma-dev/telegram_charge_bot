from aiogram import Router, F
from aiogram.types import Message
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.repositories.user_repo import get_by_tg_id
from app.repositories.wallet_repo import get_wallet_usd

router = Router()

def db_session() -> Session:
    return SessionLocal()

@router.message(F.text == "/wallet")
async def wallet_cmd(message: Message):
    db = db_session()
    try:
        tg_id = message.from_user.id
        user = get_by_tg_id(db, tg_id)
        if not user:
            await message.answer("اكتب /start أولاً لإنشاء حساب.")
            return
        wallet = get_wallet_usd(db, user.id)
        if not wallet:
            await message.answer("لا توجد محفظة USD.")
            return
        await message.answer(f"الرصيد: <b>{wallet.balance}</b> {wallet.currency}")
    finally:
        db.close()
