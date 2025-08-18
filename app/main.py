import asyncio
import shutil
from contextlib import asynccontextmanager
from pathlib import Path
from importlib.resources import files
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand

from sqladmin import Admin
import sqladmin

from app.core.config import settings
from app.db.session import engine
from app.bot.handlers.start import router as start_router
from app.bot.handlers.wallet import router as wallet_router
from app.bot.handlers.products import router as products_router
from app.bot.handlers.menu import router as menu_router
from app.bot.handlers import admin_topup_handlers, admin_broadcast

from app.admin.auth import AdminAuth
from app.admin.views import (
    UserAdmin, WalletAdmin, TopupMethodAdmin, WalletTxnAdmin,
    ProductAdmin, OrderAdmin, ExchangeRateAdmin, LogAdmin
)
from app.admin.stats_view import StatsView

# --- Bot & Dispatcher ---
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

# --- Lifespan ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.BOT_MODE == "polling":
        await bot.delete_webhook(drop_pending_updates=True)
        await bot.set_my_commands([BotCommand(command="start", description="بدء")])
        asyncio.create_task(dp.start_polling(bot))
    yield

# --- App ---
app = FastAPI(title="Telegram Charge Bot API", lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

# --- Static mounts ---
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)

# ✅ انسخ أصول SQLAdmin (مرة وحدة) داخل static/sqladmin
try:
    SQLADMIN_SRC = files("sqladmin").joinpath("static")
    SQLADMIN_DST = STATIC_DIR / "sqladmin"
    if SQLADMIN_SRC.is_dir():
        if SQLADMIN_DST.exists():
            shutil.rmtree(SQLADMIN_DST)  # احذف القديم لو موجود
        shutil.copytree(SQLADMIN_SRC, SQLADMIN_DST)
except Exception as e:
    print("⚠️ لم يتم نسخ static من sqladmin:", e)
# ✅ خدم مجلد static بالكامل (سيشمل الآن sqladmin/css/js)
app.mount("/assets", StaticFiles(directory=str(STATIC_DIR)), name="assets")

# --- Admin ---
admin = Admin(app, engine, authentication_backend=AdminAuth(settings.SECRET_KEY))
admin.add_view(UserAdmin)
admin.add_view(WalletAdmin)
admin.add_view(TopupMethodAdmin)
admin.add_view(WalletTxnAdmin)
admin.add_view(ProductAdmin)
admin.add_view(OrderAdmin)
admin.add_view(ExchangeRateAdmin)
admin.add_view(LogAdmin)
admin.add_view(StatsView)

@app.get("/")
async def root():
    return {"status": "ok"}
