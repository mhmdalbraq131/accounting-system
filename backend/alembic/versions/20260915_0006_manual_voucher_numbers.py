"""add manual voucher numbers

Revision ID: 20260915_0006
Revises: 20260914_0005
Create Date: 2026-09-15
"""

from alembic import op
import sqlalchemy as sa

revision = "20260915_0006"
down_revision = "20260914_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("vouchers") as batch:
        batch.add_column(sa.Column("manual_voucher_number", sa.String(length=80), nullable=True))
        batch.create_index("ix_vouchers_manual_voucher_number", ["manual_voucher_number"], unique=True)


def downgrade() -> None:
    with op.batch_alter_table("vouchers") as batch:
        batch.drop_index("ix_vouchers_manual_voucher_number")
        batch.drop_column("manual_voucher_number")
