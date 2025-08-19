# app/admin/wallets_view.py
from typing import Optional, Tuple
from decimal import Decimal

from sqladmin import BaseView, expose
from sqlalchemy import or_, func, cast, String
from sqlalchemy.orm import Session
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse
from markupsafe import Markup

from app.db.session import SessionLocal
from app.models.wallet import Wallet
from app.models.user import User

BASE = "/admin"  # بادئة لوحة SQLAdmin

# ---------- Helpers ----------
def _layout(title: str, body_html: str) -> Markup:
    return Markup(f"""<!doctype html><html dir="rtl" lang="ar"><head>
<meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>{title}</title>
<style>
:root {{ --bg:#0f172a; --card:#0b1220; --muted:#94a3b8; --text:#e5e7eb; --accent:#22d3ee; --accent2:#60a5fa; --border:#1f2937; --danger:#ef4444; --ok:#22c55e; --shadow:0 10px 25px rgba(0,0,0,.25); --radius:14px; }}
@media (prefers-color-scheme: light) {{ :root {{ --bg:#f7f7fb; --card:#fff; --muted:#6b7280; --text:#0f172a; --accent:#0ea5e9; --accent2:#2563eb; --border:#e5e7eb; --danger:#dc2626; --ok:#16a34a; }} }}
*{{box-sizing:border-box}} body{{margin:0;padding:22px;font-family:-apple-system,Segoe UI,Roboto,"Cairo",Tahoma,Arial,sans-serif;background:
radial-gradient(1000px 600px at 100% -10%,rgba(34,211,238,.08),transparent 60%),radial-gradient(800px 500px at -10% 0%,rgba(96,165,250,.08),transparent 60%),var(--bg);color:var(--text)}}
.header{{background:linear-gradient(90deg,rgba(34,211,238,.20),rgba(96,165,250,.20));border:1px solid var(--border);border-radius:var(--radius);padding:16px;box-shadow:var(--shadow);display:flex;gap:12px;align-items:center;justify-content:space-between;flex-wrap:wrap}}
.header h2{{margin:0;font-size:20px}} .actions{{display:flex;gap:8px;align-items:center;flex-wrap:wrap}}
.btn{{display:inline-flex;align-items:center;gap:8px;padding:8px 12px;border-radius:10px;border:1px solid var(--border);background:var(--card);color:var(--text);text-decoration:none;cursor:pointer;font-size:14px}}
.btn.primary{{background:linear-gradient(180deg,var(--accent),var(--accent2));color:#fff;border:none}}
.btn.danger{{border-color:var(--danger);color:var(--danger)}} .btn.ok{{border-color:var(--ok);color:var(--ok)}}
.input,.select{{padding:8px 10px;border:1px solid var(--border);border-radius:10px;background:var(--card);color:var(--text);min-width:160px}}
.table-wrap{{margin-top:16px;background:var(--card);border:1px solid var(--border);border-radius:var(--radius);overflow:auto;box-shadow:var(--shadow)}}
table{{width:100%;border-collapse:separate;border-spacing:0}}
thead th{{text-align:right;padding:12px;font-size:13px;color:var(--muted);border-bottom:1px solid var(--border);background:linear-gradient(180deg,rgba(255,255,255,.02),transparent);position:sticky;top:0}}
tbody td{{padding:12px;border-bottom:1px solid var(--border);font-size:14px;vertical-align:middle}}
tbody tr:nth-child(odd) td{{background:rgba(255,255,255,.02)}}
.badge{{padding:2px 8px;border-radius:999px;font-size:12px;border:1px solid var(--border)}}
.badge.ok{{background:rgba(34,197,94,.12);color:var(--ok)}} .badge.block{{background:rgba(239,68,68,.12);color:var(--danger)}}
.toolbar{{display:flex;gap:8px;align-items:center;flex-wrap:wrap}}
.pagination{{display:flex;gap:6px;align-items:center;margin-top:12px;justify-content:flex-end}}
.page-btn{{padding:6px 10px;border:1px solid var(--border);border-radius:8px;background:var(--card);color:var(--text);text-decoration:none}}
.page-btn.active{{background:linear-gradient(180deg,var(--accent),var(--accent2));color:#fff;border:none}}
.form-card{{margin-top:16px;background:var(--card);border:1px solid var(--border);border-radius:var(--radius);padding:16px;box-shadow:var(--shadow)}}
.form-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}}
label{{font-size:13px;color:var(--muted)}} .help{{font-size:12px;color:var(--muted);margin-top:4px}} hr.sep{{border:none;height:1px;background:var(--border);margin:12px 0}}
</style>
<script>
function confirmDelete(id){{
  if(!confirm('حذف هذه المحفظة؟')) return;
  const f=document.createElement('form'); f.method='POST'; f.action='{BASE}/wallets/'+id+'/delete';
  document.body.appendChild(f); f.submit();
}}
</script>
</head><body>{body_html}</body></html>""")

