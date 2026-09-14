"""add shared service orders for flight, bus, visits and work visas

Revision ID: 20260914_0005
Revises: 20260914_0004
Create Date: 2026-09-14
"""

from alembic import op
import sqlalchemy as sa

revision = "20260914_0005"
down_revision = "20260914_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "service_orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("service_type", sa.String(length=30), nullable=False),
        sa.Column("reference_no", sa.String(length=60), nullable=False),
        sa.Column("service_date", sa.Date(), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("pilgrim_id", sa.Integer(), nullable=True),
        sa.Column("customer_id", sa.Integer(), nullable=True),
        sa.Column("agent_id", sa.Integer(), nullable=True),
        sa.Column("supplier_id", sa.Integer(), nullable=True),
        sa.Column("sale_price", sa.Numeric(18, 2), nullable=False),
        sa.Column("supplier_cost", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("paid_amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("remaining_amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("profit", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("journal_entry_id", sa.Integer(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("branch_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("posted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["pilgrim_id"], ["pilgrims.id"], name="fk_service_orders_pilgrim_id_pilgrims"),
        sa.ForeignKeyConstraint(["customer_id"], ["parties.id"], name="fk_service_orders_customer_id_parties"),
        sa.ForeignKeyConstraint(["agent_id"], ["parties.id"], name="fk_service_orders_agent_id_parties"),
        sa.ForeignKeyConstraint(["supplier_id"], ["parties.id"], name="fk_service_orders_supplier_id_parties"),
        sa.ForeignKeyConstraint(["journal_entry_id"], ["journal_entries.id"], name="fk_service_orders_journal_entry_id_journal_entries"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name="fk_service_orders_created_by_users"),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], name="fk_service_orders_branch_id_branches"),
        sa.UniqueConstraint("reference_no", name="uq_service_orders_reference_no"),
        sa.UniqueConstraint("journal_entry_id", name="uq_service_orders_journal_entry_id"),
    )
    op.create_index("ix_service_orders_service_type", "service_orders", ["service_type"])
    op.create_index("ix_service_orders_reference_no", "service_orders", ["reference_no"])
    op.create_index("ix_service_orders_pilgrim_id", "service_orders", ["pilgrim_id"])
    op.create_index("ix_service_orders_customer_id", "service_orders", ["customer_id"])
    op.create_index("ix_service_orders_agent_id", "service_orders", ["agent_id"])
    op.create_index("ix_service_orders_supplier_id", "service_orders", ["supplier_id"])
    op.create_index("ix_service_orders_branch_id", "service_orders", ["branch_id"])


def downgrade() -> None:
    op.drop_index("ix_service_orders_branch_id", table_name="service_orders")
    op.drop_index("ix_service_orders_supplier_id", table_name="service_orders")
    op.drop_index("ix_service_orders_agent_id", table_name="service_orders")
    op.drop_index("ix_service_orders_customer_id", table_name="service_orders")
    op.drop_index("ix_service_orders_pilgrim_id", table_name="service_orders")
    op.drop_index("ix_service_orders_reference_no", table_name="service_orders")
    op.drop_index("ix_service_orders_service_type", table_name="service_orders")
    op.drop_table("service_orders")
