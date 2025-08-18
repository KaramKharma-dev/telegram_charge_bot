from sqlalchemy.orm import Session
from app.models.user import User
from app.models.wallet import Wallet

def get_by_tg_id(db: Session, tg_id: int) -> User | None:
    return db.query(User).filter(User.tg_id == tg_id).one_or_none()

def create_with_wallet(db: Session, *, tg_id: int, name: str | None) -> User:
    user = User(tg_id=tg_id, name=name or "User")
    db.add(user)
    db.flush()  # يولّد id

    wallet = Wallet(user_id=user.id, currency="USD", balance=0)
    db.add(wallet)
    db.commit()
    db.refresh(user)
    return user
