from aiogram import Router, F
from aiogram.types import Message
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.repositories.user_repo import get_by_tg_id, create_with_wallet
from app.bot.keyboards.common import main_menu  # NEW

router = Router()

def db_session() -> Session:
    return SessionLocal()

@router.message(F.text == "/start")
async def start_cmd(message: Message):
    db = db_session()
    try:
        tg_id = message.from_user.id
        name = message.from_user.full_name
        user = get_by_tg_id(db, tg_id)
        if not user:
            user = create_with_wallet(db, tg_id=tg_id, name=name)
            await message.answer(
                f"✨🎮 <b>مرحباً بك</b> <b>{name}</b> في عالم <b>Crypto Zone | Store</b> !\n"
                "💳 تم إنشاء <b>حسابك</b> بنجاح ✅\n"
                "⚡ الآن يمكنك شحن ألعابك وتطبيقاتك بسهولة وسرعة\n\n"
                "اختر من القائمة بالأسفل للبدء 👇",
                parse_mode="HTML",
                reply_markup=main_menu()
            )
        else:
            await message.answer(
                f"🎮 <b>مرحباً مجدداً</b> <b>{name}</b>\n"
                "🚀 حسابك جاهز لخدمتك، ابدأ الشحن الآن",
                parse_mode="HTML",
                reply_markup=main_menu()
            )

    finally:
        db.close()
