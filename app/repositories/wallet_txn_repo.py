# app/repositories/wallet_txn_repo.py
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.wallet_transaction import WalletTransaction
from app.models.wallet import Wallet

class DuplicateOperationRefError(Exception):
    """رقم العملية مستخدم من قبل"""

def create_pending_topup(
    db: Session,
    *,
    wallet_id: int,
    topup_method_id: int,
    amount_usd: Decimal,
    op_ref: str | None = None,
    note: str | None = None,
) -> WalletTransaction:
    # تحقّق مسبق سريع (يحميك قبل commit، وقد يفوت سباقات نادرة)
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
        # في حال سباق حالات وتخطّى التحقق المسبق
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
