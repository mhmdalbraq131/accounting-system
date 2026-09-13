"""align branch-aware schema and scope journal entries

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


def _columns(table_name: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {col["name"] for col in inspector.get_columns(table_name)}


def _tables() -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return set(inspector.get_table_names())


def _add_branch_column(table_name: str) -> None:
    if "branch_id" not in _columns(table_name):
        op.add_column(table_name, sa.Column("branch_id", sa.Integer(), nullable=True))
    inspector = sa.inspect(op.get_bind())
    indexes = {idx["name"] for idx in inspector.get_indexes(table_name)}
    index_name = f"ix_{table_name}_branch_id"
    if index_name not in indexes:
        op.create_index(index_name, table_name, ["branch_id"])


def upgrade() -> None:
    tables = _tables()
    if "branches" not in tables:
        op.create_table(
            "branches",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("code", sa.String(30), nullable=False),
            sa.Column("name_ar", sa.String(200), nullable=False),
            sa.Column("address", sa.String(300), nullable=True),
            sa.Column("phone", sa.String(50), nullable=True),
            sa.Column("is_main", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        )
        op.create_index("ix_branches_code", "branches", ["code"], unique=True)

    for table_name in [
        "users",
        "accounts",
        "financial_accounts",
        "parties",
        "vouchers",
        "program_bookings",
        "visa_services",
        "expenses",
        "journal_entries",
    ]:
        if table_name in tables:
            _add_branch_column(table_name)

    for table_name in [
        "users",
        "accounts",
        "financial_accounts",
        "parties",
        "vouchers",
        "program_bookings",
        "visa_services",
        "expenses",
        "journal_entries",
    ]:
        if table_name not in tables:
            continue
        inspector = sa.inspect(op.get_bind())
        fk_names = {fk["name"] for fk in inspector.get_foreign_keys(table_name)}
        fk_name = f"fk_{table_name}_branch_id_branches"
        if fk_name not in fk_names:
            op.create_foreign_key(fk_name, table_name, "branches", ["branch_id"], ["id"])


def downgrade() -> None:
    tables = _tables()
    for table_name in [
        "journal_entries",
        "expenses",
        "visa_services",
        "program_bookings",
        "vouchers",
        "parties",
        "financial_accounts",
        "accounts",
        "users",
    ]:
        if table_name not in tables:
            continue
        inspector = sa.inspect(op.get_bind())
        fk_name = f"fk_{table_name}_branch_id_branches"
        if fk_name in {fk["name"] for fk in inspector.get_foreign_keys(table_name)}:
            op.drop_constraint(fk_name, table_name, type_="foreignkey")
        index_name = f"ix_{table_name}_branch_id"
        if index_name in {idx["name"] for idx in inspector.get_indexes(table_name)}:
            op.drop_index(index_name, table_name=table_name)
        if "branch_id" in _columns(table_name):
            op.drop_column(table_name, "branch_id")
    if "branches" in _tables():
        op.drop_index("ix_branches_code", table_name="branches")
        op.drop_table("branches")
