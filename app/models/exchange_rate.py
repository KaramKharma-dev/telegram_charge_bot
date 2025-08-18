# app/models/exchange_rate.py
from sqlalchemy import BigInteger, CHAR, Column, DateTime, DECIMAL, UniqueConstraint, Index
from sqlalchemy.sql import func
from app.db.session import Base

class ExchangeRate(Base):
    __tablename__ = "exchange_rate"
    __table_args__ = (
        UniqueConstraint("from_currency", "to_currency", name="uq_exch_from_to"),
        Index("ix_exch_from_to", "from_currency", "to_currency"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    from_currency = Column(CHAR(3), nullable=False)   # مثال: SYP
    to_currency = Column(CHAR(3), nullable=False)     # مثال: USD
    value = Column(DECIMAL(18, 8), nullable=False)    # سعر 1 to_currency بوحدة from_currency
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<ExchangeRate {self.from_currency}->{self.to_currency}={self.value}>"
