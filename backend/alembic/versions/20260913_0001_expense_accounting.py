"""link expenses to accounting journals

Revision ID: 20260913_0001
Revises:
Create Date: 2026-09-13
"""

from alembic import op
import sqlalchemy as sa

revision = "20260913_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("expenses", sa.Column("expense_account_id", sa.Integer(), nullable=True))
    op.add_column("expenses", sa.Column("journal_entry_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_expenses_expense_account_id_accounts",
        "expenses",
        "accounts",
        ["expense_account_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_expenses_journal_entry_id_journal_entries",
        "expenses",
        "journal_entries",
        ["journal_entry_id"],
        ["id"],
    )
    op.create_unique_constraint("uq_expenses_journal_entry_id", "expenses", ["journal_entry_id"])


def downgrade() -> None:
    op.drop_constraint("uq_expenses_journal_entry_id", "expenses", type_="unique")
    op.drop_constraint("fk_expenses_journal_entry_id_journal_entries", "expenses", type_="foreignkey")
    op.drop_constraint("fk_expenses_expense_account_id_accounts", "expenses", type_="foreignkey")
    op.drop_column("expenses", "journal_entry_id")
    op.drop_column("expenses", "expense_account_id")
