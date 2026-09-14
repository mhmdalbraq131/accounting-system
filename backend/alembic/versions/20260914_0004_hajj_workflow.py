"""add hajj quotas, agent links, and voucher service references

Revision ID: 20260914_0004
Revises: 20260913_0003
Create Date: 2026-09-14
"""

from alembic import op
import sqlalchemy as sa

revision = "20260914_0004"
down_revision = "20260913_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "hajj_quotas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name_ar", sa.String(length=200), nullable=False),
        sa.Column("season", sa.String(length=100), nullable=False),
        sa.Column("supplier_id", sa.Integer(), nullable=False),
        sa.Column("total_units", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("used_units", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unit_cost", sa.Numeric(precision=18, scale=2), nullable=False, server_default="0"),
        sa.Column("branch_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="open"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["supplier_id"], ["parties.id"], name="fk_hajj_quotas_supplier_id_parties"),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], name="fk_hajj_quotas_branch_id_branches"),
    )
    op.create_index("ix_hajj_quotas_season", "hajj_quotas", ["season"])
    op.create_index("ix_hajj_quotas_supplier_id", "hajj_quotas", ["supplier_id"])
    op.create_index("ix_hajj_quotas_branch_id", "hajj_quotas", ["branch_id"])

    op.add_column("program_bookings", sa.Column("agent_id", sa.Integer(), nullable=True))
    op.add_column("program_bookings", sa.Column("quota_id", sa.Integer(), nullable=True))
    op.add_column("program_bookings", sa.Column("supplier_id", sa.Integer(), nullable=True))
    op.create_index("ix_program_bookings_agent_id", "program_bookings", ["agent_id"])
    op.create_index("ix_program_bookings_quota_id", "program_bookings", ["quota_id"])
    op.create_index("ix_program_bookings_supplier_id", "program_bookings", ["supplier_id"])
    op.create_foreign_key("fk_program_bookings_agent_id_parties", "program_bookings", "parties", ["agent_id"], ["id"])
    op.create_foreign_key("fk_program_bookings_quota_id_hajj_quotas", "program_bookings", "hajj_quotas", ["quota_id"], ["id"])
    op.create_foreign_key("fk_program_bookings_supplier_id_parties", "program_bookings", "parties", ["supplier_id"], ["id"])

    op.add_column("vouchers", sa.Column("linked_service_type", sa.String(length=40), nullable=True))
    op.add_column("vouchers", sa.Column("linked_service_id", sa.Integer(), nullable=True))
    op.create_index("ix_vouchers_linked_service", "vouchers", ["linked_service_type", "linked_service_id"])


def downgrade() -> None:
    op.drop_index("ix_vouchers_linked_service", table_name="vouchers")
    op.drop_column("vouchers", "linked_service_id")
    op.drop_column("vouchers", "linked_service_type")

    op.drop_constraint("fk_program_bookings_supplier_id_parties", "program_bookings", type_="foreignkey")
    op.drop_constraint("fk_program_bookings_quota_id_hajj_quotas", "program_bookings", type_="foreignkey")
    op.drop_constraint("fk_program_bookings_agent_id_parties", "program_bookings", type_="foreignkey")
    op.drop_index("ix_program_bookings_supplier_id", table_name="program_bookings")
    op.drop_index("ix_program_bookings_quota_id", table_name="program_bookings")
    op.drop_index("ix_program_bookings_agent_id", table_name="program_bookings")
    op.drop_column("program_bookings", "supplier_id")
    op.drop_column("program_bookings", "quota_id")
    op.drop_column("program_bookings", "agent_id")

    op.drop_index("ix_hajj_quotas_branch_id", table_name="hajj_quotas")
    op.drop_index("ix_hajj_quotas_supplier_id", table_name="hajj_quotas")
    op.drop_index("ix_hajj_quotas_season", table_name="hajj_quotas")
    op.drop_table("hajj_quotas")
