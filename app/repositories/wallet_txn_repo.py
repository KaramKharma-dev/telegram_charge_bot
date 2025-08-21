# app/repositories/wallet_txn_repo.py
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.wallet_transaction import WalletTransaction
from app.models.wallet import Wallet

class DuplicateOperationRefError(Exception):
    """رقم العملية مستخدم من قبل"""

class AlreadyFinalizedError(Exception):
    """المعاملة مُنجزة سابقاً (approved/rejected)"""

def create_pending_topup(
    db: Session,
    *,
    wallet_id: int,
    topup_method_id: int,
    amount_usd: Decimal,
    op_ref: str | None = None,
    note: str | None = None,
) -> WalletTransaction:
    # تحقّق مسبق سريع
    if op_ref:
        exists = db.execute(
            select(WalletTransaction.id).where(
                WalletTransaction.operation_ref_or_txid == op_ref
            ).limit(1)
        ).scalar_one_or_none()
        if exists:
            raise DuplicateOperationRefError("رقم العملية مستخدم من قبل")

    tx = WalletTransaction(
        wallet_id=wallet_id,
        topup_method_id=topup_method_id,
        type="topup",
        direction="credit",
        amount_usd=amount_usd,
        status="pending",
        operation_ref_or_txid=op_ref,
        note=note,
    )
    db.add(tx)
    try:
        db.commit()
        db.refresh(tx)
        return tx
    except IntegrityError:
        db.rollback()
        raise DuplicateOperationRefError("رقم العملية مستخدم من قبل")

def list_user_topups(db: Session, user_id: int, limit: int = 10) -> list[WalletTransaction]:
    return (
        db.query(WalletTransaction)
        .join(Wallet, Wallet.id == WalletTransaction.wallet_id)
        .filter(Wallet.user_id == user_id, WalletTransaction.type == "topup")
        .order_by(WalletTransaction.created_at.desc())
        .limit(limit)
        .all()
    )

# --------- مساعدات داخلية ---------
def _load_topup_for_update(
    db: Session, *, tx_id: int | None = None, op_ref: str | None = None
) -> WalletTransaction:
    q = db.query(WalletTransaction).with_for_update()
    if tx_id is not None:
        tx = q.filter(WalletTransaction.id == tx_id).one_or_none()
    elif op_ref is not None:
        tx = q.filter(WalletTransaction.operation_ref_or_txid == op_ref).one_or_none()
    else:
        raise ValueError("يجب تمرير tx_id أو op_ref")
    if tx is None:
        raise ValueError("المعاملة غير موجودة")
    if tx.type != "topup":
        raise ValueError("المعاملة ليست topup")
    return tx

# --------- اعتماد التعبئة (الاسم المتوقع من sms.py) ---------
def approve_topup(
    db: Session,
    *,
    tx_id: int | None = None,
    op_ref: str | None = None,
    admin_note: str | None = None,
) -> WalletTransaction:
    """
    يجعل حالة المعاملة approved ويزيد رصيد المحفظة بمبلغها. آمن ضد التكرار.
    قابل للنداء بـ tx_id أو op_ref.
    """
    tx = _load_topup_for_update(db, tx_id=tx_id, op_ref=op_ref)

    if tx.status in ("approved", "rejected"):
        raise AlreadyFinalizedError("المعاملة مُنجزة سابقاً")

    # زيادة الرصيد
    wallet = db.query(Wallet).with_for_update().filter(Wallet.id == tx.wallet_id).one()
    wallet.balance = (wallet.balance or Decimal("0")) + (tx.amount_usd or Decimal("0"))

    # تحديث حالة العملية
    tx.status = "approved"
    if admin_note:
        tx.note = (tx.note or "") + (f" | {admin_note}" if tx.note else admin_note)

    db.add(wallet)
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx

# اختياري: رفض التعبئة
def reject_topup(
    db: Session,
    *,
    tx_id: int | None = None,
    op_ref: str | None = None,
    reason: str | None = None,
) -> WalletTransaction:
    tx = _load_topup_for_update(db, tx_id=tx_id, op_ref=op_ref)
    if tx.status in ("approved", "rejected"):
        raise AlreadyFinalizedError("المعاملة مُنجزة سابقاً")
    tx.status = "rejected"
    if reason:
        tx.note = (tx.note or "") + (f" | رفض: {reason}" if tx.note else f"رفض: {reason}")
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx

# توافقية: لو في كود قديم يستخدم اسم آخر
finalize_topup = approve_topup
