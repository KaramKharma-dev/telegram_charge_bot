from sqlalchemy.orm import Session
from app.models.wallet import Wallet

def get_wallet_usd(db: Session, user_id: int) -> Wallet | None:
    return (
        db.query(Wallet)
        .filter(Wallet.user_id == user_id, Wallet.currency == "USD")
        .one_or_none()
    )
