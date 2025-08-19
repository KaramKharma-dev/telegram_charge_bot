from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '28a8b0f192cd'
down_revision: Union[str, Sequence[str], None] = '3d6c149ae33c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "order",
        sa.Column(
            "is_refunded",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False
        )
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("order", "is_refunded")
