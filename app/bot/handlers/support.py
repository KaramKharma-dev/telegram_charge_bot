from aiogram import Router, F
from aiogram.types import Message
from app.core.config import settings

router = Router()

@router.message(F.text == "📞 التواصل مع الدعم")
async def support_handler(message: Message):
    uname = (settings.SUPPORT_USERNAME or settings.ADMIN_USERNAME or "").strip().lstrip("@")
    if uname:
        await message.answer(
            f"📞 <b>الدعم الفني</b>\n\n"
            f"لأي استفسار أو مشكلة يرجى التواصل عبر المعرف التالي:\n"
            f"➡️ @{uname}\n\n"
            f"🕐 فريق الدعم جاهز لمساعدتك في أي وقت",
            parse_mode="HTML"
        )
    else:
        await message.answer("⚠️ لم يتم ضبط معرف الدعم. راجع ملف الإعدادات.")
