from sqlalchemy import BigInteger, Column, DateTime, Enum, ForeignKey, String, Text, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.session import Base

class Log(Base):
    __tablename__ = "logs"
    __table_args__ = (
        Index("ix_logs_created", "created_at"),
    )

    id = Column(BigInteger, primary_key=True)
    level = Column(
        Enum("info", "warning", "error", name="log_level"),
        nullable=False
    )
    source = Column(String(50), nullable=False)
    message = Column(Text, nullable=False)

    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=True)
    order_id = Column(BigInteger, ForeignKey("orders.id"), nullable=True)
    wallet_txn_id = Column(BigInteger, ForeignKey("wallet_transactions.id"), nullable=True)

    created_at = Column(DateTime, nullable=False, server_default=func.now())

    # علاقات اختيارية
    user = relationship("User", backref="logs")
    order = relationship("Order", backref="logs")
    wallet_transaction = relationship("WalletTransaction", backref="logs")
