"""add incoming_sms table

Revision ID: 6a5f49690880
Revises: 28a8b0f192cd
Create Date: 2025-08-21 14:50:22.126178
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6a5f49690880"
down_revision: Union[str, Sequence[str], None] = "28a8b0f192cd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "incoming_sms",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("sender", sa.String(64), nullable=True),
        sa.Column("body", sa.String(1024), nullable=False),
        sa.Column("op_ref", sa.String(128), nullable=True),
        sa.Column("amount_syp", sa.Integer(), nullable=True),
        sa.Column(
            "received_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("msg_uid", sa.String(128), nullable=True),
        sa.Column("consumed_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("msg_uid", name="uq_incomingsms_msguid"),
    )
    op.create_index(
        "ix_incomingsms_ref_time", "incoming_sms", ["op_ref", "received_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_incomingsms_ref_time", table_name="incoming_sms")
    op.drop_table("incoming_sms")
