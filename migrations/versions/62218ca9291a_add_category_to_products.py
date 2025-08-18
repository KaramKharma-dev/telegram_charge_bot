"""add category to products

Revision ID: 62218ca9291a
Revises: 7547e9384479
Create Date: 2025-08-12 11:35:40.128307

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '62218ca9291a'
down_revision: Union[str, Sequence[str], None] = '7547e9384479'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('products', sa.Column('category', sa.String(50), nullable=True))


def downgrade() -> None:
    op.drop_column('products', 'category')