from sqlalchemy import inspect, text, select
from app.db.base import Base
from app.db.session import SessionLocal
from app.models.account import Account
from app.db.session import engine
from app import models  # noqa: F401


def ensure_schema_compatibility() -> None:
    """
    Safely bring older local databases forward without deleting existing data.

    The project currently uses SQLAlchemy models without a migration runner.
    create_all() handles missing tables; the explicit ALTER statements handle
    columns added to tables that already existed in older installations.
    """
    Base.metadata.create_all(bind=engine)

    inspector = inspect(engine)
    dialect = engine.dialect.name

    required_columns = {
        "program_bookings": {
            "supplier_paid_amount": "NUMERIC(18, 2) NOT NULL DEFAULT 0",
            "journal_entry_id": "INTEGER",
        },
        "travel_programs": {
            "supplier_id": "INTEGER",
        },
        "vouchers": {
            "beneficiary_name": "VARCHAR(200)",
        },
    }

    with engine.begin() as connection:
        for table, columns in required_columns.items():
            if not inspector.has_table(table):
                continue
            existing = {column["name"] for column in inspect(connection).get_columns(table)}
            for column, definition in columns.items():
                if column in existing:
                    continue
                if dialect == "sqlite":
                    connection.execute(text(f'ALTER TABLE "{table}" ADD COLUMN "{column}" {definition}'))
                else:
                    connection.execute(text(f'ALTER TABLE "{table}" ADD COLUMN "{column}" {definition}'))

    _ensure_default_chart_of_accounts()


def _ensure_default_chart_of_accounts() -> None:
    """
    Create the minimum standard chart without touching existing accounts.
    The chart follows the five standard financial-statement classifications;
    cost_of_service remains a dedicated system subtype of expenses.
    """
    defaults = [
        ("1000", "الأصول", "asset", None),
        ("1100", "النقدية والحسابات المالية", "asset", "1000"),
        ("1200", "العملاء والوكلاء", "asset", "1000"),
        ("1300", "الأصول الأخرى", "asset", "1000"),
        ("2000", "الخصوم", "liability", None),
        ("2100", "الموردون والدائنون", "liability", "2000"),
        ("2200", "الخصوم الأخرى", "liability", "2000"),
        ("3000", "حقوق الملكية", "equity", None),
        ("3100", "رأس المال", "equity", "3000"),
        ("3200", "الأرباح المحتجزة", "equity", "3000"),
        ("4000", "الإيرادات", "revenue", None),
        ("4100", "إيرادات الحج والعمرة", "revenue", "4000"),
        ("4200", "إيرادات الطيران", "revenue", "4000"),
        ("4300", "إيرادات الباصات", "revenue", "4000"),
        ("4400", "إيرادات الزيارات", "revenue", "4000"),
        ("4500", "إيرادات فيز العمل", "revenue", "4000"),
        ("5000", "المصروفات والتكاليف", "expense", None),
        ("5100", "تكلفة الخدمات", "cost_of_service", "5000"),
        ("5200", "المصروفات التشغيلية", "expense", "5000"),
    ]
    with SessionLocal() as db:
        by_code = {a.code: a for a in db.scalars(select(Account)).all()}
        for code, name, account_type, parent_code in defaults:
            if code in by_code:
                continue
            parent_id = by_code[parent_code].id if parent_code else None
            account = Account(
                code=code,
                name_ar=name,
                account_type=account_type,
                parent_id=parent_id,
                branch_id=None,
            )
            db.add(account)
            db.flush()
            by_code[code] = account
        db.commit()
