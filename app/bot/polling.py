import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.core.config import settings
from app.bot.handlers.start import router as start_router
from app.bot.handlers.wallet import router as wallet_router
from app.bot.handlers.products import router as products_router
from app.bot.handlers.menu import router as menu_router
from app.bot.handlers import admin_topup_handlers, admin_broadcast

async def main():
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.include_router(start_router)
    dp.include_router(wallet_router)
    dp.include_router(menu_router)
    dp.include_router(admin_topup_handlers.router)
    dp.include_router(products_router)
    dp.include_router(admin_broadcast.router)

    print("🚀 Bot polling started...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
