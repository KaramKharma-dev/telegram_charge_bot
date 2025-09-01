"""add user_type column to users

Revision ID: a303959b914a
Revises: 6a5f49690880
Create Date: 2025-09-01 12:21:01.989882

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a303959b914a'
down_revision: Union[str, Sequence[str], None] = '6a5f49690880'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column("users", sa.Column("user_type", sa.Integer(), nullable=False, server_default="1"))

def downgrade():
    op.drop_column("users", "user_type")