def _q(request: Request, key: str, default: Optional[str] = None) -> str:
    return str(request.query_params.get(key, default or "")).strip()

def _paginate(page: int, per: int) -> Tuple[int, int]:
    page = max(page, 1); per = min(max(per, 5), 100); offset = (page - 1) * per; return offset, per


class WalletsView(BaseView):
    name = "المحافظ"
    icon = "fa fa-wallet"
    category = "Dashboard"

    # ------ List -------
    @expose("/wallets", methods=["GET"])
    def list_wallets(self, request: Request):
        db: Session = SessionLocal()
        try:
            q = _q(request, "q", "")
            page = int(_q(request, "page", "1") or "1")
            per = int(_q(request, "per", "20") or "20")
            offset, limit = _paginate(page, per)

            base = (
                db.query(
                    Wallet.id,
                    Wallet.user_id,
                    Wallet.currency,
                    Wallet.balance,
                    Wallet.created_at,
                    Wallet.updated_at,
                    User.name.label("user_name"),
                )
                .join(User, User.id == Wallet.user_id, isouter=True)
            )

            if q:
                like = f"%{q}%"
                base = base.filter(
                    or_(
                        cast(Wallet.id, String).ilike(like),
                        cast(Wallet.user_id, String).ilike(like),
                        Wallet.currency.ilike(like),
                        User.name.ilike(like),
                    )
                )

            total = base.count()
            rows = (
                base.order_by(Wallet.created_at.desc())
                .offset(offset)
                .limit(limit)
                .all()
            )

            tr = "".join(
                f"""
<tr>
  <td>{r.id}</td>
  <td>{r.user_id}</td>
  <td>{r.user_name or '-'}</td>
  <td>{r.currency}</td>
  <td>{(r.balance or Decimal('0')):.2f}</td>
  <td>{r.created_at.strftime('%Y-%m-%d')}</td>
  <td>{r.updated_at.strftime('%Y-%m-%d')}</td>
  <td>
    <a class="btn" href="{BASE}/wallets/{r.id}/edit">تعديل</a>
    <button class="btn danger" onclick="confirmDelete({r.id})">حذف</button>
  </td>
</tr>
"""
                for r in rows
            )

            pages = max((total + limit - 1) // limit, 1)
            pag_html = ""
            if pages > 1:
                items = []
                for i in range(1, pages + 1):
                    cls = "page-btn active" if i == page else "page-btn"
                    items.append(f'<a class="{cls}" href="{BASE}/wallets?q={q}&page={i}&per={per}">{i}</a>')
                pag_html = f'<div class="pagination">{"".join(items)}</div>'

            body = f"""
<section class="header">
  <h2>إدارة المحافظ</h2>
  <div class="actions">
    <a class="btn primary" href="{BASE}/wallets/new">+ محفظة جديدة</a>
  </div>
</section>

<div class="toolbar" style="margin-top:12px">
  <form method="get" action="{BASE}/wallets" style="display:flex;gap:8px;align-items:center">
    <input class="input" type="search" name="q" placeholder="بحث بـ ID أو User ID أو الاسم أو العملة" value="{q}">
    <select class="select" name="per">
      <option value="10" {"selected" if per==10 else ""}>10</option>
      <option value="20" {"selected" if per==20 else ""}>20</option>
      <option value="50" {"selected" if per==50 else ""}>50</option>
      <option value="100" {"selected" if per==100 else ""}>100</option>
    </select>
    <button class="btn" type="submit">بحث</button>
  </form>
  <div style="margin-inline-start:auto;color:var(--muted);font-size:13px">الإجمالي: {total:,}</div>
</div>

<div class="table-wrap">
  <table>
    <thead>
      <tr>
        <th>#</th><th>User ID</th><th>الاسم</th><th>العملة</th><th>الرصيد</th><th>أُنشئت</th><th>عُدّلت</th><th>إجراءات</th>
      </tr>
    </thead>
    <tbody>
      {tr or '<tr><td colspan="8" style="text-align:center;color:var(--muted)">لا يوجد بيانات</td></tr>'}
    </tbody>
  </table>
</div>

{pag_html}
"""
            return HTMLResponse(_layout("إدارة المحافظ", body))
        finally:
            db.close()

    # ------ Create -------
    @expose("/wallets/new", methods=["GET", "POST"])
    async def create_wallet(self, request: Request):
        if request.method == "POST":
            form = await request.form()
            user_id = (form.get("user_id") or "").strip()
            currency = (form.get("currency") or "USD").strip().upper()[:3]
            balance_s = (form.get("balance") or "").strip()

            if not user_id.isdigit():
                return HTMLResponse(_layout("إنشاء محفظة", _form_wallet(user_id, currency, balance_s, error="User ID يجب أن يكون رقمًا")), status_code=400)

            db: Session = SessionLocal()
            try:
                user = db.get(User, int(user_id))
                if not user:
                    return HTMLResponse(_layout("إنشاء محفظة", _form_wallet(user_id, currency, balance_s, error="المستخدم غير موجود")), status_code=400)

                try:
                    bal = Decimal(balance_s) if balance_s else Decimal("0")
                except Exception:
                    return HTMLResponse(_layout("إنشاء محفظة", _form_wallet(user_id, currency, balance_s, error="الرصيد غير صالح")), status_code=400)

                if bal < 0:
                    return HTMLResponse(_layout("إنشاء محفظة", _form_wallet(user_id, currency, balance_s, error="الرصيد يجب أن يكون ≥ 0")), status_code=400)

                # فريدة (user_id, currency)
                exists = db.query(Wallet).filter(Wallet.user_id == user.id, Wallet.currency == currency).first()
                if exists:
                    return HTMLResponse(_layout("إنشاء محفظة", _form_wallet(user_id, currency, balance_s, error="هناك محفظة بنفس العملة لهذا المستخدم")), status_code=400)

                w = Wallet(user_id=user.id, currency=currency, balance=bal)
                db.add(w); db.commit()
                return RedirectResponse(url=f"{BASE}/wallets", status_code=303)
            except Exception:
                db.rollback(); raise
            finally:
                db.close()

        return HTMLResponse(_layout("إنشاء محفظة", _form_wallet()))

    # ------ Edit -------
    @expose("/wallets/{wallet_id}/edit", methods=["GET", "POST"])
    async def edit_wallet(self, request: Request, wallet_id: int):
        db: Session = SessionLocal()
        try:
            w = db.get(Wallet, wallet_id)
            if not w:
                return HTMLResponse(_layout("غير موجود", f"<div class='form-card'>المحفظة #{wallet_id} غير موجودة.</div>"), status_code=404)

            if request.method == "POST":
                form = await request.form()
                user_id = (form.get("user_id") or "").strip()
                currency = (form.get("currency") or "USD").strip().upper()[:3]
                balance_s = (form.get("balance") or "").strip()

                if not user_id.isdigit():
                    return HTMLResponse(_layout("تعديل محفظة", _form_wallet(user_id, currency, balance_s, error="User ID يجب أن يكون رقمًا", submit_text="حفظ", back_href=f"{BASE}/wallets")), status_code=400)

                user = db.get(User, int(user_id))
                if not user:
                    return HTMLResponse(_layout("تعديل محفظة", _form_wallet(user_id, currency, balance_s, error="المستخدم غير موجود", submit_text="حفظ", back_href=f"{BASE}/wallets")), status_code=400)

                try:
                    bal = Decimal(balance_s) if balance_s else Decimal("0")
                except Exception:
                    return HTMLResponse(_layout("تعديل محفظة", _form_wallet(user_id, currency, balance_s, error="الرصيد غير صالح", submit_text="حفظ", back_href=f"{BASE}/wallets")), status_code=400)

                if bal < 0:
                    return HTMLResponse(_layout("تعديل محفظة", _form_wallet(user_id, currency, balance_s, error="الرصيد يجب أن يكون ≥ 0", submit_text="حفظ", back_href=f"{BASE}/wallets")), status_code=400)

                # تحقق من unique إذا تغير user_id أو currency
                if user.id != w.user_id or currency != w.currency:
                    dup = db.query(Wallet).filter(Wallet.user_id == user.id, Wallet.currency == currency).first()
                    if dup and dup.id != w.id:
                        return HTMLResponse(_layout("تعديل محفظة", _form_wallet(user_id, currency, balance_s, error="هناك محفظة بنفس العملة لهذا المستخدم", submit_text="حفظ", back_href=f"{BASE}/wallets")), status_code=400)

                w.user_id = user.id
                w.currency = currency
                w.balance = bal
                db.commit()
                return RedirectResponse(url=f"{BASE}/wallets", status_code=303)

            body = _form_wallet(
                user_id=str(w.user_id),
                currency=w.currency,
                balance=f"{w.balance:.2f}",
                submit_text="حفظ",
                back_href=f"{BASE}/wallets",
            )
            return HTMLResponse(_layout(f"تعديل محفظة #{wallet_id}", body))
        finally:
            db.close()

    # ------ Delete -------
    @expose("/wallets/{wallet_id}/delete", methods=["POST"])
    async def delete_wallet(self, request: Request, wallet_id: int):
        db: Session = SessionLocal()
        try:
            w = db.get(Wallet, wallet_id)
            if not w:
                return RedirectResponse(url=f"{BASE}/wallets", status_code=303)

            db.delete(w)
            db.commit()
            return RedirectResponse(url=f"{BASE}/wallets", status_code=303)
        except Exception:
            db.rollback()
            msg = "لا يمكن حذف المحفظة. تحقق من المعاملات المرتبطة أو قيود الـ FK."
            return HTMLResponse(_layout("خطأ حذف", f"<div class='form-card badge block'>{msg}</div><div style='margin-top:10px'><a class='btn' href='{BASE}/wallets'>رجوع</a></div>"), status_code=400)
        finally:
            db.close()


# ---------- Form builder ----------
def _form_wallet(
    user_id: str = "",
    currency: str = "USD",
    balance: str = "0.00",
    error: Optional[str] = None,
    submit_text: str = "إنشاء",
    back_href: str = f"{BASE}/wallets",
) -> str:
    err = f"<div class='badge block' style='margin-bottom:10px'>{error}</div>" if error else ""
    return f"""
<section class="header">
  <h2>{'محفظة جديدة' if submit_text == 'إنشاء' else 'تعديل محفظة'}</h2>
  <div class="actions">
    <a class="btn" href="{back_href}">رجوع</a>
  </div>
</section>

<div class="form-card">
  {err}
  <form method="post" class="form-grid" action="">
    <div>
      <label>User ID</label>
      <input class="input" type="text" name="user_id" value="{user_id}" placeholder="مثال: 1" required>
      <div class="help">رقم المستخدم المرتبط بالمحفظة</div>
    </div>
    <div>
      <label>العملة</label>
      <input class="input" type="text" name="currency" value="{currency}" maxlength="3" placeholder="USD, EUR, TRY ..." required>
    </div>
    <div>
      <label>الرصيد</label>
      <input class="input" type="number" step="0.01" min="0" name="balance" value="{balance}">
    </div>
    <div style="grid-column:1/-1"><hr class="sep"></div>
    <div style="grid-column:1/-1;display:flex;gap:8px">
      <button class="btn primary" type="submit">{submit_text}</button>
      <a class="btn" href="{back_href}">إلغاء</a>
    </div>
  </form>
</div>
"""
