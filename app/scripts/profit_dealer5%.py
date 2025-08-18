from decimal import Decimal
from app.db.session import SessionLocal
from app.models.product import Product  # الجدول الصحيح

def update_profit():
    db = SessionLocal()
    try:
        products = db.query(Product).all()
        for product in products:
            if product.cost_per_unit_usd is not None:
                product.profit_dealer = Decimal(product.cost_per_unit_usd) * Decimal("0.05")
        db.commit()
        print(f"تم تحديث {len(products)} صف.")
    finally:
        db.close()

if __name__ == "__main__":
    update_profit()
