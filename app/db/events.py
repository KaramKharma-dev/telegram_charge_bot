from decimal import Decimal
from datetime import datetime
from sqlalchemy import event
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.models.wallet import Wallet
from app.models.wallet_transaction import WalletTransaction

@event.listens_for(Session, "before_flush")
def apply_wallet_txn_on_approve(session: Session, flush_context, instances):
    for obj in list(session.dirty):
        if not isinstance(obj, WalletTransaction):
            continue

        insp = inspect(obj)
        if "status" not in insp.attrs:
            continue

        hist = insp.attrs.status.history
        if not hist.has_changes():
            continue

        # تغيير الحالة إلى approved الآن ولم تكن approved سابقًا
        if obj.status == "approved" and (not hist.deleted or hist.deleted[-1] != "approved"):
            wallet = session.get(Wallet, obj.wallet_id)
            if wallet is None:
                continue

            # طبّق الحركة مرة واحدة
            amount = Decimal(obj.amount_usd)
            if obj.direction == "credit":
                wallet.balance = (Decimal(wallet.balance) + amount).quantize(Decimal("0.01"))
            else:  # debit
                wallet.balance = (Decimal(wallet.balance) - amount).quantize(Decimal("0.01"))
                if wallet.balance < 0:
                    wallet.balance = Decimal("0.00")

            obj.wallet_balance_after = wallet.balance
            if obj.approved_at is None:
                obj.approved_at = datetime.utcnow()
