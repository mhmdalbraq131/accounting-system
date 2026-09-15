"""track supplier payments on services

Revision ID: 20260915_0007
Revises: 20260915_0006
Create Date: 2026-09-15
"""

from alembic import op
import sqlalchemy as sa

revision = "20260915_0007"
down_revision = "20260915_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("program_bookings") as batch:
        batch.add_column(sa.Column("supplier_paid_amount", sa.Numeric(18, 2), nullable=False, server_default="0"))
    with op.batch_alter_table("service_orders") as batch:
        batch.add_column(sa.Column("supplier_paid_amount", sa.Numeric(18, 2), nullable=False, server_default="0"))


def downgrade() -> None:
    with op.batch_alter_table("service_orders") as batch:
        batch.drop_column("supplier_paid_amount")
    with op.batch_alter_table("program_bookings") as batch:
        batch.drop_column("supplier_paid_amount")
