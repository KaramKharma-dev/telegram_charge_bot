# app/admin/users_view.py
from sqladmin import BaseView, expose
from starlette.responses import HTMLResponse
from sqlalchemy.orm import Session
from markupsafe import Markup
from app.db.session import SessionLocal
from app.models.user import User
from app.models.wallet import Wallet


class UsersView(BaseView):
    name = "المستخدمين"
    icon = "fa fa-users"
    category = "Dashboard"

    @expose("/users", methods=["GET"])
    def page(self, request):
        db: Session = SessionLocal()
        try:
            users = (
                db.query(User.id, User.tg_id, User.name, User.country,
                         User.is_blocked, User.created_at, Wallet.balance)
                .join(Wallet, Wallet.user_id == User.id, isouter=True)
                .all()
            )

            rows = "".join(
                f"<tr>"
                f"<td>{u.id}</td>"
                f"<td>{u.tg_id}</td>"
                f"<td>{u.name or '-'}</td>"
                f"<td>{u.balance or 0} USD</td>"
                f"<td>{u.country or '-'}</td>"
                f"<td>{'محظور' if u.is_blocked else 'نشط'}</td>"
                f"<td>{u.created_at.strftime('%Y-%m-%d')}</td>"
                f"</tr>"
                for u in users
            )

            html = Markup(f"""
            <html dir="rtl" lang="ar">
            <head>
                <meta charset="utf-8">
                <style>
                    body {{ font-family: Cairo, sans-serif; padding:20px; }}
                    table {{ width:100%; border-collapse: collapse; }}
                    th, td {{ border:1px solid #ccc; padding:8px; text-align:center; }}
                    th {{ background:#eee; }}
                </style>
            </head>
            <body>
                <h2>قائمة المستخدمين</h2>
                <table>
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Telegram ID</th>
                            <th>الاسم</th>
                            <th>الرصيد</th>
                            <th>الدولة</th>
                            <th>الحالة</th>
                            <th>تاريخ الإنشاء</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows}
                    </tbody>
                </table>
            </body>
            </html>
            """)
            return HTMLResponse(html)
        finally:
            db.close()
