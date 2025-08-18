from sqlalchemy import BigInteger, Boolean, CHAR, Column, DateTime, ForeignKey, String
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.session import Base
from sqlalchemy.ext.hybrid import hybrid_property
from decimal import Decimal

class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True)
    tg_id = Column(BigInteger, unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    country = Column(CHAR(2), nullable=True)
    referrer_user_id = Column(BigInteger, ForeignKey("users.id"), nullable=True)
    is_blocked = Column(Boolean, nullable=False, default=False, server_default="0")
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    referrer = relationship("User", remote_side=[id], uselist=False)
    wallets = relationship("Wallet", back_populates="user", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="user", cascade="all, delete-orphan")

    @hybrid_property
    def wallet_usd(self):
        for w in self.wallets or []:
            if w.currency == "USD":
                return w.balance
        return Decimal("0.00")
