from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def main_menu() -> ReplyKeyboardMarkup:
    kb = [
        [KeyboardButton(text="💳 الرصيد"), KeyboardButton(text="➕ تعبئة رصيد")],
        [KeyboardButton(text="🎮 شحن لعبة"), KeyboardButton(text="💬 شحن تطبيق")],
        [KeyboardButton(text="🧾 سجل تعبئة المحفظة"),KeyboardButton(text="📦 سجل شحن التطبيقات")],
        [KeyboardButton(text="📞 التواصل مع الدعم")],
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
