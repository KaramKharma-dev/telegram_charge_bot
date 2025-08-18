from sqlalchemy import BigInteger, Column, DateTime, DECIMAL, Enum, ForeignKey, Integer, String, Index, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.session import Base

class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        Index("ix_order_user_created", "user_id", "created_at"),
        Index("ix_order_uuid", "order_uuid", unique=True),
    )

    id = Column(BigInteger, primary_key=True)

    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    product_id = Column(BigInteger, ForeignKey("products.id"), nullable=False, index=True)

    # جديد
    provider_product_id = Column(String(50), nullable=False)   # من products.num
    order_uuid = Column(String(36), nullable=False)            # نولّده ونرسله للمزوّد
    provider_order_id = Column(String(64), nullable=True)      # يرجع من المزوّد
    provider_status = Column(String(20), nullable=True)        # wait/accept/reject
    provider_price_usd = Column(DECIMAL(18, 8), nullable=True) # price من الرد
    provider_payload = Column(Text, nullable=True)             # الرد الكامل JSON
    error_msg = Column(String(200), nullable=True)             # سبب الفشل إن وجد

    product_name = Column(String(120), nullable=False)
    qty = Column(Integer, nullable=False)
    target = Column(String(120), nullable=False)

    unit_price_usd = Column(DECIMAL(18, 8), nullable=False)
    total_price_usd = Column(DECIMAL(18, 8), nullable=False)

    status = Column(
        Enum("created", "sent", "completed", "failed", name="order_status"),
        nullable=False,
        server_default="created"
    )

    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="orders")
    product = relationship("Product", back_populates="orders")
    wallet_transactions = relationship("WalletTransaction", back_populates="related_order")
