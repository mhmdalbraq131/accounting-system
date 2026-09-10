from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Expense(Base):
    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    expense_number: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    expense_date: Mapped[date] = mapped_column(Date)
    category: Mapped[str] = mapped_column(String(100), index=True)
    description: Mapped[str] = mapped_column(String(500))
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("parties.id"), nullable=True)
    program_id: Mapped[int | None] = mapped_column(ForeignKey("travel_programs.id"), nullable=True)
    payment_account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
