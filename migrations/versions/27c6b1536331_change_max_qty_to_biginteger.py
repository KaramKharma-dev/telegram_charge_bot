"""change max_qty to BigInteger

Revision ID: 27c6b1536331
Revises: 5840face82a9
Create Date: 2025-08-11 19:05:21.092322

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '27c6b1536331'
down_revision: Union[str, Sequence[str], None] = '5840face82a9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.alter_column(
        "products",
        "max_qty",
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=False
    )

def downgrade():
    op.alter_column(
        "products",
        "max_qty",
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        existing_nullable=False
    )