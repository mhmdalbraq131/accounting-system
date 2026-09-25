from sqlalchemy import inspect, text
from app.db.base import Base
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
        },
        "travel_programs": {
            "supplier_id": "INTEGER",
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
