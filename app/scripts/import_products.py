# app/scripts/import_products.py
from pathlib import Path
import json
from decimal import Decimal, InvalidOperation
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.product import Product

JSON_FILE = Path(__file__).parent / "products.json"
SAFE_MAX_PRICE = Decimal("1000000")  # حد أعلى منطقي للسعر

def to_decimal(x, q="0.00000001"):
    try:
        d = Decimal(str(x))
        _ = d + 0  # يتحقق أنه رقم حقيقي
        return d.quantize(Decimal(q))
    except (InvalidOperation, TypeError):
        return Decimal("0")

def parse_qty(qv):
    if isinstance(qv, dict):
        mn = qv.get("min")
        mx = qv.get("max")
        return (int(str(mn)) if mn and str(mn).strip() != "" else None,
                int(str(mx)) if mx and str(mx).strip() != "" else None)
    if isinstance(qv, list) and qv:
        try:
            return (int(str(qv[0])), int(str(qv[-1])))
        except Exception:
            return (None, None)
    try:
        v = int(str(qv))
        return (v, v)
    except Exception:
        return (None, None)

def load_products_from_json():
    db: Session = SessionLocal()
    inserted = 0
    skipped = 0
    try:
        data = json.loads(JSON_FILE.read_text(encoding="utf-8"))
        for p in data:
            if not isinstance(p, dict):
                skipped += 1
                continue

            min_qty, max_qty = parse_qty(p.get("qty_values"))
            cost = to_decimal(p.get("price"), q="0.00000001")

            # فلترة الأسعار الغير منطقية
            if cost <= 0 or cost > SAFE_MAX_PRICE:
                print(f"⏩ تخطي منتج بسعر غير منطقي: id={p.get('id')} name={p.get('name')} price={p.get('price')}")
                skipped += 1
                continue

            obj = Product(
                name=p.get("name", "").strip(),
                unit_label=str(p.get("product_type", "")).strip(),
                cost_per_unit_usd=cost,
                profit=Decimal("0"),
                min_qty=min_qty or 0,
                max_qty=max_qty,
                is_active=bool(p.get("available", False)),
                **({"num": int(p["id"])} if hasattr(Product, "num") and "id" in p else {}),
                **({"profit_dealer": Decimal("0")} if hasattr(Product, "profit_dealer") else {}),
            )

            q = db.query(Product).filter(Product.name == obj.name)
            if hasattr(Product, "num"):
                q = q.union_all(
                    db.query(Product).filter(getattr(Product, "num") == getattr(obj, "num", None))
                )

            if q.first():
                skipped += 1
                continue

            db.add(obj)
            inserted += 1

        db.commit()
        print(f"✅ تم إدخال {inserted} وتخطّي {skipped}.")
    except Exception as e:
        db.rollback()
        print(f"❌ خطأ أثناء الإدخال: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    load_products_from_json()
