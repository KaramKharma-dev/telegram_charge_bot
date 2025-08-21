# app/scripts/import_and_update_products.py
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


def update_profit():
    db = SessionLocal()
    try:
        products = db.query(Product).all()
        for product in products:
            if product.cost_per_unit_usd is not None:
                product.profit = Decimal(product.cost_per_unit_usd) * Decimal("0.10")
        db.commit()
        print(f"تم تحديث profit في {len(products)} صف.")
    finally:
        db.close()


def update_profit_dealer():
    db = SessionLocal()
    try:
        products = db.query(Product).all()
        for product in products:
            if product.cost_per_unit_usd is not None:
                product.profit_dealer = Decimal(product.cost_per_unit_usd) * Decimal("0.05")
        db.commit()
        print(f"تم تحديث profit_dealer في {len(products)} صف.")
    finally:
        db.close()


# ------- تحديث التصنيفات في النهاية -------
# المجموعتان المستهدفتان
target_chat = [
    227, 3288, 3182, 3265, 15, 3456, 3245, 73, 45, 3286, 151, 152, 153, 154, 155,
    66, 230, 43, 56, 3179, 176, 19, 20, 69, 54, 3252, 3253, 3254, 3255, 3256,
    3269, 3455, 3021, 3404, 193, 33, 26, 67, 3100, 55, 3206, 3483, 3144, 49,
    3024, 60, 31, 3260, 32, 3181, 16, 3264, 3479, 3308, 68, 48, 3475, 3412, 70,
    194, 3010, 254, 59, 3, 3306, 3099, 119, 120, 121, 122, 123, 124, 125, 126,
    3471, 3472, 3247, 28, 3307, 197, 198, 199, 200, 3431, 3432, 3433, 3434,
    3435, 3436, 3437, 63, 3031, 3032, 3033, 3034, 3035, 3036, 39, 3250, 42,
    3251, 62, 3298, 46, 3175, 3028, 41, 3469, 3410, 211, 3262, 17, 3287, 64,
    3176, 2, 195, 3143, 3258, 3055, 3029, 50, 180, 53, 27, 177, 3120, 25, 110,
    111, 112, 113, 114, 118, 3409, 71, 3052, 3294, 3291, 3023, 38, 24, 18, 3290,
    208, 209, 210, 3285, 3188, 34, 61, 3124, 13, 3476, 3477, 261, 3406, 260,
    3304, 3244, 12, 252, 3292, 3201, 3202, 3203, 3204, 3205,
    29, 30, 37, 40, 44, 47, 57, 58, 61, 156, 157, 158, 159, 160, 161, 162, 163,
    179, 189, 3215, 3216, 3245, 3246, 3247, 3250, 3251, 3258, 3277, 3285, 3289,
    3305, 3405, 3407, 3408, 3411, 3413, 3424, 3454, 3458, 3474, 3478, 3482,
    3484, 3485, 3486, 3487, 3488, 3489, 3490, 3491, 3492
]
target_game = [
    75,76,77,78,79,80,81,82,83,84,85,86,87,88,89,90,91,92,93,94,95,96,97,98,99,100,101,102,
    103,104,105,3270,3271,3272,3273,3274,231,232,233,234,235,236,237,238,3386,3387,3388,3389,
    3390,3391,239,240,241,242,243,244,245,3068,3069,3070,3071,3072,3073,246,247,248,249,250,
    251,3060,3061,3062,3063,3064,3065,3066,3038,3039,3040,3041,3042,3043,3164,3165,3166,106,
    107,108,170,171,172,173,174,175,3378,3379,3380,3381,3382,3383,3384,164,165,166,167,168,
    169,3233,3234,3235,3236,3217,3218,3219,3220,3221,3222,3223,3224,3225,3226,3227,3228,3229,
    3230,3231,3232,3328,3329,3330,3331,3332,3333,3334,3316,3317,3318,3319,3320,3321,3322,3323,
    3324,3325,3326,3327,3348,3349,3350,3351,3352,3359,3360,3361,3362,3363,3364,3365,3366,3367,
    3369,3370,3371,3372,3373,3374,3375,3376,3377,3046,3048,3049,3050,3051,3385,3411,3158,3159,
    3160,3161,3162,3237,3238,3239,3208,3209,3210,3211,3335,3336,3337,3338,3339,3340,3341,3342,
    3343,3344,3345,3346,3347,3353,3354,3355,3356,3357,3358,3191,3192,3193,3194,3195,3196,3197,
    3198,3199,3200,219,220,221,222,223,224,3241,3244,3425,3426,3427,3428,3169,3170,3171,3280,
    3281,3282
]

def update_categories():
    session: Session = SessionLocal()
    try:
        # تحديث chat
        session.query(Product).filter(Product.num.in_(target_chat)).update(
            {Product.category: "chat"}, synchronize_session=False
        )
        # تحديث game
        session.query(Product).filter(Product.num.in_(target_game)).update(
            {Product.category: "game"}, synchronize_session=False
        )
        session.commit()
        print("تم تحديث التصنيفات.")
    except Exception as e:
        session.rollback()
        print("خطأ عند تحديث التصنيفات:", e)
    finally:
        session.close()


if __name__ == "__main__":
    load_products_from_json()
    update_profit()
    update_profit_dealer()
    update_categories()
