# app/repositories/product_repo.py
from sqlalchemy.orm import Session
from app.models.product import Product

def list_active_by_category(db: Session, category: str):
    """
    إرجاع قائمة المنتجات الفعّالة حسب التصنيف
    """
    return (
        db.query(Product)
        .filter(Product.category == category, Product.is_active == True)
        .order_by(Product.name.asc())
        .all()
    )

def get_by_id(db: Session, product_id: int):
    """
    إرجاع منتج واحد حسب ID
    """
    return db.query(Product).filter(Product.id == product_id).first()
