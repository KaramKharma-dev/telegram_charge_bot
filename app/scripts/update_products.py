# app/scripts/update_products.py
from pathlib import Path
import json
from decimal import Decimal, InvalidOperation
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.db.session import SessionLocal
from app.models.product import Product

JSON_FILE = Path(__file__).parent / "products.json"
SAFE_MAX_PRICE = Decimal("1000000")  # حد أعلى منطقي للسعر

def to_decimal(x, q="0.00000001"):
    try:
        d = Decimal(str(x))
        _ = d + 0
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

def update_products_from_json():
    db: Session = SessionLocal()
    updated = 0
    skipped_invalid = 0
    not_found = 0
    try:
        data = json.loads(JSON_FILE.read_text(encoding="utf-8"))
        for p in data:
            if not isinstance(p, dict):
                not_found += 1
                continue

            min_qty, max_qty = parse_qty(p.get("qty_values"))
            cost = to_decimal(p.get("price"), q="0.00000001")

            if cost <= 0 or cost > SAFE_MAX_PRICE:
                print(f"⏩ تخطي منتج بسعر غير منطقي: id={p.get('id')} name={p.get('name')} price={p.get('price')}")
                skipped_invalid += 1
                continue

            filters = [Product.name == (p.get("name", "").strip())]
            if hasattr(Product, "num"):
                try:
                    pid = int(p["id"]) if "id" in p and str(p["id"]).strip() != "" else None
                except Exception:
                    pid = None
                if pid is not None:
                    filters.append(getattr(Product, "num") == pid)

            q = db.query(Product).filter(or_(*filters))
            obj = q.first()

            if not obj:
                not_found += 1
                continue

            # حفظ القيم القديمة
            old_cost = obj.cost_per_unit_usd
            old_min = obj.min_qty
            old_max = obj.max_qty
            old_active = obj.is_active

            # تعديل الحقول المسموح فيها فقط
            obj.name = p.get("name", "").strip()
            obj.unit_label = str(p.get("product_type", "")).strip()
            obj.cost_per_unit_usd = cost
            obj.min_qty = (min_qty or 0)
            obj.max_qty = max_qty
            obj.is_active = bool(p.get("available", False))
            if hasattr(Product, "num") and "id" in p:
                try:
                    setattr(obj, "num", int(p["id"]))
                except Exception:
                    pass

            updated += 1
            print(
                f"✏️ {obj.name}:\n"
                f"   السعر: {old_cost} → {obj.cost_per_unit_usd}\n"
                f"   min_qty: {old_min} → {obj.min_qty}\n"
                f"   max_qty: {old_max} → {obj.max_qty}\n"
                f"   فعال: {old_active} → {obj.is_active}"
            )

        db.commit()
        print(f"✅ تم تحديث {updated} منتج، وتخطي أسعار غير منطقية {skipped_invalid}، وعدم العثور على {not_found}.")
    except Exception as e:
        db.rollback()
        print(f"❌ خطأ أثناء التحديث: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    update_products_from_json()
