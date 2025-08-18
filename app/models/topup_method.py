from sqlalchemy import BigInteger, Boolean, Column, DateTime, String
from sqlalchemy.dialects.mysql import JSON as MySQLJSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.session import Base
from sqlalchemy import Text
class TopupMethod(Base):
    __tablename__ = "topup_methods"

    id = Column(BigInteger, primary_key=True)
    name = Column(String(50), nullable=False)
    details = Column(MySQLJSON, nullable=True)  # (phone, address…)
    is_active = Column(Boolean, nullable=False, server_default="1")
    image = Column(String(255), nullable=True)
    barcode = Column(String(255), nullable=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    wallet_transactions = relationship("WalletTransaction", back_populates="topup_method")
