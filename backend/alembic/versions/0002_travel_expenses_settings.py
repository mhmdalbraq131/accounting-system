from alembic import op
import sqlalchemy as sa

revision = "0002_travel_expenses_settings"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "travel_programs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("name_ar", sa.String(200), nullable=False),
        sa.Column("program_type", sa.String(20), nullable=False),
        sa.Column("season", sa.String(100)),
        sa.Column("departure_date", sa.Date()),
        sa.Column("return_date", sa.Date()),
        sa.Column("capacity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sale_price", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("supplier_cost", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.CheckConstraint("capacity >= 0", name="ck_travel_program_capacity_nonnegative"),
        sa.CheckConstraint("sale_price >= 0 AND supplier_cost >= 0", name="ck_travel_program_amounts_nonnegative"),
    )
    op.create_index("ix_travel_programs_code", "travel_programs", ["code"], unique=True)
    op.create_index("ix_travel_programs_program_type", "travel_programs", ["program_type"])

    op.create_table(
        "pilgrims",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("parties.id")),
        sa.Column("full_name", sa.String(200), nullable=False),
        sa.Column("passport_number", sa.String(50)),
        sa.Column("nationality", sa.String(100)),
        sa.Column("phone", sa.String(50)),
        sa.Column("visa_status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_pilgrims_full_name", "pilgrims", ["full_name"])
    op.create_index("ix_pilgrims_passport_number", "pilgrims", ["passport_number"])

    op.create_table(
        "program_bookings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("program_id", sa.Integer(), sa.ForeignKey("travel_programs.id"), nullable=False),
        sa.Column("pilgrim_id", sa.Integer(), sa.ForeignKey("pilgrims.id"), nullable=False),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("parties.id")),
        sa.Column("sale_price", sa.Numeric(18, 2), nullable=False),
        sa.Column("supplier_cost", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("paid_amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("remaining_amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("profit", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("customer_type", sa.String(20), nullable=False, server_default="direct"),
        sa.Column("status", sa.String(30), nullable=False, server_default="reserved"),
        sa.Column("booked_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("sale_price >= 0 AND supplier_cost >= 0 AND paid_amount >= 0 AND remaining_amount >= 0", name="ck_booking_amounts_nonnegative"),
    )
    op.create_index("ix_program_bookings_program_id", "program_bookings", ["program_id"])
    op.create_index("ix_program_bookings_pilgrim_id", "program_bookings", ["pilgrim_id"])

    op.create_table(
        "visa_services",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("pilgrim_id", sa.Integer(), sa.ForeignKey("pilgrims.id"), nullable=False),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("parties.id")),
        sa.Column("supplier_id", sa.Integer(), sa.ForeignKey("parties.id")),
        sa.Column("visa_type", sa.String(100), nullable=False),
        sa.Column("sale_price", sa.Numeric(18, 2), nullable=False),
        sa.Column("supplier_cost", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("profit", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("sale_price >= 0 AND supplier_cost >= 0", name="ck_visa_amounts_nonnegative"),
    )
    op.create_index("ix_visa_services_pilgrim_id", "visa_services", ["pilgrim_id"])

    op.create_table(
        "expenses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("expense_number", sa.String(40), nullable=False),
        sa.Column("expense_date", sa.Date(), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("supplier_id", sa.Integer(), sa.ForeignKey("parties.id")),
        sa.Column("program_id", sa.Integer(), sa.ForeignKey("travel_programs.id")),
        sa.Column("payment_account_id", sa.Integer(), sa.ForeignKey("accounts.id")),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("amount >= 0", name="ck_expense_amount_nonnegative"),
    )
    op.create_index("ix_expenses_expense_number", "expenses", ["expense_number"], unique=True)
    op.create_index("ix_expenses_category", "expenses", ["category"])

    op.create_table(
        "system_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("key", sa.String(120), nullable=False),
        sa.Column("value", sa.Text(), nullable=False, server_default=""),
        sa.Column("value_type", sa.String(20), nullable=False, server_default="string"),
        sa.Column("category", sa.String(40), nullable=False, server_default="general"),
        sa.Column("description_ar", sa.String(500)),
        sa.Column("is_editable", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_system_settings_key", "system_settings", ["key"], unique=True)
    op.create_index("ix_system_settings_category", "system_settings", ["category"])


def downgrade() -> None:
    for table in ["system_settings", "expenses", "visa_services", "program_bookings", "pilgrims", "travel_programs"]:
        op.drop_table(table)
