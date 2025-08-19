# app/admin/users_view.py
from typing import Optional, Tuple
from decimal import Decimal

from sqladmin import BaseView, expose
from sqlalchemy import or_, func, cast, String
from sqlalchemy.orm import Session
from starlette.responses import HTMLResponse, RedirectResponse
from starlette.requests import Request
from markupsafe import Markup

from app.db.session import SessionLocal
from app.models.user import User
from app.models.wallet import Wallet

BASE = "/admin"  # بادئة SQLAdmin

# ==== Helpers ====
def _layout(title: str, body_html: str) -> Markup:
    return Markup(f"""
<!doctype html><html dir="rtl" lang="ar"><head>
<meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>{title}</title>
<style>
:root {{ --bg:#0f172a; --card:#0b1220; --muted:#94a3b8; --text:#e5e7eb; --accent:#22d3ee; --accent2:#60a5fa; --border:#1f2937; --danger:#ef4444; --ok:#22c55e; --shadow:0 10px 25px rgba(0,0,0,.25); --radius:14px; }}
@media (prefers-color-scheme: light) {{ :root {{ --bg:#f7f7fb; --card:#fff; --muted:#6b7280; --text:#0f172a; --accent:#0ea5e9; --accent2:#2563eb; --border:#e5e7eb; --danger:#dc2626; --ok:#16a34a; }} }}
*{{box-sizing:border-box}} body{{margin:0;padding:22px;font-family:-apple-system,Segoe UI,Roboto,"Cairo",Tahoma,Arial,sans-serif;background:radial-gradient(1000px 600px at 100% -10%,rgba(34,211,238,.08),transparent 60%),radial-gradient(800px 500px at -10% 0%,rgba(96,165,250,.08),transparent 60%),var(--bg);color:var(--text)}}
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
  if(!confirm('هل تريد حذف هذا المستخدم؟'))return;
  const f=document.createElement('form'); f.method='POST'; f.action='{BASE}/users/'+id+'/delete';
  document.body.appendChild(f); f.submit();
}}
</script>
</head><body>{body_html}</body></html>
""")

def _q(request: Request, key: str, default: Optional[str] = None) -> str:
    return str(request.query_params.get(key, default or "")).strip()

def _paginate(page: int, per: int) -> Tuple[int, int]:
    page = max(page, 1); per = min(max(per, 5), 100); offset = (page - 1) * per; return offset, per


