from decimal import Decimal
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.wallet_transaction import WalletTransaction
from app.models.wallet import Wallet

# استثناءات
class DuplicateOperationRefError(Exception):
    """رقم العملية مستخدم من قبل في محفظة مختلفة"""

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
    """
    ينشئ عملية pending. Idempotent على op_ref ضمن نفس المحفظة:
    - إذا وُجدت عملية بنفس op_ref ونفس wallet_id → يعيدها كما هي.
    - إذا وُجدت بنفس op_ref ولكن wallet_id مختلف → يرمي DuplicateOperationRefError.
    - إذا op_ref فارغ أو غير موجود سابقاً → ينشئ سجل جديد.
    """
    if op_ref:
        existing = db.execute(
            select(WalletTransaction).where(WalletTransaction.operation_ref_or_txid == op_ref)
        ).scalar_one_or_none()
        if existing:
            if int(existing.wallet_id) != int(wallet_id):
                raise DuplicateOperationRefError("رقم العملية مستخدم من قبل")
            # نفس المحفظة → idempotent
            return existing

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
    يملأ status, wallet_balance_after, approved_at.
    Idempotent: إذا كانت Approved يُعاد السجل كما هو.
    """
    tx = db.execute(
        select(WalletTransaction).where(WalletTransaction.id == tx_id).with_for_update()
    ).scalar_one_or_none()
    if tx is None:
        raise TopupNotFoundError(f"tx {tx_id} not found")

    status = (tx.status or "").lower()
    if status == "approved":
        return tx
    if status != "pending":
        raise TopupNotPendingError(f"tx {tx_id} status is {tx.status}")

    wallet = db.execute(
        select(Wallet).where(Wallet.id == tx.wallet_id).with_for_update()
    ).scalar_one()

    wallet.balance = (Decimal(wallet.balance or 0) + Decimal(tx.amount_usd or 0))
    tx.status = "approved"
    tx.wallet_balance_after = wallet.balance
    tx.approved_at = datetime.utcnow()

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
