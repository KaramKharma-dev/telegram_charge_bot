from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy.orm import Session
from sqlalchemy import select
from decimal import Decimal, ROUND_DOWN
from datetime import datetime

from app.db.session import SessionLocal
from app.models.wallet_transaction import WalletTransaction
from app.models.wallet import Wallet
from app.models.user import User

router = Router()

def db_session() -> Session:
    return SessionLocal()

@router.callback_query(F.data.startswith("adm_approve:"))
async def admin_approve_topup(callback: CallbackQuery):
    db = db_session()
    try:
        tx_id = int(callback.data.split(":")[1])
        txn = db.get(WalletTransaction, tx_id)
        if not txn:
            await callback.answer("❌ الطلب غير موجود", show_alert=True); return
        if txn.status == "approved":
            await callback.answer("تمت الموافقة مسبقاً", show_alert=True); return
        if txn.status == "rejected":
            await callback.answer("مرفوض مسبقاً", show_alert=True); return
        if txn.direction != "credit":
            await callback.answer("نوع الحركة غير صالح للشحن", show_alert=True); return

        # قفل صفّ المحفظة لمنع سباقات التحديث
        wallet = db.execute(
            select(Wallet).where(Wallet.id == txn.wallet_id).with_for_update()
        ).scalar_one_or_none()
        if wallet is None:
            await callback.answer("محفظة غير موجودة", show_alert=True); return

        # تعديل الرصيد بذريّة
        new_balance = (Decimal(wallet.balance) + Decimal(txn.amount_usd)).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
        wallet.balance = new_balance

        # تحديث بيانات العملية
        txn.status = "approved"
        txn.wallet_balance_after = new_balance
        if txn.approved_at is None:
            txn.approved_at = datetime.utcnow()

        db.commit()

        # إشعار المستخدم
        user = db.get(User, wallet.user_id)
        if user and user.tg_id:
            await callback.bot.send_message(
                user.tg_id,
                f"✅ تم قبول طلب الشحن #{tx_id} وإضافة {txn.amount_usd} USD إلى رصيدك.",
                parse_mode="HTML"
            )

        await callback.message.edit_text(f"✅ تمت الموافقة على طلب #{tx_id}.")
        await callback.answer("تمت الموافقة")
    except Exception:
        db.rollback()
        await callback.answer("حصل خطأ غير متوقع", show_alert=True)
        # اختياري: سجل الخطأ
        # import logging; logging.exception("approve_topup failed")
    finally:
        db.close()

@router.callback_query(F.data.startswith("adm_reject:"))
async def admin_reject_topup(callback: CallbackQuery):
    db = db_session()
    try:
        tx_id = int(callback.data.split(":")[1])
        txn = db.get(WalletTransaction, tx_id)
        if not txn:
            await callback.answer("❌ الطلب غير موجود", show_alert=True); return
        if txn.status == "rejected":
            await callback.answer("تم الرفض مسبقاً", show_alert=True); return
        if txn.status == "approved":
            await callback.answer("تمت الموافقة سابقاً", show_alert=True); return

        txn.status = "rejected"
        db.commit()

        wallet = db.get(Wallet, txn.wallet_id)
        user = db.get(User, wallet.user_id) if wallet else None
        if user and user.tg_id:
            await callback.bot.send_message(
                user.tg_id,
                f"🔴 تم رفض طلب الشحن #{tx_id}.",
                parse_mode="HTML"
            )

        await callback.message.edit_text(f"❌ تم رفض طلب #{tx_id}.")
        await callback.answer("تم الرفض")
    except Exception:
        db.rollback()
        await callback.answer("حصل خطأ غير متوقع", show_alert=True)
    finally:
        db.close()
