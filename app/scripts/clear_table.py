from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.session import SessionLocal

TABLE_NAME = "products"  # عدل حسب الجدول

def clear_table():
    db: Session = SessionLocal()
    try:
        db.execute(text(f"TRUNCATE TABLE {TABLE_NAME}"))
        db.commit()
        print(f"✅ تم تفريغ الجدول {TABLE_NAME}")
    except Exception as e:
        db.rollback()
        print(f"❌ خطأ: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    clear_table()
