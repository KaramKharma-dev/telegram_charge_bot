"""add profit_dealer_2 and profit_dealer_3 to products

Revision ID: 44e0f07fdd52
Revises: a303959b914a
Create Date: 2025-09-01 12:33:44.593042

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '44e0f07fdd52'
down_revision: Union[str, Sequence[str], None] = 'a303959b914a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column("products", sa.Column("profit_dealer_2", sa.DECIMAL(18, 8), nullable=True))
    op.add_column("products", sa.Column("profit_dealer_3", sa.DECIMAL(18, 8), nullable=True))

def downgrade():
    op.drop_column("products", "profit_dealer_3")
    op.drop_column("products", "profit_dealer_2")
