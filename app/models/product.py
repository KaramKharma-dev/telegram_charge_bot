from sqlalchemy import BigInteger, Boolean, Column, DateTime, DECIMAL, Integer, String
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.session import Base
from sqlalchemy import BigInteger

class Product(Base):
    __tablename__ = "products"

    id = Column(BigInteger, primary_key=True)
    name = Column(String(120), nullable=False)
    num = Column(String(50), nullable=True)
    unit_label = Column(String(20), nullable=False)
    cost_per_unit_usd = Column(DECIMAL(23, 8), nullable=False)
    
    profit = Column(DECIMAL(18, 8), nullable=False)          # فئة 1
    profit_dealer = Column(DECIMAL(18, 8), nullable=True)    # فئة 2
    profit_dealer_2 = Column(DECIMAL(18, 8), nullable=True)  # فئة 3
    profit_dealer_3 = Column(DECIMAL(18, 8), nullable=True)  # فئة 4

    category = Column(String(50), nullable=True) 
    min_qty = Column(Integer, nullable=True, server_default="1")
    max_qty = Column(BigInteger, nullable=True)
    is_active = Column(Boolean, nullable=False, server_default="1")
    image = Column(String(255), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    orders = relationship("Order", back_populates="product")
