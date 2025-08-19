# app/admin/logs_view.py
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Any, Tuple, Dict

from markupsafe import Markup
from sqlalchemy import func
from sqlalchemy.orm import Session
from sqladmin import BaseView, expose
from starlette.responses import HTMLResponse

from app.db.session import SessionLocal
from app.models.wallet_transaction import WalletTransaction
from app.models.order import Order
from app.models.product import Product
from app.models.topup_method import TopupMethod
from app.models.user import User
from app.models.wallet import Wallet


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


class LogsView(BaseView):
    name = "سجل العمليات"
    icon = "fa fa-list"
    category = "Dashboard"

    @expose("/logs", methods=["GET"])
    def page(self, request) -> Any:
        db: Session = SessionLocal()
        try:
            # اكتشاف عمود الطريقة
            method_col_name = None
            for cand in ("topup_method_id", "method_id", "payment_method_id", "topup_method", "method", "payment_method"):
                if hasattr(WalletTransaction, cand):
                    method_col_name = cand
                    break

            approved_col = getattr(WalletTransaction, "approved_at", WalletTransaction.created_at)

            # --- جدول 1: سجل تعبئة الرصيد ---
            if method_col_name is None:
                # لا FK للطريقة
                topup_rows = db.query(
                    func.coalesce(WalletTransaction.type, "غير محدد"),
                    WalletTransaction.amount_usd,
                    getattr(WalletTransaction, "amount_syp", None),
                    User.name,
                    User.tg_id,
                    approved_col
                ).select_from(WalletTransaction) \
                .join(Wallet, Wallet.id == WalletTransaction.wallet_id, isouter=True) \
                .join(User, User.id == Wallet.user_id, isouter=True) \
                 .filter(WalletTransaction.status == "approved",
                         WalletTransaction.direction == "credit") \
                 .order_by(approved_col.desc()) \
                 .limit(500).all()
            else:
                method_col = getattr(WalletTransaction, method_col_name)
                if method_col_name.endswith("_id"):
                    topup_rows = db.query(
                        func.coalesce(TopupMethod.name, "غير محدد"),
                        WalletTransaction.amount_usd,
                        getattr(WalletTransaction, "amount_syp", None),
                        User.name,
                        User.tg_id,
                        approved_col
                    ).select_from(WalletTransaction) \
                     .join(TopupMethod, TopupMethod.id == method_col, isouter=True) \
                     .join(Wallet, Wallet.id == WalletTransaction.wallet_id, isouter=True) \
                     .join(User, User.id == Wallet.user_id, isouter=True) \
                     .filter(WalletTransaction.status == "approved",
                             WalletTransaction.direction == "credit") \
                     .order_by(approved_col.desc()) \
                     .limit(500).all()
                else:
                    topup_rows = db.query(
                        func.coalesce(method_col, "غير محدد"),
                        WalletTransaction.amount_usd,
                        getattr(WalletTransaction, "amount_syp", None),
                        User.name,
                        User.tg_id,
                        approved_col
                    ).select_from(WalletTransaction) \
                     .join(Wallet, Wallet.id == WalletTransaction.wallet_id, isouter=True) \
                     .join(User, User.id == Wallet.user_id, isouter=True) \
                     .filter(WalletTransaction.status == "approved",
                             WalletTransaction.direction == "credit") \
                     .order_by(approved_col.desc()) \
                     .limit(500).all()

            topups = [
                {
                    "method": m or "غير محدد",
                    "usd": _dec(usd),
                    "syp": _dec(syp) if syp is not None else Decimal("0"),
                    "user": un or "غير معروف",
                    "tg_id": tg or "",
                    "ts": (ts or datetime.min).strftime("%Y-%m-%d %H:%M"),
                }
                for (m, usd, syp, un, tg, ts) in topup_rows
            ]

            # --- جدول 2: سجل شحن المنتجات ---
            order_rows = db.query(
                func.coalesce(Order.product_name, Product.name, "غير محدد"),
                Order.qty,
                func.coalesce(Order.total_price_usd, 0),
                User.name,
                User.tg_id,
                Order.target,                 # NEW
                Order.created_at
            ).select_from(Order) \
            .join(Product, Product.id == Order.product_id, isouter=True) \
            .join(User, User.id == Order.user_id, isouter=True) \
            .filter(Order.status.in_(("created", "sent", "completed"))) \
            .order_by(Order.created_at.desc()) \
            .limit(500).all()

            orders = [
                {
                    "product": pn,
                    "qty": int(q or 0),
                    "usd": _dec(total),
                    "user": un or "غير معروف",
                    "tg_id": tg or "",
                    "target": tgt or "",
                    "ts": (ts or datetime.min).strftime("%Y-%m-%d %H:%M"),
                }
                for (pn, q, total, un, tg, tgt, ts) in order_rows
            ]

            # HTML
            def _render_topups():
                rows_html = "".join([
                    f"<tr>"
                    f"<td>{r['ts']}</td>"
                    f"<td>{r['method']}</td>"
                    f"<td>{_fmt_money(r['usd'])}</td>"
                    f"<td>{_fmt_money(r['syp'])}</td>"
                    f"<td>{r['user']}</td>"
                    f"<td>{r['tg_id']}</td>"
                    f"</tr>"
                    for r in topups
                ])
                return f"""
                <div class="card" style="padding:0;">
                <h3 style="margin:0;padding:12px 16px;border-bottom:1px solid var(--border);font-size:16px;color:var(--muted);">
                    سجل تعبئة الرصيد
                </h3>
                <table>
                    <thead>
                    <tr>
                        <th>التاريخ</th>
                        <th>طريقة الشحن</th>
                        <th>المبلغ (USD)</th>
                        <th>المبلغ (SYP)</th>
                        <th>المستخدم</th>
                        <th>tg_id</th>
                    </tr>
                    </thead>
                    <tbody>{rows_html or '<tr><td colspan="6">لا بيانات</td></tr>'}</tbody>
                </table>
                </div>
                """

            def _render_orders():
                rows_html = "".join([
                    f"<tr>"
                    f"<td>{r['ts']}</td>"
                    f"<td>{r['product']}</td>"
                    f"<td>{_fmt_int(r['qty'])}</td>"
                    f"<td>{_fmt_money(r['usd'])}</td>"
                    f"<td>{r['user']}</td>"
                    f"<td>{r['tg_id']}</td>"
                    f"<td>{r.get('target','')}</td>"   # NEW
                    f"</tr>"
                    for r in orders
                ])
                return f"""
                <div class="card" style="padding:0;">
                <h3 style="margin:0;padding:12px 16px;border-bottom:1px solid var(--border);font-size:16px;color:var(--muted);">
                    سجل شحن المنتجات
                </h3>
                <table>
                    <thead>
                    <tr>
                        <th>التاريخ</th>
                        <th>المنتج</th>
                        <th>الكمية</th>
                        <th>السعر (USD)</th>
                        <th>المستخدم</th>
                        <th>tg_id</th>
                        <th>المعرّف المشحون له</th>  <!-- NEW -->
                    </tr>
                    </thead>
                    <tbody>{rows_html or '<tr><td colspan="7">لا بيانات</td></tr>'}</tbody>
                </table>
                </div>
                """


            html = Markup(f"""
<!doctype html>
<html dir="rtl" lang="ar">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <style>
    :root {{
      --bg:#0f172a; --card:#111827; --muted:#94a3b8; --text:#e5e7eb;
      --border:#1f2937; --table-stripe:rgba(255,255,255,0.03); --radius:14px;
      --shadow:0 10px 25px rgba(0,0,0,0.25);
    }}
    @media (prefers-color-scheme: light) {{
      :root {{ --bg:#f7f7fb; --card:#fff; --muted:#6b7280; --text:#0f172a; --border:#e5e7eb; --table-stripe:rgba(0,0,0,0.02); }}
    }}
    body {{ margin:0; padding:24px; font-family:-apple-system, Segoe UI, Roboto, "Cairo", Tahoma, Arial, sans-serif; background:var(--bg); color:var(--text); }}
    .header {{ border:1px solid var(--border); border-radius:var(--radius); padding:18px; box-shadow:var(--shadow); background:var(--card); }}
    .header h2 {{ margin:0; font-size:22px; }}
    .grid-2 {{ display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-top:16px; }}
    @media (max-width:1100px) {{ .grid-2 {{ grid-template-columns:1fr; }} }}
    .card {{ background:var(--card); border:1px solid var(--border); border-radius:var(--radius); box-shadow:var(--shadow); }}
    table {{ width:100%; border-collapse:separate; border-spacing:0; }}
    thead th {{ text-align:right; padding:12px; font-size:13px; color:var(--muted); border-bottom:1px solid var(--border); }}
    tbody td {{ padding:12px; border-bottom:1px solid var(--border); font-size:14px; }}
    tbody tr:nth-child(odd) td {{ background: var(--table-stripe); }}
  </style>
</head>
<body>
  <section class="header">
    <h2>سجل العمليات</h2>
  </section>

  <section class="grid-2">
    {_render_topups()}
    {_render_orders()}
  </section>
</body>
</html>
""")
            return HTMLResponse(html)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return HTMLResponse(f"<pre>Logs error:\n{e}\n\n{traceback.format_exc()}</pre>", status_code=500)
        finally:
            db.close()
