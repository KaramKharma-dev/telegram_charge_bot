import asyncio
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from sqladmin import Admin
from starlette.middleware.sessions import SessionMiddleware
from pathlib import Path 

from app.core.config import settings
from app.db.session import engine
from app.bot.handlers.start import router as start_router
from app.bot.handlers.wallet import router as wallet_router
from app.bot.handlers.products import router as products_router

from app.admin.auth import AdminAuth
from app.admin.views import (
    UserAdmin, WalletAdmin, TopupMethodAdmin, WalletTxnAdmin,
    ProductAdmin, OrderAdmin, ExchangeRateAdmin, LogAdmin
)

from app.bot.handlers.menu import router as menu_router
from app.bot.handlers import admin_topup_handlers
from aiogram.types import BotCommand
from app.bot.handlers import admin_broadcast
from app.admin.stats_view import StatsView
app = FastAPI(title="Telegram Charge Bot API")
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

# ✅ تجهيز مجلد static وربطه
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

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

admin = Admin(app, engine, authentication_backend=AdminAuth(settings.SECRET_KEY))
admin.add_view(UserAdmin)
admin.add_view(WalletAdmin)
admin.add_view(TopupMethodAdmin)
admin.add_view(WalletTxnAdmin)
admin.add_view(ProductAdmin)
admin.add_view(OrderAdmin)
admin.add_view(ExchangeRateAdmin)
admin.add_view(LogAdmin)
admin.add_view(StatsView)  # صفحة الإحصائيات

@app.on_event("startup")
async def on_startup():
    if settings.BOT_MODE == "polling":
        # ضبط أوامر البوت في تيليغرام
        commands = [
            BotCommand(command="start", description="بدء"),
        ]
        await bot.set_my_commands(commands)
        asyncio.create_task(dp.start_polling(bot))

@app.get("/")
async def root():
    return {"status": "ok"}
