"""Add receivables, payables, payments and allocations."""
from alembic import op
import sqlalchemy as sa

revision = "20260925_0012"
down_revision = "20260925_0011"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "invoices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("invoice_number", sa.String(length=50), nullable=False),
        sa.Column("invoice_type", sa.String(length=20), nullable=False),
        sa.Column("party_id", sa.Integer(), sa.ForeignKey("parties.id"), nullable=False),
        sa.Column("invoice_date", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("total_amount", sa.Numeric(18,2), nullable=False),
        sa.Column("paid_amount", sa.Numeric(18,2), nullable=False, server_default="0"),
        sa.Column("remaining_amount", sa.Numeric(18,2), nullable=False, server_default="0"),
        sa.Column("receivable_account_id", sa.Integer(), sa.ForeignKey("accounts.id"), nullable=False),
        sa.Column("revenue_account_id", sa.Integer(), sa.ForeignKey("accounts.id"), nullable=False),
        sa.Column("journal_entry_id", sa.Integer(), sa.ForeignKey("journal_entries.id"), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("branch_id", sa.Integer(), sa.ForeignKey("branches.id"), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("invoice_number"),
        sa.UniqueConstraint("journal_entry_id"),
    )
    op.create_index("ix_invoices_invoice_number","invoices",["invoice_number"])
    op.create_index("ix_invoices_invoice_type","invoices",["invoice_type"])
    op.create_index("ix_invoices_party_id","invoices",["party_id"])
    op.create_index("ix_invoices_branch_id","invoices",["branch_id"])
    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("payment_number", sa.String(length=50), nullable=False),
        sa.Column("payment_type", sa.String(length=20), nullable=False),
        sa.Column("party_id", sa.Integer(), sa.ForeignKey("parties.id"), nullable=True),
        sa.Column("payment_date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(18,2), nullable=False),
        sa.Column("allocated_amount", sa.Numeric(18,2), nullable=False, server_default="0"),
        sa.Column("remaining_amount", sa.Numeric(18,2), nullable=False, server_default="0"),
        sa.Column("source_account_id", sa.Integer(), sa.ForeignKey("accounts.id"), nullable=False),
        sa.Column("target_account_id", sa.Integer(), sa.ForeignKey("accounts.id"), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("journal_entry_id", sa.Integer(), sa.ForeignKey("journal_entries.id"), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("branch_id", sa.Integer(), sa.ForeignKey("branches.id"), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("payment_number"),
        sa.UniqueConstraint("journal_entry_id"),
    )
    op.create_index("ix_payments_payment_number","payments",["payment_number"])
    op.create_index("ix_payments_payment_type","payments",["payment_type"])
    op.create_index("ix_payments_party_id","payments",["party_id"])
    op.create_index("ix_payments_branch_id","payments",["branch_id"])
    op.create_table(
        "payment_allocations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("payment_id", sa.Integer(), sa.ForeignKey("payments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("invoice_id", sa.Integer(), sa.ForeignKey("invoices.id"), nullable=False),
        sa.Column("amount", sa.Numeric(18,2), nullable=False),
    )
    op.create_index("ix_payment_allocations_payment_id","payment_allocations",["payment_id"])
    op.create_index("ix_payment_allocations_invoice_id","payment_allocations",["invoice_id"])

def downgrade():
    op.drop_index("ix_payment_allocations_invoice_id",table_name="payment_allocations")
    op.drop_index("ix_payment_allocations_payment_id",table_name="payment_allocations")
    op.drop_table("payment_allocations")
    op.drop_constraint("payments_journal_entry_id_key","payments",type_="unique")
    op.drop_index("ix_payments_branch_id",table_name="payments")
    op.drop_index("ix_payments_party_id",table_name="payments")
    op.drop_index("ix_payments_payment_type",table_name="payments")
    op.drop_index("ix_payments_payment_number",table_name="payments")
    op.drop_table("payments")
    op.drop_constraint("invoices_journal_entry_id_key","invoices",type_="unique")
    op.drop_index("ix_invoices_branch_id",table_name="invoices")
    op.drop_index("ix_invoices_party_id",table_name="invoices")
    op.drop_index("ix_invoices_invoice_type",table_name="invoices")
    op.drop_index("ix_invoices_invoice_number",table_name="invoices")
    op.drop_table("invoices")
