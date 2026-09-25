"""Add accounting dimension to expenses."""
from alembic import op
import sqlalchemy as sa

revision = "20260925_0011"
down_revision = "20260925_0010"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("expenses", sa.Column("dimension_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_expenses_dimension",
        "expenses",
        "accounting_dimensions",
        ["dimension_id"],
        ["id"],
    )
    op.create_index("ix_expenses_dimension_id", "expenses", ["dimension_id"])


def downgrade():
    op.drop_index("ix_expenses_dimension_id", table_name="expenses")
    op.drop_constraint("fk_expenses_dimension", "expenses", type_="foreignkey")
    op.drop_column("expenses", "dimension_id")
