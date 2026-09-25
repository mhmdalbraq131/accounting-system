from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db.session import get_db
from app.models.account import Account
from app.models.expense import Expense
from app.models.journal import JournalEntry, JournalLine
from app.models.party import Party
from app.models.travel import Pilgrim, ProgramBooking, TravelProgram, VisaService
from app.models.user import User

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@router.get("")
def dashboard(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    branch_filter = lambda stmt, col: stmt if user.branch_id is None else stmt.where((col == user.branch_id) | col.is_(None))
    programs = db.scalar(branch_filter(select(func.count(TravelProgram.id)).where(TravelProgram.is_active.is_(True)), TravelProgram.branch_id)) or 0
    pilgrims = db.scalar(branch_filter(select(func.count(Pilgrim.id)), Pilgrim.branch_id)) or 0
    bookings = db.scalar(branch_filter(select(func.count(ProgramBooking.id)), ProgramBooking.branch_id)) or 0
    visas = db.scalar(branch_filter(select(func.count(VisaService.id)), VisaService.branch_id)) or 0
    customers = db.scalar(branch_filter(select(func.count(Party.id)).where(Party.party_type == "customer", Party.is_active.is_(True)), Party.branch_id)) or 0
    suppliers = db.scalar(branch_filter(select(func.count(Party.id)).where(Party.party_type == "supplier", Party.is_active.is_(True)), Party.branch_id)) or 0
    journal_base = (
        select(JournalLine)
        .join(JournalEntry, JournalLine.journal_entry_id == JournalEntry.id)
        .join(Account, JournalLine.account_id == Account.id)
        .where(JournalEntry.status == "posted")
    )
    if user.branch_id is not None:
        journal_base = journal_base.where((JournalEntry.branch_id == user.branch_id) | JournalEntry.branch_id.is_(None))
    journal_rows = db.execute(journal_base).scalars().all()
    revenue = Decimal("0")
    service_cost = Decimal("0")
    expenses = Decimal("0")
    for line in journal_rows:
        account = db.get(Account, line.account_id)
        if account.account_type == "revenue":
            revenue += Decimal(str(line.credit or 0)) - Decimal(str(line.debit or 0))
        elif account.account_type == "cost_of_service":
            service_cost += Decimal(str(line.debit or 0)) - Decimal(str(line.credit or 0))
        elif account.account_type == "expense":
            expenses += Decimal(str(line.debit or 0)) - Decimal(str(line.credit or 0))
    posted_stmt = select(func.count(JournalEntry.id)).where(JournalEntry.status == "posted")
    if user.branch_id is not None:
        posted_stmt = posted_stmt.where((JournalEntry.branch_id == user.branch_id) | JournalEntry.branch_id.is_(None))
    posted_journals = db.scalar(posted_stmt) or 0
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
