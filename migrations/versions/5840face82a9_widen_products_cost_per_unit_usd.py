"""widen products.cost_per_unit_usd

Revision ID: 5840face82a9
Revises: ad04e0bf21fc
Create Date: 2025-08-11 19:02:47.201775

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import DECIMAL
# revision identifiers, used by Alembic.
revision: str = '5840face82a9'
down_revision: Union[str, Sequence[str], None] = 'ad04e0bf21fc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.alter_column(
        "products",
        "cost_per_unit_usd",
        existing_type=DECIMAL(18, 8),
        type_=DECIMAL(20, 8),
        existing_nullable=False,
    )

def downgrade():
    op.alter_column(
        "products",
        "cost_per_unit_usd",
        existing_type=DECIMAL(20, 8),
        type_=DECIMAL(18, 8),
        existing_nullable=False,
    )