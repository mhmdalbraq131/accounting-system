"""add suggested currencies and protect the system base currency

Revision ID: 20260915_0009
Revises: 20260915_0008
Create Date: 2026-09-15
"""

from alembic import op
import sqlalchemy as sa

revision = "20260915_0009"
down_revision = "20260915_0008"
branch_labels = None
depends_on = None

SUGGESTED_CURRENCIES = [
    ("YER", "الريال اليمني", "ر.ي"),
    ("SAR", "الريال السعودي", "ر.س"),
    ("USD", "الدولار الأمريكي", "$"),
]


def upgrade() -> None:
    bind = op.get_bind()
    for code, name_ar, symbol in SUGGESTED_CURRENCIES:
        bind.execute(
            sa.text(
                "INSERT INTO currencies (code, name_ar, symbol, is_base, is_active) "
                "SELECT :code, :name_ar, :symbol, false, true "
                "WHERE NOT EXISTS (SELECT 1 FROM currencies WHERE code = :code)"
            ),
            {"code": code, "name_ar": name_ar, "symbol": symbol},
        )


def downgrade() -> None:
    bind = op.get_bind()
    for code, _, _ in SUGGESTED_CURRENCIES:
        bind.execute(sa.text("DELETE FROM currencies WHERE code = :code"), {"code": code})
