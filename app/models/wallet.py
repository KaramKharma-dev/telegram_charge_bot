from sqlalchemy import (
    BigInteger, CHAR, Column, DateTime, DECIMAL, ForeignKey,
    UniqueConstraint, CheckConstraint, Index
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.session import Base

class Wallet(Base):
    __tablename__ = "wallets"
    __table_args__ = (
        UniqueConstraint("user_id", "currency", name="uq_wallet_user_currency"),
        CheckConstraint("balance >= 0", name="ck_wallet_balance_non_negative"),
        Index("ix_wallet_user_created", "user_id", "created_at"),
    )

    id = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    currency = Column(CHAR(3), nullable=False, server_default="USD")
    balance = Column(DECIMAL(18, 2), nullable=False, server_default="0.00")
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    # العلاقات
    user = relationship("User", back_populates="wallets")
    transactions = relationship("WalletTransaction", back_populates="wallet")

    # اسم المستخدم لعرضه في الـ Admin
    @property
    def user_name(self):
        return self.user.name if self.user else None
