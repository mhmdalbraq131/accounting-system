"""ERPNext-inspired accounting controls: dimensions, fiscal periods, audit logs."""
from alembic import op
import sqlalchemy as sa

revision = "20260925_0010"
down_revision = "20260915_0009"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "accounting_dimensions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("dimension_type", sa.String(length=30), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("name_ar", sa.String(length=200), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("branch_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_accounting_dimensions_code", "accounting_dimensions", ["code"], unique=True)
    op.create_index("ix_accounting_dimensions_dimension_type", "accounting_dimensions", ["dimension_type"])
    op.create_index("ix_accounting_dimensions_branch_id", "accounting_dimensions", ["branch_id"])

    op.create_table(
        "fiscal_periods",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("is_closed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("branch_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.UniqueConstraint("name", name="uq_fiscal_period_name"),
    )
    op.create_index("ix_fiscal_periods_name", "fiscal_periods", ["name"])
    op.create_index("ix_fiscal_periods_start_date", "fiscal_periods", ["start_date"])

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=40), nullable=False),
        sa.Column("entity_type", sa.String(length=80), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_entity_type", "audit_logs", ["entity_type"])
    op.create_index("ix_audit_logs_entity_id", "audit_logs", ["entity_id"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])

    op.add_column("journal_entries", sa.Column("fiscal_period_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_journal_entries_fiscal_period", "journal_entries", "fiscal_periods", ["fiscal_period_id"], ["id"])
    op.create_index("ix_journal_entries_fiscal_period_id", "journal_entries", ["fiscal_period_id"])

    op.add_column("journal_lines", sa.Column("dimension_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_journal_lines_dimension", "journal_lines", "accounting_dimensions", ["dimension_id"], ["id"])
    op.create_index("ix_journal_lines_dimension_id", "journal_lines", ["dimension_id"])

def downgrade():
    op.drop_index("ix_journal_lines_dimension_id", table_name="journal_lines")
    op.drop_constraint("fk_journal_lines_dimension", "journal_lines", type_="foreignkey")
    op.drop_column("journal_lines", "dimension_id")
    op.drop_index("ix_journal_entries_fiscal_period_id", table_name="journal_entries")
    op.drop_constraint("fk_journal_entries_fiscal_period", "journal_entries", type_="foreignkey")
    op.drop_column("journal_entries", "fiscal_period_id")
    for idx in ["ix_audit_logs_created_at","ix_audit_logs_entity_id","ix_audit_logs_entity_type","ix_audit_logs_action","ix_audit_logs_user_id"]:
        op.drop_index(idx, table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_index("ix_fiscal_periods_start_date", table_name="fiscal_periods")
    op.drop_index("ix_fiscal_periods_name", table_name="fiscal_periods")
    op.drop_table("fiscal_periods")
    op.drop_index("ix_accounting_dimensions_branch_id", table_name="accounting_dimensions")
    op.drop_index("ix_accounting_dimensions_dimension_type", table_name="accounting_dimensions")
    op.drop_index("ix_accounting_dimensions_code", table_name="accounting_dimensions")
    op.drop_table("accounting_dimensions")
