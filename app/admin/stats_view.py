# app/admin/stats_view.py
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Tuple

from markupsafe import Markup
from sqlalchemy import func
from sqlalchemy.orm import Session
from sqladmin import BaseView, expose
from starlette.responses import HTMLResponse
import httpx

from app.db.session import SessionLocal
from app.models.wallet_transaction import WalletTransaction
from app.models.order import Order
from app.models.product import Product
from app.models.topup_method import TopupMethod  # لاستخدام اسم طريقة الشحن إن وجد FK
from app.models.wallet import Wallet

# إعدادات API المزوّد
_PROVIDER_PROFILE_URL = "https://api.jentel-cash.com/client/api/profile"
_PROVIDER_API_TOKEN = "ace7f794532f369ba7d8008a1782178cc082c808b82cb57c"


def _dec(v) -> Decimal:
    try:
        return Decimal(str(v or 0))
    except Exception:
        return Decimal("0")


def _fmt_money(v) -> str:
    d = _dec(v)
    return f"{d:,.2f}"


def _fmt_int(v) -> str:
    try:
        return f"{int(v or 0):,}"
    except Exception:
        return "0"


def _day_range(d: date) -> Tuple[datetime, datetime]:
    start = datetime.combine(d, datetime.min.time())
    end = start + timedelta(days=1)
    return start, end


def _month_range(d: date) -> Tuple[datetime, datetime]:
    start = d.replace(day=1)
    start_dt = datetime.combine(start, datetime.min.time())
    if start.month == 12:
        end_dt = datetime(d.year + 1, 1, 1)
    else:
        end_dt = datetime(d.year, d.month + 1, 1)
    return start_dt, end_dt


def _fetch_provider_profile() -> Tuple[Decimal, str]:
    """يرجع (الرصيد, الإيميل) من /client/api/profile."""
    try:
        headers = {"api-token": _PROVIDER_API_TOKEN, "Accept": "application/json"}
        with httpx.Client(timeout=10) as client:
            r = client.get(_PROVIDER_PROFILE_URL, headers=headers)
        r.raise_for_status()
        payload = r.json()
        bal = Decimal(str(payload.get("balance", "0") or "0"))
        email = str(payload.get("email") or "")
        return bal, email
    except Exception:
        return Decimal("0"), ""


