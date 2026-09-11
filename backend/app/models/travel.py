from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TravelProgram(Base):
    __tablename__ = "travel_programs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name_ar: Mapped[str] = mapped_column(String(200))
    program_type: Mapped[str] = mapped_column(String(20), index=True)
    season: Mapped[str | None] = mapped_column(String(100), nullable=True)
    departure_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    return_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    capacity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sale_price: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"), nullable=False)
    supplier_cost: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    branch_id: Mapped[int | None] = mapped_column(ForeignKey("branches.id"), nullable=True, index=True)


class Pilgrim(Base):
    __tablename__ = "pilgrims"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("parties.id"), nullable=True)
    full_name: Mapped[str] = mapped_column(String(200), index=True)
    passport_number: Mapped[str | None] = mapped_column(String(50), index=True, nullable=True)
    nationality: Mapped[str | None] = mapped_column(String(100), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    visa_status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    branch_id: Mapped[int | None] = mapped_column(ForeignKey("branches.id"), nullable=True, index=True)


class ProgramBooking(Base):
    __tablename__ = "program_bookings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    program_id: Mapped[int] = mapped_column(ForeignKey("travel_programs.id"), index=True)
    pilgrim_id: Mapped[int] = mapped_column(ForeignKey("pilgrims.id"), index=True)
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("parties.id"), nullable=True)
    sale_price: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    supplier_cost: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"), nullable=False)
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"), nullable=False)
    remaining_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"), nullable=False)
    profit: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"), nullable=False)
    customer_type: Mapped[str] = mapped_column(String(20), default="direct", nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="reserved", nullable=False)
    booked_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    branch_id: Mapped[int | None] = mapped_column(ForeignKey("branches.id"), nullable=True, index=True)


class VisaService(Base):
    __tablename__ = "visa_services"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pilgrim_id: Mapped[int] = mapped_column(ForeignKey("pilgrims.id"), index=True)
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("parties.id"), nullable=True)
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("parties.id"), nullable=True)
    visa_type: Mapped[str] = mapped_column(String(100))
    sale_price: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    supplier_cost: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"), nullable=False)
    profit: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    branch_id: Mapped[int | None] = mapped_column(ForeignKey("branches.id"), nullable=True, index=True)
