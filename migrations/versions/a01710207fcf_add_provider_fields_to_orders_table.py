"""add provider fields to orders table

Revision ID: a01710207fcf
Revises: 62218ca9291a
Create Date: 2025-08-12 13:34:43.886614

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a01710207fcf'
down_revision: Union[str, Sequence[str], None] = '62218ca9291a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column("orders", sa.Column("provider_product_id", sa.String(length=50), nullable=False))
    op.add_column("orders", sa.Column("order_uuid", sa.String(length=36), nullable=False))
    op.add_column("orders", sa.Column("provider_order_id", sa.String(length=64), nullable=True))
    op.add_column("orders", sa.Column("provider_status", sa.String(length=20), nullable=True))
    op.add_column("orders", sa.Column("provider_price_usd", sa.DECIMAL(18, 8), nullable=True))
    op.add_column("orders", sa.Column("provider_payload", sa.Text(), nullable=True))
    op.add_column("orders", sa.Column("error_msg", sa.String(length=200), nullable=True))
    op.create_index("ix_order_uuid", "orders", ["order_uuid"], unique=True)

def downgrade():
    op.drop_index("ix_order_uuid", table_name="orders")
    op.drop_column("orders", "error_msg")
    op.drop_column("orders", "provider_payload")
    op.drop_column("orders", "provider_price_usd")
    op.drop_column("orders", "provider_status")
    op.drop_column("orders", "provider_order_id")
    op.drop_column("orders", "order_uuid")
    op.drop_column("orders", "provider_product_id")
