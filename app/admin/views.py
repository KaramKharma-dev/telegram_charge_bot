from sqladmin import ModelView
from app.models.user import User
from app.models.wallet import Wallet
from app.models.topup_method import TopupMethod
from app.models.wallet_transaction import WalletTransaction
from app.models.product import Product
from app.models.order import Order
from app.models.exchange_rate import ExchangeRate
from app.models.log import Log
from markupsafe import Markup
from sqlalchemy import select
from decimal import Decimal, ROUND_DOWN
from datetime import datetime
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.core.config import settings

from app.db.session import SessionLocal

from decimal import Decimal

class UserAdmin(ModelView, model=User):
    column_list = [
        User.id,
        User.tg_id,
        User.name,
        "wallet_usd",  # نص وليس User.wallet_usd
        User.country,
        User.is_blocked,
        User.created_at,
    ]

    column_labels = {"wallet_usd": "Wallet USD"}

    column_formatters = {
        "wallet_usd": lambda m, a: m.wallet_usd
    }
    column_formatters_detail = column_formatters

class WalletAdmin(ModelView, model=Wallet):
    column_list = [Wallet.id, "user_name", Wallet.currency, Wallet.balance, Wallet.created_at]
    column_labels = {"user_name": "User"}



class TopupMethodAdmin(ModelView, model=TopupMethod):
    column_list = [TopupMethod.id, TopupMethod.name, TopupMethod.is_active, TopupMethod.created_at]

class WalletTxnAdmin(ModelView, model=WalletTransaction):
    column_list = [
        WalletTransaction.id,
        WalletTransaction.type,
        WalletTransaction.direction,
        WalletTransaction.amount_usd,
        WalletTransaction.status,
        WalletTransaction.operation_ref_or_txid,
        WalletTransaction.created_at,
    ]

    async def on_model_change(self, data, model: WalletTransaction, is_created: bool, request):
        # خزّن الحالة القديمة لمنع التكرار
        if is_created or not model.id:
            request.state._old_status = None
            return
        db = SessionLocal()
        try:
            existing = db.get(WalletTransaction, model.id)
            request.state._old_status = existing.status if existing else None
        finally:
            db.close()

    async def after_model_change(self, data, model: WalletTransaction, is_created: bool, request):
        old_status = getattr(request.state, "_old_status", None)
        new_status = model.status

        # لا شيء إذا لم تتغير الحالة
        if not is_created and old_status == new_status:
            return

        # نفّذ منطق اعتماد الرصيد فقط عند انتقال أول مرة إلى approved
        if new_status == "approved" and old_status != "approved":
            db = SessionLocal()
            try:
                # تأكد أن العملية ائتمان
                if model.direction != "credit":
                    # لا نخصم هنا من الـ Admin Panel. ائتمانات فقط.
                    pass
                else:
                    # اقفل صفّ المحفظة
                    wallet = db.execute(
                        select(Wallet).where(Wallet.id == model.wallet_id).with_for_update()
                    ).scalar_one_or_none()
                    if wallet:
                        new_balance = (Decimal(wallet.balance) + Decimal(model.amount_usd)).quantize(
                            Decimal("0.01"), rounding=ROUND_DOWN
                        )
                        wallet.balance = new_balance
                        # حدّث حقول العملية في القاعدة أيضًا
                        tx = db.get(WalletTransaction, model.id)
                        if tx:
                            tx.wallet_balance_after = new_balance
                            if tx.approved_at is None:
                                tx.approved_at = datetime.utcnow()
                        db.commit()
            except Exception:
                db.rollback()
                raise
            finally:
                db.close()

        # إرسال الإشعار للمستخدم
        db = SessionLocal()
        user = None
        try:
            wallet = db.get(Wallet, model.wallet_id)
            if wallet:
                user = db.get(User, wallet.user_id)
        finally:
            db.close()

        if user and user.tg_id:
            bot = Bot(
                token=settings.BOT_TOKEN,
                default=DefaultBotProperties(parse_mode=ParseMode.HTML),
            )
            try:
                if new_status == "approved":
                    await bot.send_message(
                        user.tg_id,
                        f"✅ تم قبول طلب الشحن رقم <b>#{model.id}</b>\n"
                        f"📥 أضيف إلى رصيدك: <b>{model.amount_usd} USD</b>."
                    )
                elif new_status == "rejected":
                    await bot.send_message(
                        user.tg_id,
                        f"❌ تم رفض طلب الشحن رقم <b>#{model.id}</b>."
                    )
            finally:
                await bot.session.close()

class ProductAdmin(ModelView, model=Product):
    column_list = [
        Product.id,
        Product.name,
        Product.category,
        Product.unit_label,
        Product.is_active,
        Product.created_at,
    ]


    column_sortable_list = [
        Product.name,
        Product.category,
        Product.unit_label,
        Product.num,      
        Product.id,
        Product.created_at,
    ]

class OrderAdmin(ModelView, model=Order):
    column_list = [
        Order.id,
        Order.user_id,
        Order.product_name,
        Order.qty,
        "status_colored",
        Order.created_at
    ]

    column_labels = {"status_colored": "Status"}

    column_formatters = {
        "status_colored": lambda m, a: (
            Markup('<span style="color: red;">مرفوض</span>') if m.status in ["rejected", "failed"] else
            Markup('<span style="color: orange;">قيد الانتظار</span>') if m.status in ["pennding", "wait"] else
            Markup('<span style="color: green;">مكتمل</span>') if m.status == "completed" else
            m.status
        )
    }
    column_formatters_detail = column_formatters

class ExchangeRateAdmin(ModelView, model=ExchangeRate):
    column_list = [ExchangeRate.id, ExchangeRate.from_currency, ExchangeRate.to_currency, ExchangeRate.value]

class LogAdmin(ModelView, model=Log):
    column_list = [Log.id, Log.level, Log.source, Log.created_at]
