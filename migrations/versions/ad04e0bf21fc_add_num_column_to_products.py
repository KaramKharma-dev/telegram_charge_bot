"""add num column to products

Revision ID: ad04e0bf21fc
Revises: b46f08d13be2
Create Date: 2025-08-11 18:44:14.542866
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "ad04e0bf21fc"
down_revision: Union[str, Sequence[str], None] = "b46f08d13be2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {c["name"] for c in insp.get_columns("products")}

    if "num" not in cols:
        op.add_column("products", sa.Column("num", sa.String(50), nullable=True))
        # ترتيب العمود بعد name (يعمل على MySQL فقط)
        try:
            op.execute("ALTER TABLE products MODIFY COLUMN num VARCHAR(50) NULL AFTER name")
        except Exception:
            pass


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {c["name"] for c in insp.get_columns("products")}

    if "num" in cols:
        op.drop_column("products", "num")
