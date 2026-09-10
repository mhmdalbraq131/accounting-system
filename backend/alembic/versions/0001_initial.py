from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(100), nullable=False),
        sa.Column("full_name", sa.String(200), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.create_table("roles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_roles_name", "roles", ["name"], unique=True)
    op.create_table("permissions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(120), nullable=False),
        sa.Column("name_ar", sa.String(200), nullable=False),
    )
    op.create_index("ix_permissions_code", "permissions", ["code"], unique=True)
    op.create_table("accounts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(30), nullable=False),
        sa.Column("name_ar", sa.String(200), nullable=False),
        sa.Column("account_type", sa.String(30), nullable=False),
        sa.Column("parent_id", sa.Integer()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("opening_balance", sa.Numeric(18, 2), nullable=False, server_default="0"),
    )
    op.create_index("ix_accounts_code", "accounts", ["code"], unique=True)
    op.create_table("financial_accounts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("account_type", sa.String(20), nullable=False),
        sa.Column("ledger_account_id", sa.Integer(), sa.ForeignKey("accounts.id"), nullable=False),
        sa.Column("opening_balance", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_financial_accounts_account_type", "financial_accounts", ["account_type"])
    op.create_table("parties",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("party_type", sa.String(20), nullable=False),
        sa.Column("phone", sa.String(50)),
        sa.Column("address", sa.String(300)),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_table("journal_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entry_number", sa.String(40), nullable=False),
        sa.Column("entry_date", sa.Date(), nullable=False),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("created_by", sa.Integer()),
        sa.Column("posted_at", sa.DateTime()),
    )
    op.create_index("ix_journal_entries_entry_number", "journal_entries", ["entry_number"], unique=True)
    op.create_table("journal_lines",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("journal_entry_id", sa.Integer(), sa.ForeignKey("journal_entries.id", ondelete="CASCADE"), nullable=False),
        sa.Column("account_id", sa.Integer(), sa.ForeignKey("accounts.id"), nullable=False),
        sa.Column("description", sa.String(500)),
        sa.Column("debit", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("credit", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.CheckConstraint("debit >= 0 AND credit >= 0 AND NOT (debit > 0 AND credit > 0)", name="ck_journal_line_one_side"),
    )
    op.create_index("ix_journal_lines_journal_entry_id", "journal_lines", ["journal_entry_id"])
    op.create_index("ix_journal_lines_account_id", "journal_lines", ["account_id"])
    op.create_table("vouchers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("voucher_number", sa.String(40), nullable=False),
        sa.Column("voucher_type", sa.String(20), nullable=False),
        sa.Column("voucher_date", sa.Date(), nullable=False),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("source_account_id", sa.Integer(), sa.ForeignKey("accounts.id")),
        sa.Column("destination_account_id", sa.Integer(), sa.ForeignKey("accounts.id")),
        sa.Column("journal_entry_id", sa.Integer(), sa.ForeignKey("journal_entries.id"), unique=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("posted_at", sa.DateTime()),
    )
    op.create_index("ix_vouchers_voucher_number", "vouchers", ["voucher_number"], unique=True)
    op.create_table("user_roles",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("role_id", sa.Integer(), sa.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    )
    op.create_table("role_permissions",
        sa.Column("role_id", sa.Integer(), sa.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("permission_id", sa.Integer(), sa.ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
    )


def downgrade() -> None:
    for table in ["role_permissions", "user_roles", "vouchers", "journal_lines", "journal_entries", "parties", "financial_accounts", "accounts", "permissions", "roles", "users"]:
        op.drop_table(table)
