from datetime import date
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.auth import get_current_user
from app.db.session import get_db
from app.models.expense import Expense
from app.models.journal import JournalEntry, JournalLine
from app.models.party import Party
from app.models.travel import ProgramBooking, VisaService
from app.models.user import User

router = APIRouter(prefix="/reports", tags=["التقارير"])

def scope(stmt, col, user):
    return stmt if user.branch_id is None else stmt.where((col == user.branch_id) | col.is_(None))

@router.get("/financial-summary")
def financial_summary(from_date: date | None = None, to_date: date | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    def dated(stmt, col):
        if from_date: stmt=stmt.where(col >= from_date)
        if to_date: stmt=stmt.where(col <= to_date)
        return stmt
    rev = db.scalar(scope(dated(select(func.coalesce(func.sum(ProgramBooking.sale_price),0)), ProgramBooking.booked_at, user), ProgramBooking.branch_id, user)) or 0
    visa_rev = db.scalar(scope(dated(select(func.coalesce(func.sum(VisaService.sale_price),0)), VisaService.created_at, user), VisaService.branch_id, user)) or 0
    cost = db.scalar(scope(dated(select(func.coalesce(func.sum(ProgramBooking.supplier_cost),0)), ProgramBooking.booked_at, user), ProgramBooking.branch_id, user)) or 0
    visa_cost = db.scalar(scope(dated(select(func.coalesce(func.sum(VisaService.supplier_cost),0)), VisaService.created_at, user), VisaService.branch_id, user)) or 0
    exp = db.scalar(scope(dated(select(func.coalesce(func.sum(Expense.amount),0)).where(Expense.status != "cancelled"), Expense.expense_date, user), Expense.branch_id, user)) or 0
    revenue=rev+visa_rev; service_cost=cost+visa_cost
    return {"from_date":from_date,"to_date":to_date,"revenue":revenue,"service_cost":service_cost,"gross_profit":revenue-service_cost,"expenses":exp,"net_profit":revenue-service_cost-exp,"printed_by":user.full_name,"username":user.username,"branch_id":user.branch_id}

@router.get("/party/{party_id}")
def party_report(party_id:int, db:Session=Depends(get_db), user:User=Depends(get_current_user)):
    party=db.get(Party,party_id)
    if not party: return {"detail":"الطرف غير موجود"}
    debit=db.scalar(select(func.coalesce(func.sum(JournalLine.debit),0)).join(JournalEntry,JournalLine.journal_entry_id==JournalEntry.id).where(JournalEntry.status=="posted", JournalEntry.description.contains(party.name))) or 0
    credit=db.scalar(select(func.coalesce(func.sum(JournalLine.credit),0)).join(JournalEntry,JournalLine.journal_entry_id==JournalEntry.id).where(JournalEntry.status=="posted", JournalEntry.description.contains(party.name))) or 0
    return {"party_id":party.id,"party_name":party.name,"party_type":party.party_type,"total_debit":debit,"total_credit":credit,"balance":debit-credit,"printed_by":user.full_name,"username":user.username,"branch_id":user.branch_id}
