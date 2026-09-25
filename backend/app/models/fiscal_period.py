from datetime import date
from sqlalchemy import Boolean, Date, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class FiscalPeriod(Base):
    __tablename__ = "fiscal_periods"
    __table_args__ = (UniqueConstraint("name", name="uq_fiscal_period_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), index=True)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    is_closed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    branch_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("branches.id"), nullable=True, index=True)