class UsersView(BaseView):
    name = "المستخدمين"
    icon = "fa fa-users"
    category = "Dashboard"

    # اجعل /admin يفتح /admin/users مباشرةً
    @expose("/", methods=["GET"])
    def index_redirect(self, request: Request):
        return RedirectResponse(url=f"{BASE}/users", status_code=303)

    # ------- List with search + pagination --------
    @expose("/users", methods=["GET"])
    def list_users(self, request: Request):
        db: Session = SessionLocal()
        try:
            q = _q(request, "q", "")
            page = int(_q(request, "page", "1") or "1")
            per = int(_q(request, "per", "20") or "20")
            offset, limit = _paginate(page, per)

            base = (
                db.query(
                    User.id, User.tg_id, User.name, User.country,
                    User.is_blocked, User.created_at, Wallet.balance,
                )
                .join(Wallet, Wallet.user_id == User.id, isouter=True)
            )

            if q:
                like = f"%{q}%"
                base = base.filter(
                    or_(
                        cast(User.id, String).ilike(like),
                        cast(User.tg_id, String).ilike(like),
                        User.name.ilike(like),
                        User.country.ilike(like),
                    )
                )

            total = base.count()
            rows = base.order_by(User.created_at.desc()).offset(offset).limit(limit).all()

            tr = "".join(
                f"""
<tr>
  <td>{r.id}</td>
  <td>{r.tg_id or "-"}</td>
  <td>{(r.name or "-")}</td>
  <td>{(r.balance or Decimal("0")):.2f} USD</td>
  <td>{r.country or "-"}</td>
  <td><span class="badge {'block' if r.is_blocked else 'ok'}">{'محظور' if r.is_blocked else 'نشط'}</span></td>
  <td>{r.created_at.strftime('%Y-%m-%d')}</td>
  <td>
    <a class="btn" href="{BASE}/users/{r.id}/edit">تعديل</a>
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
                    items.append(f'<a class="{cls}" href="{BASE}/users?q={q}&page={i}&per={per}">{i}</a>')
                pag_html = f'<div class="pagination">{"".join(items)}</div>'

            body = f"""
<section class="header">
  <h2>إدارة المستخدمين</h2>
  <div class="actions">
    <a class="btn primary" href="{BASE}/users/new">+ مستخدم جديد</a>
  </div>
</section>

<div class="toolbar" style="margin-top:12px">
  <form method="get" action="{BASE}/users" style="display:flex;gap:8px;align-items:center">
    <input class="input" type="search" name="q" placeholder="بحث بالاسم أو Telegram ID أو الدولة" value="{q}">
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
        <th>#</th><th>Telegram ID</th><th>الاسم</th><th>الرصيد</th><th>الدولة</th><th>الحالة</th><th>أُنشئ</th><th>إجراءات</th>
      </tr>
    </thead>
    <tbody>
      {tr or '<tr><td colspan="8" style="text-align:center;color:var(--muted)">لا يوجد بيانات</td></tr>'}
    </tbody>
  </table>
</div>

{pag_html}
"""
            return HTMLResponse(_layout("إدارة المستخدمين", body))
        finally:
            db.close()

    # ------- Create -------
    @expose("/users/new", methods=["GET", "POST"])
    async def create_user(self, request: Request):
        if request.method == "POST":
            form = await request.form()
            tg_id = (form.get("tg_id") or "").strip()
            name = (form.get("name") or "").strip()
            country = (form.get("country") or "").strip()
            is_blocked = form.get("is_blocked") == "on"
            balance = (form.get("balance") or "").strip()

            if not tg_id.isdigit():
                return HTMLResponse(
                    _layout("إنشاء مستخدم", _form_user(name, tg_id, country, is_blocked, balance, error="Telegram ID يجب أن يكون رقمًا")),
                    status_code=400
                )

            db: Session = SessionLocal()
            try:
                user = User(tg_id=int(tg_id), name=name or None, country=country or None, is_blocked=is_blocked)
                db.add(user); db.flush()

                try:
                    bal = Decimal(balance) if balance else Decimal("0")
                except Exception:
                    bal = Decimal("0")

                w = db.query(Wallet).filter(Wallet.user_id == user.id, Wallet.currency == "USD").one_or_none()
                if not w:
                    db.add(Wallet(user_id=user.id, currency="USD", balance=bal))
                else:
                    w.balance = bal

                db.commit()
                return RedirectResponse(url=f"{BASE}/users", status_code=303)
            except Exception:
                db.rollback(); raise
            finally:
                db.close()

        return HTMLResponse(_layout("إنشاء مستخدم", _form_user()))

    # ------- Edit -------
    @expose("/users/{user_id}/edit", methods=["GET", "POST"])
    async def edit_user(self, request: Request, user_id: int):
        db: Session = SessionLocal()
        try:
            user = db.get(User, user_id)
            if not user:
                return HTMLResponse(_layout("غير موجود", f"<div class='form-card'>المستخدم #{user_id} غير موجود.</div>"), status_code=404)

            wallet = db.query(Wallet).filter(Wallet.user_id == user.id, Wallet.currency == "USD").one_or_none()

            if request.method == "POST":
                form = await request.form()
                tg_id = (form.get("tg_id") or "").strip()
                name = (form.get("name") or "").strip()
                country = (form.get("country") or "").strip()
                is_blocked = form.get("is_blocked") == "on"
                balance = (form.get("balance") or "").strip()

                if not tg_id.isdigit():
                    body = _form_user(name, tg_id, country, is_blocked, balance, error="Telegram ID يجب أن يكون رقمًا", submit_text="حفظ التعديلات", back_href=f"{BASE}/users")
                    return HTMLResponse(_layout("تعديل مستخدم", body), status_code=400)

                user.tg_id = int(tg_id)
                user.name = name or None
                user.country = country or None
                user.is_blocked = is_blocked

                try:
                    bal = Decimal(balance) if balance else Decimal("0")
                except Exception:
                    bal = Decimal("0")

                if not wallet:
                    wallet = Wallet(user_id=user.id, currency="USD", balance=bal)
                    db.add(wallet)
                else:
                    wallet.balance = bal

                db.commit()
                return RedirectResponse(url=f"{BASE}/users", status_code=303)

            body = _form_user(
                name=user.name or "",
                tg_id=str(user.tg_id or ""),
                country=user.country or "",
                is_blocked=bool(user.is_blocked),
                balance=str((wallet.balance if wallet else Decimal("0"))),
                submit_text="حفظ التعديلات",
                back_href=f"{BASE}/users",
            )
            return HTMLResponse(_layout(f"تعديل مستخدم #{user_id}", body))
        finally:
            db.close()

    # ------- Delete -------
    @expose("/users/{user_id}/delete", methods=["POST"])
    async def delete_user(self, request: Request, user_id: int):
        db: Session = SessionLocal()
        try:
            user = db.get(User, user_id)
            if not user:
                return RedirectResponse(url=f"{BASE}/users", status_code=303)

            db.query(Wallet).filter(Wallet.user_id == user.id).delete()
            db.delete(user); db.commit()
            return RedirectResponse(url=f"{BASE}/users", status_code=303)
        except Exception:
            db.rollback(); raise
        finally:
            db.close()


# ------- Form builder -------
def _form_user(
    name: str = "",
    tg_id: str = "",
    country: str = "",
    is_blocked: bool = False,
    balance: str = "0",
    error: Optional[str] = None,
    submit_text: str = "إنشاء",
    back_href: str = f"{BASE}/users",
) -> str:
    err = f"<div class='badge block' style='margin-bottom:10px'>{error}</div>" if error else ""
    checked = "checked" if is_blocked else ""
    return f"""
<section class="header">
  <h2>{'مستخدم جديد' if submit_text == 'إنشاء' else 'تعديل مستخدم'}</h2>
  <div class="actions">
    <a class="btn" href="{back_href}">رجوع</a>
  </div>
</section>

<div class="form-card">
  {err}
  <form method="post" class="form-grid" action="">
    <div>
      <label>Telegram ID</label>
      <input class="input" type="text" name="tg_id" value="{tg_id}" placeholder="مثال: 123456789" required>
      <div class="help">رقم مستخدم تيليغرام</div>
    </div>
    <div>
      <label>الاسم</label>
      <input class="input" type="text" name="name" value="{name}" placeholder="الاسم الظاهر">
    </div>
    <div>
      <label>الدولة</label>
      <input class="input" type="text" name="country" value="{country}" placeholder="SY, TR, NL ...">
    </div>
    <div>
      <label>الرصيد (USD)</label>
      <input class="input" type="number" step="0.01" name="balance" value="{balance}">
    </div>
    <div style="display:flex;align-items:center;gap:8px;margin-top:20px">
      <input id="blk" type="checkbox" name="is_blocked" {checked}>
      <label for="blk">محظور</label>
    </div>
    <div style="grid-column:1/-1"><hr class="sep"></div>
    <div style="grid-column:1/-1;display:flex;gap:8px">
      <button class="btn primary" type="submit">{submit_text}</button>
      <a class="btn" href="{back_href}">إلغاء</a>
    </div>
  </form>
</div>
"""
