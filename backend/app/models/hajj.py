from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class HajjQuota(Base):
    __tablename__ = "hajj_quotas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name_ar: Mapped[str] = mapped_column(String(200))
    season: Mapped[str] = mapped_column(String(100), index=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("parties.id"), index=True)
    total_units: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    used_units: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"), nullable=False)
    branch_id: Mapped[int | None] = mapped_column(ForeignKey("branches.id"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    @property
    def remaining_units(self) -> int:
        return max(self.total_units - self.used_units, 0)
