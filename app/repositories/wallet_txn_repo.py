from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.wallet_transaction import WalletTransaction
from app.models.wallet import Wallet

# استثناءات مفيدة
class DuplicateOperationRefError(Exception):
    """رقم العملية مستخدم من قبل"""

class TopupNotPendingError(Exception):
    """لا يمكن اعتماد عملية ليست pending"""

class TopupNotFoundError(Exception):
    """عملية الشحن غير موجودة"""


def create_pending_topup(
    db: Session,
    *,
    wallet_id: int,
    topup_method_id: int,
    amount_usd: Decimal,
    op_ref: str | None = None,
    note: str | None = None,
) -> WalletTransaction:
    # تحقّق اختياري لمنع تكرار رقم العملية
    if op_ref:
        exists = (
            db.query(WalletTransaction.id)
            .filter(WalletTransaction.operation_ref_or_txid == op_ref)
            .limit(1)
            .first()
        )
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
    db.commit()
    db.refresh(tx)
    return tx


def approve_topup(db: Session, tx_id: int) -> WalletTransaction:
    """
    يعتمد عملية الشحن ويضيف المبلغ إلى رصيد المحفظة.
    Idempotent: إن كانت Approved يُعاد نفس السجل.
    يرفع TopupNotPendingError إن كانت الحالة ليست pending.
    """
    # اقفل صف العملية
    tx = db.execute(
        select(WalletTransaction)
        .where(WalletTransaction.id == tx_id)
        .with_for_update()
    ).scalar_one_or_none()
    if tx is None:
        raise TopupNotFoundError(f"tx {tx_id} not found")

    if (tx.status or "").lower() == "approved":
        return tx
    if (tx.status or "").lower() != "pending":
        raise TopupNotPendingError(f"tx {tx_id} status is {tx.status}")

    # اقفل المحفظة
    wallet = db.execute(
        select(Wallet).where(Wallet.id == tx.wallet_id).with_for_update()
    ).scalar_one()

    # حدث الرصيد والحالة
    wallet.balance = (Decimal(wallet.balance or 0) + Decimal(tx.amount_usd or 0))
    tx.status = "approved"

    db.add(wallet)
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


def list_user_topups(db: Session, user_id: int, limit: int = 10) -> list[WalletTransaction]:
    return (
        db.query(WalletTransaction)
        .join(Wallet, Wallet.id == WalletTransaction.wallet_id)
        .filter(Wallet.user_id == user_id, WalletTransaction.type == "topup")
        .order_by(WalletTransaction.created_at.desc())
        .limit(limit)
        .all()
    )
