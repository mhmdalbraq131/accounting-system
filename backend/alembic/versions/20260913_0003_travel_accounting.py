"""link travel programs and services to accounting

Revision ID: 20260913_0003
Revises: 20260913_0002
Create Date: 2026-09-13
"""

from alembic import op
import sqlalchemy as sa

revision = "20260913_0003"
down_revision = "20260913_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("travel_programs", sa.Column("supplier_id", sa.Integer(), nullable=True))
    op.create_index("ix_travel_programs_supplier_id", "travel_programs", ["supplier_id"])
    op.create_foreign_key(
        "fk_travel_programs_supplier_id_parties",
        "travel_programs",
        "parties",
        ["supplier_id"],
        ["id"],
    )

    op.add_column("program_bookings", sa.Column("journal_entry_id", sa.Integer(), nullable=True))
    op.create_unique_constraint("uq_program_bookings_journal_entry_id", "program_bookings", ["journal_entry_id"])
    op.create_foreign_key(
        "fk_program_bookings_journal_entry_id_journal_entries",
        "program_bookings",
        "journal_entries",
        ["journal_entry_id"],
        ["id"],
    )

    op.add_column("visa_services", sa.Column("journal_entry_id", sa.Integer(), nullable=True))
    op.create_unique_constraint("uq_visa_services_journal_entry_id", "visa_services", ["journal_entry_id"])
    op.create_foreign_key(
        "fk_visa_services_journal_entry_id_journal_entries",
        "visa_services",
        "journal_entries",
        ["journal_entry_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_visa_services_journal_entry_id_journal_entries", "visa_services", type_="foreignkey")
    op.drop_constraint("uq_visa_services_journal_entry_id", "visa_services", type_="unique")
    op.drop_column("visa_services", "journal_entry_id")

    op.drop_constraint("fk_program_bookings_journal_entry_id_journal_entries", "program_bookings", type_="foreignkey")
    op.drop_constraint("uq_program_bookings_journal_entry_id", "program_bookings", type_="unique")
    op.drop_column("program_bookings", "journal_entry_id")

    op.drop_constraint("fk_travel_programs_supplier_id_parties", "travel_programs", type_="foreignkey")
    op.drop_index("ix_travel_programs_supplier_id", table_name="travel_programs")
    op.drop_column("travel_programs", "supplier_id")
