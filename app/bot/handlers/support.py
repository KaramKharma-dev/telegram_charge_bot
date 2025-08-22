from aiogram import Router, F
from aiogram.types import Message
from app.core.config import settings

router = Router()

@router.message(F.text == "📞 التواصل مع الدعم")
async def support_handler(message: Message):
    uname = (settings.SUPPORT_USERNAME or "").strip().lstrip("@")
    if uname:
        await message.answer(f"للتواصل مع الدعم الفني يرجى مراسلة الأدمن:\n\n@{uname}")
    else:
        await message.answer("⚠️ لم يتم ضبط معرف الدعم. راجع ملف .env")
