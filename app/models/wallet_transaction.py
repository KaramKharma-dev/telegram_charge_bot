from sqlalchemy import (
    BigInteger, Column, DateTime, DECIMAL, ForeignKey, String,
    UniqueConstraint, Index, Enum
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.session import Base

class WalletTransaction(Base):
    __tablename__ = "wallet_transactions"
    __table_args__ = (
        UniqueConstraint("operation_ref_or_txid", name="uq_wallettxn_opref"),
        UniqueConstraint("idempotency_key", name="uq_wallettxn_idemkey"),
        Index("ix_wallettxn_wallet_created", "wallet_id", "created_at"),
        Index("ix_wallettxn_status", "status"),
    )

    id = Column(BigInteger, primary_key=True)

    wallet_id = Column(BigInteger, ForeignKey("wallets.id"), nullable=False, index=True)
    topup_method_id = Column(BigInteger, ForeignKey("topup_methods.id"), nullable=True, index=True)

    type = Column(
        Enum("topup", "order", "refund", "admin_adjustment", name="wallettxn_type"),
        nullable=False
    )
    direction = Column(
        Enum("credit", "debit", name="wallettxn_direction"),
        nullable=False
    )
    amount_usd = Column(DECIMAL(18, 2), nullable=False)

    status = Column(
        Enum("pending", "approved", "rejected", name="wallettxn_status"),
        nullable=False,
        server_default="pending"
    )

    operation_ref_or_txid = Column(String(128), nullable=True)
    related_order_id = Column(BigInteger, ForeignKey("orders.id"), nullable=True, index=True)
    idempotency_key = Column(String(64), nullable=True)
    note = Column(String(255), nullable=True)
    wallet_balance_after = Column(DECIMAL(18, 2), nullable=True)

    created_at = Column(DateTime, nullable=False, server_default=func.now())
    approved_at = Column(DateTime, nullable=True)

    # علاقات
    wallet = relationship("Wallet", back_populates="transactions")
    topup_method = relationship("TopupMethod", back_populates="wallet_transactions")
    related_order = relationship("Order", back_populates="wallet_transactions")
