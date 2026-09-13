"""add branch scope to journal entries

Revision ID: 20260913_0002
Revises: 20260913_0001
Create Date: 2026-09-13
"""

from alembic import op
import sqlalchemy as sa

revision = "20260913_0002"
down_revision = "20260913_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "journal_entries",
        sa.Column("branch_id", sa.Integer(), nullable=True),
    )
    op.create_index("ix_journal_entries_branch_id", "journal_entries", ["branch_id"])
    op.create_foreign_key(
        "fk_journal_entries_branch_id_branches",
        "journal_entries",
        "branches",
        ["branch_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_journal_entries_branch_id_branches", "journal_entries", type_="foreignkey")
    op.drop_index("ix_journal_entries_branch_id", table_name="journal_entries")
    op.drop_column("journal_entries", "branch_id")
