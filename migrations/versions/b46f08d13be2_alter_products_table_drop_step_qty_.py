from alembic import op
import sqlalchemy as sa

revision = "b46f08d13be2"
down_revision = "fbb9ee2e3435"

def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {c["name"] for c in insp.get_columns("products")}

    # حذف العمود step_qty إذا موجود
    if "step_qty" in cols:
        op.drop_column("products", "step_qty")

    # إعادة تسمية العمود
    if "profit_per_unit_usd" in cols:
        op.alter_column(
            "products",
            "profit_per_unit_usd",
            new_column_name="profit",
            existing_type=sa.DECIMAL(18, 8),
            existing_nullable=False,
        )

    # إضافة العمود profit_dealer بعد profit
    cols = {c["name"] for c in insp.get_columns("products")}
    if "profit_dealer" not in cols:
        op.add_column("products", sa.Column("profit_dealer", sa.DECIMAL(18, 8), nullable=True))
        op.execute("ALTER TABLE products MODIFY COLUMN profit_dealer DECIMAL(18,8) NULL AFTER profit")

    # إضافة العمود number إذا غير موجود
    cols = {c["name"] for c in insp.get_columns("products")}
    if "number" not in cols:
        op.add_column("products", sa.Column("number", sa.String(50), nullable=True))
        op.execute("ALTER TABLE products MODIFY COLUMN number VARCHAR(50) NULL AFTER name")


def downgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {c["name"] for c in insp.get_columns("products")}

    if "number" in cols:
        op.drop_column("products", "number")

    if "profit_dealer" in cols:
        op.drop_column("products", "profit_dealer")

    cols = {c["name"] for c in insp.get_columns("products")}
    if "profit" in cols:
        op.alter_column(
            "products",
            "profit",
            new_column_name="profit_per_unit_usd",
            existing_type=sa.DECIMAL(18, 8),
            existing_nullable=False,
        )

    cols = {c["name"] for c in insp.get_columns("products")}
    if "step_qty" not in cols:
        op.add_column("products", sa.Column("step_qty", sa.Integer(), nullable=False, server_default="1"))
