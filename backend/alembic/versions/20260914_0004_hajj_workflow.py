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


def _columns(table_name: str) -> set[str]:
    return {col["name"] for col in sa.inspect(op.get_bind()).get_columns(table_name)}


def _indexes(table_name: str) -> set[str]:
    return {idx["name"] for idx in sa.inspect(op.get_bind()).get_indexes(table_name)}


def _foreign_keys(table_name: str) -> set[str]:
    return {
        fk["name"]
        for fk in sa.inspect(op.get_bind()).get_foreign_keys(table_name)
        if fk.get("name")
    }


def _ensure_foreign_keys(table_name: str, foreign_keys: list[tuple[str, str, str, list[str], list[str]]]) -> None:
    """Add foreign keys on both PostgreSQL and SQLite.

    SQLite does not support ALTER TABLE ... ADD CONSTRAINT directly, so
    Alembic batch mode is required there. The migration is also idempotent
    because this revision may have partially run before an SQLite failure.
    """
    bind = op.get_bind()
    existing = _foreign_keys(table_name)
    missing = [item for item in foreign_keys if item[0] not in existing]
    if not missing:
        return

    if bind.dialect.name == "sqlite":
        with op.batch_alter_table(table_name, recreate="always") as batch_op:
            for name, referred_table, _referred_column, local_cols, remote_cols in missing:
                batch_op.create_foreign_key(
                    name,
                    referred_table,
                    local_cols,
                    remote_cols,
                )
    else:
        for name, referred_table, _referred_column, local_cols, remote_cols in missing:
            op.create_foreign_key(
                name,
                table_name,
                referred_table,
                local_cols,
                remote_cols,
            )


def upgrade() -> None:
    tables = set(sa.inspect(op.get_bind()).get_table_names())

    if "hajj_quotas" not in tables:
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

    quota_indexes = _indexes("hajj_quotas")
    for index_name, columns, unique in [
        ("ix_hajj_quotas_season", ["season"], False),
        ("ix_hajj_quotas_supplier_id", ["supplier_id"], False),
        ("ix_hajj_quotas_branch_id", ["branch_id"], False),
    ]:
        if index_name not in quota_indexes:
            op.create_index(index_name, "hajj_quotas", columns, unique=unique)

    booking_columns = _columns("program_bookings")
    for name, column in [
        ("agent_id", sa.Column("agent_id", sa.Integer(), nullable=True)),
        ("quota_id", sa.Column("quota_id", sa.Integer(), nullable=True)),
        ("supplier_id", sa.Column("supplier_id", sa.Integer(), nullable=True)),
    ]:
        if name not in booking_columns:
            op.add_column("program_bookings", column)

    booking_indexes = _indexes("program_bookings")
    for index_name, columns in [
        ("ix_program_bookings_agent_id", ["agent_id"]),
        ("ix_program_bookings_quota_id", ["quota_id"]),
        ("ix_program_bookings_supplier_id", ["supplier_id"]),
    ]:
        if index_name not in booking_indexes:
            op.create_index(index_name, "program_bookings", columns)

    _ensure_foreign_keys(
        "program_bookings",
        [
            (
                "fk_program_bookings_agent_id_parties",
                "parties",
                "id",
                ["agent_id"],
                ["id"],
            ),
            (
                "fk_program_bookings_quota_id_hajj_quotas",
                "hajj_quotas",
                "id",
                ["quota_id"],
                ["id"],
            ),
            (
                "fk_program_bookings_supplier_id_parties",
                "parties",
                "id",
                ["supplier_id"],
                ["id"],
            ),
        ],
    )

    voucher_columns = _columns("vouchers")
    if "linked_service_type" not in voucher_columns:
        op.add_column("vouchers", sa.Column("linked_service_type", sa.String(length=40), nullable=True))
    if "linked_service_id" not in voucher_columns:
        op.add_column("vouchers", sa.Column("linked_service_id", sa.Integer(), nullable=True))
    if "ix_vouchers_linked_service" not in _indexes("vouchers"):
        op.create_index("ix_vouchers_linked_service", "vouchers", ["linked_service_type", "linked_service_id"])


def downgrade() -> None:
    if "ix_vouchers_linked_service" in _indexes("vouchers"):
        op.drop_index("ix_vouchers_linked_service", table_name="vouchers")
    voucher_columns = _columns("vouchers")
    if "linked_service_id" in voucher_columns:
        op.drop_column("vouchers", "linked_service_id")
    if "linked_service_type" in voucher_columns:
        op.drop_column("vouchers", "linked_service_type")

    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "program_bookings" in tables:
        fk_names = _foreign_keys("program_bookings")
        for name in [
            "fk_program_bookings_supplier_id_parties",
            "fk_program_bookings_quota_id_hajj_quotas",
            "fk_program_bookings_agent_id_parties",
        ]:
            if name in fk_names:
                if op.get_bind().dialect.name == "sqlite":
                    with op.batch_alter_table("program_bookings", recreate="always") as batch_op:
                        batch_op.drop_constraint(name, type="foreignkey")
                    fk_names = _foreign_keys("program_bookings")
                else:
                    op.drop_constraint(name, "program_bookings", type="foreignkey")

        booking_indexes = _indexes("program_bookings")
        for index_name in [
            "ix_program_bookings_supplier_id",
            "ix_program_bookings_quota_id",
            "ix_program_bookings_agent_id",
        ]:
            if index_name in booking_indexes:
                op.drop_index(index_name, table_name="program_bookings")

        booking_columns = _columns("program_bookings")
        for column_name in ["supplier_id", "quota_id", "agent_id"]:
            if column_name in booking_columns:
                op.drop_column("program_bookings", column_name)

    if "hajj_quotas" in set(sa.inspect(op.get_bind()).get_table_names()):
        for index_name in [
            "ix_hajj_quotas_branch_id",
            "ix_hajj_quotas_supplier_id",
            "ix_hajj_quotas_season",
        ]:
            if index_name in _indexes("hajj_quotas"):
                op.drop_index(index_name, table_name="hajj_quotas")
        op.drop_table("hajj_quotas")
