from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db.session import get_db
from app.models.expense import Expense
from app.models.journal import JournalEntry
from app.models.party import Party
from app.models.travel import Pilgrim, ProgramBooking, TravelProgram, VisaService
from app.models.user import User

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@router.get("")
def dashboard(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    programs = db.scalar(select(func.count(TravelProgram.id)).where(TravelProgram.is_active.is_(True))) or 0
    pilgrims = db.scalar(select(func.count(Pilgrim.id))) or 0
    bookings = db.scalar(select(func.count(ProgramBooking.id))) or 0
    visas = db.scalar(select(func.count(VisaService.id))) or 0
    customers = db.scalar(select(func.count(Party.id)).where(Party.party_type == "customer", Party.is_active.is_(True))) or 0
    suppliers = db.scalar(select(func.count(Party.id)).where(Party.party_type == "supplier", Party.is_active.is_(True))) or 0
    expenses = db.scalar(select(func.coalesce(func.sum(Expense.amount), 0)).where(Expense.status != "cancelled")) or Decimal("0")
    revenue = db.scalar(select(func.coalesce(func.sum(ProgramBooking.sale_price), 0))) or Decimal("0")
    service_cost = db.scalar(select(func.coalesce(func.sum(ProgramBooking.supplier_cost), 0))) or Decimal("0")
    visa_revenue = db.scalar(select(func.coalesce(func.sum(VisaService.sale_price), 0))) or Decimal("0")
    visa_cost = db.scalar(select(func.coalesce(func.sum(VisaService.supplier_cost), 0))) or Decimal("0")
    posted_journals = db.scalar(select(func.count(JournalEntry.id)).where(JournalEntry.status == "posted")) or 0
    return {
        "programs": programs,
        "pilgrims": pilgrims,
        "bookings": bookings,
        "visas": visas,
        "customers": customers,
        "suppliers": suppliers,
        "revenue": revenue + visa_revenue,
        "service_cost": service_cost + visa_cost,
        "gross_profit": (revenue + visa_revenue) - (service_cost + visa_cost),
        "expenses": expenses,
        "net_profit": (revenue + visa_revenue) - (service_cost + visa_cost) - expenses,
        "posted_journals": posted_journals,
    }