class StatsView(BaseView):
    name = "لوحة الإحصائيات"
    icon = "fa fa-chart-line"
    category = "Dashboard"

    @expose("/stats", methods=["GET"])
    def page(self, request) -> Any:
        db: Session = SessionLocal()
        try:
            today = date.today()
            day_start, day_end = _day_range(today)
            month_start, month_end = _month_range(today)

            approved_col = getattr(WalletTransaction, "approved_at", WalletTransaction.created_at)

            # رصيد المزوّد + الإيميل
            provider_balance, provider_email = _fetch_provider_profile()

            # إجمالي رصيد محافظ المستخدمين
            _balance_col = None
            for cand in ("balance_usd", "usd_balance", "balance", "amount_usd", "usd"):
                if hasattr(Wallet, cand):
                    _balance_col = getattr(Wallet, cand)
                    break
            users_balance_total = db.query(func.coalesce(func.sum(_balance_col), 0)).scalar() if _balance_col is not None else 0

            # تعبئات الرصيد
            total_topups = db.query(func.coalesce(func.sum(WalletTransaction.amount_usd), 0)).filter(
                WalletTransaction.status == "approved",
                WalletTransaction.direction == "credit",
            ).scalar()

            topups_today = db.query(func.coalesce(func.sum(WalletTransaction.amount_usd), 0)).filter(
                WalletTransaction.status == "approved",
                WalletTransaction.direction == "credit",
                approved_col >= day_start, approved_col < day_end
            ).scalar()

            topups_month = db.query(func.coalesce(func.sum(WalletTransaction.amount_usd), 0)).filter(
                WalletTransaction.status == "approved",
                WalletTransaction.direction == "credit",
                approved_col >= month_start, approved_col < month_end
            ).scalar()

            # ===== تفصيل تعبئة الرصيد حسب طريقة الشحن =====
            # نحاول اكتشاف عمود الطريقة
            _method_col_name = None
            for cand in ("topup_method_id", "method_id", "payment_method_id", "topup_method", "method", "payment_method"):
                if hasattr(WalletTransaction, cand):
                    _method_col_name = cand
                    break

            if _method_col_name is None:
                # لا يوجد عمود طريقة: fallback إلى type
                topups_by_type: List[Tuple[str, Decimal]] = db.query(
                    (WalletTransaction.type).label("method_name"),
                    func.coalesce(func.sum(WalletTransaction.amount_usd), 0)
                ).filter(
                    WalletTransaction.status == "approved",
                    WalletTransaction.direction == "credit",
                ).group_by(WalletTransaction.type).all()
            else:
                method_col = getattr(WalletTransaction, _method_col_name)
                if _method_col_name.endswith("_id"):
                    # نفترض FK -> join على TopupMethod.id
                    topups_by_type = db.query(
                        func.coalesce(TopupMethod.name, "غير محدد"),
                        func.coalesce(func.sum(WalletTransaction.amount_usd), 0)
                    ).select_from(WalletTransaction).join(
                        TopupMethod, TopupMethod.id == method_col, isouter=True
                    ).filter(
                        WalletTransaction.status == "approved",
                        WalletTransaction.direction == "credit",
                    ).group_by(TopupMethod.name).all()
                else:
                    # العمود نصّي باسم الطريقة
                    topups_by_type = db.query(
                        func.coalesce(method_col, "غير محدد"),
                        func.coalesce(func.sum(WalletTransaction.amount_usd), 0)
                    ).filter(
                        WalletTransaction.status == "approved",
                        WalletTransaction.direction == "credit",
                    ).group_by(method_col).all()

            # الطلبات
            VALID_STATUSES = ("created", "sent", "completed")

            orders_count = db.query(func.count(Order.id)).filter(
                Order.status.in_(VALID_STATUSES)
            ).scalar()

            orders_total_usd = db.query(func.coalesce(func.sum(Order.total_price_usd), 0)).filter(
                Order.status.in_(VALID_STATUSES)
            ).scalar()

            orders_today_usd = db.query(func.coalesce(func.sum(Order.total_price_usd), 0)).filter(
                Order.status.in_(VALID_STATUSES),
                Order.created_at >= day_start, Order.created_at < day_end
            ).scalar()

            orders_month_usd = db.query(func.coalesce(func.sum(Order.total_price_usd), 0)).filter(
                Order.status.in_(VALID_STATUSES),
                Order.created_at >= month_start, Order.created_at < month_end
            ).scalar()

            # الربح
            profit_total = db.query(
                func.coalesce(func.sum(Product.profit * Order.qty), 0)
            ).select_from(Order).join(Product, Product.id == Order.product_id).filter(
                Order.status.in_(VALID_STATUSES)
            ).scalar()

            profit_today = db.query(
                func.coalesce(func.sum(Product.profit * Order.qty), 0)
            ).select_from(Order).join(Product, Product.id == Order.product_id).filter(
                Order.status.in_(VALID_STATUSES),
                Order.created_at >= day_start, Order.created_at < day_end
            ).scalar()

            profit_month = db.query(
                func.coalesce(func.sum(Product.profit * Order.qty), 0)
            ).select_from(Order).join(Product, Product.id == Order.product_id).filter(
                Order.status.in_(VALID_STATUSES),
                Order.created_at >= month_start, Order.created_at < month_end
            ).scalar()

            # أفضل المنتجات
            top_products = db.query(
                Order.product_name,
                func.count(Order.id).label("orders"),
                func.coalesce(func.sum(Order.qty), 0).label("qty_sum"),
                func.coalesce(func.sum(Order.total_price_usd), 0).label("usd_sum"),
            ).filter(
                Order.status.in_(VALID_STATUSES)
            ).group_by(
                Order.product_name
            ).order_by(
                func.coalesce(func.sum(Order.total_price_usd), 0).desc()
            ).limit(10).all()

            data: Dict[str, Any] = {
                "provider_balance": provider_balance,
                "provider_email": provider_email,

                "users_balance_total": _dec(users_balance_total),

                "total_topups": _dec(total_topups),
                "topups_today": _dec(topups_today),
                "topups_month": _dec(topups_month),

                "orders_count": int(orders_count or 0),
                "orders_total_usd": _dec(orders_total_usd),
                "orders_today_usd": _dec(orders_today_usd),
                "orders_month_usd": _dec(orders_month_usd),

                "profit_total": _dec(profit_total),
                "profit_today": _dec(profit_today),
                "profit_month": _dec(profit_month),

                "topups_by_type": [(t or "غير محدد", _dec(v)) for t, v in topups_by_type],
                "top_products": top_products,
                "today": today.strftime("%Y-%m-%d"),
                "month_start": month_start.strftime("%Y-%m-%d"),
            }

            # HTML/CSS
            html = Markup(f"""
<!doctype html>
<html dir="rtl" lang="ar">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <style>
    :root {{
      --bg: #0f172a; --card: #111827; --muted: #94a3b8; --text: #e5e7eb;
      --accent: #22d3ee; --accent-2: #60a5fa; --border: #1f2937;
      --table-stripe: rgba(255,255,255,0.03); --shadow: 0 10px 25px rgba(0,0,0,0.25);
      --radius: 14px;
    }}
    @media (prefers-color-scheme: light) {{
      :root {{ --bg:#f7f7fb; --card:#fff; --muted:#6b7280; --text:#0f172a; --accent:#0ea5e9; --accent-2:#2563eb; --border:#e5e7eb; --table-stripe:rgba(0,0,0,0.02); }}
    }}
    body {{
      margin:0; padding:24px; font-family:-apple-system, Segoe UI, Roboto, "Cairo", Tahoma, Arial, sans-serif;
      background: radial-gradient(1000px 600px at 100% -10%, rgba(34,211,238,0.08), transparent 60%),
                  radial-gradient(800px 500px at -10% 0%, rgba(96,165,250,0.08), transparent 60%),
                  var(--bg);
      color:var(--text);
    }}
    .header {{
      background: linear-gradient(90deg, rgba(34,211,238,0.20), rgba(96,165,250,0.20));
      border:1px solid var(--border); border-radius:var(--radius); padding:20px 18px; box-shadow:var(--shadow);
      display:flex; flex-wrap:wrap; justify-content:space-between; gap:12px; align-items:center;
    }}
    .header h2 {{ margin:0; font-size:22px; }}
    .meta {{ color:var(--muted); font-size:13px; }}
    .pill {{ display:inline-block; padding:2px 8px; border-radius:999px; font-size:12px; border:1px solid var(--border);
            background:rgba(34,211,238,0.10); color:var(--accent-2); }}

    .grid-cards {{ display:grid; grid-template-columns: repeat(auto-fit, minmax(240px,1fr)); gap:16px; margin:18px 0 22px 0; }}
    .card {{
      background:var(--card); border:1px solid var(--border); border-radius:var(--radius); padding:16px; box-shadow:var(--shadow);
      position:relative; overflow:hidden;
    }}
    .card::after {{
      content:""; position:absolute; inset:-20% -10% auto auto; width:160px; height:160px; transform: rotate(35deg);
      background: linear-gradient(180deg, transparent, rgba(34,211,238,0.10)); border-radius:24px; pointer-events:none;
    }}
    .card h4 {{ margin:0 0 8px 0; font-size:15px; color:var(--muted); }}
    .card .value {{ font-size:28px; font-weight:700; letter-spacing:0.2px; }}
    .card .sub {{ margin-top:6px; color:var(--muted); font-size:13px; }}

    .grid-2 {{ display:grid; grid-template-columns:1fr 1fr; gap:16px; }}
    @media (max-width: 1100px) {{ .grid-2 {{ grid-template-columns:1fr; }} }}

    table {{
      width:100%; border-collapse:separate; border-spacing:0; overflow:hidden;
      border:1px solid var(--border); border-radius:var(--radius); background:var(--card); box-shadow:var(--shadow);
    }}
    thead th {{ text-align:right; padding:12px; font-size:13px; color:var(--muted); border-bottom:1px solid var(--border);
               background: linear-gradient(180deg, rgba(255,255,255,0.02), transparent); }}
    tbody td {{ padding:12px; border-bottom:1px solid var(--border); font-size:14px; }}
    tbody tr:nth-child(odd) td {{ background: var(--table-stripe); }}
  </style>
</head>
<body>
  <section class="header">
    <h2>لوحة الإحصائيات</h2>
    <div class="meta">اليوم: {data['today']} <span class="pill">بداية الشهر: {data['month_start']}</span></div>
  </section>

  <section class="grid-cards">
    <div class="card">
      <h4>رصيدي عند المزوّد</h4>
      <div class="value">{_fmt_money(data['provider_balance'])} USD</div>
      <div class="sub">الحساب: {data['provider_email'] or 'غير متاح'} • المصدر: /profile</div>
    </div>
    <div class="card">
      <h4>إجمالي تعبئة الرصيد</h4>
      <div class="value">{_fmt_money(data['total_topups'])} USD</div>
      <div class="sub">اليوم: {_fmt_money(data['topups_today'])} • هذا الشهر: {_fmt_money(data['topups_month'])}</div>
    </div>
    <div class="card">
      <h4>أرصدة المستخدمين</h4>
      <div class="value">{_fmt_money(data['users_balance_total'])} USD</div>
      <div class="sub">إجمالي المتبقي في المحافظ</div>
    </div>
    <div class="card">
      <h4>مبيعات الشحن</h4>
      <div class="value">{_fmt_money(data['orders_total_usd'])} USD</div>
      <div class="sub">عدد الطلبات: {_fmt_int(data['orders_count'])} • اليوم: {_fmt_money(data['orders_today_usd'])} • هذا الشهر: {_fmt_money(data['orders_month_usd'])}</div>
    </div>
    <div class="card">
      <h4>الربح</h4>
      <div class="value">{_fmt_money(data['profit_total'])} USD</div>
      <div class="sub">اليوم: {_fmt_money(data['profit_today'])} • هذا الشهر: {_fmt_money(data['profit_month'])}</div>
    </div>
  </section>

  <section class="grid-2">
    <div class="card" style="padding:0;">
      <table>
        <thead>
          <tr><th>طريقة الشحن</th><th>المجموع (USD)</th></tr>
        </thead>
        <tbody>
          {"".join([f"<tr><td>{t}</td><td>{_fmt_money(v)}</td></tr>" for t, v in data['topups_by_type']])}
        </tbody>
      </table>
    </div>

    <div class="card" style="padding:0;">
      <table>
        <thead>
          <tr><th>المنتج</th><th>طلبات</th><th>كمية</th><th>المجموع (USD)</th></tr>
        </thead>
        <tbody>
          {"".join([
            f"<tr><td>{name}</td><td>{_fmt_int(orders)}</td><td>{_fmt_int(qty)}</td><td>{_fmt_money(usd)}</td></tr>"
            for name, orders, qty, usd in data['top_products']
          ])}
        </tbody>
      </table>
    </div>
  </section>
</body>
</html>
""")
            return HTMLResponse(html)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return HTMLResponse(
                f"<pre>Stats error:\n{e}\n\n{traceback.format_exc()}</pre>",
                status_code=500
            )
        finally:
            db.close()
