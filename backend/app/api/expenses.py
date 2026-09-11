from datetime import date
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.auth import get_current_user
from app.db.session import get_db
from app.models.expense import Expense
from app.models.user import User
from app.models.party import Party

router=APIRouter(prefix="/expenses",tags=["المصروفات"])

class ExpenseIn(BaseModel):
    expense_number:str=Field(min_length=1,max_length=40)
    expense_date:date
    category:str=Field(min_length=1,max_length=100)
    description:str=Field(min_length=1,max_length=500)
    amount:Decimal=Field(gt=0)
    supplier_id:int|None=None
    program_id:int|None=None
    payment_account_id:int|None=None

@router.get("")
def list_expenses(db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    stmt=select(Expense).order_by(Expense.expense_date.desc(),Expense.id.desc())
    if user.branch_id is not None: stmt=stmt.where((Expense.branch_id==user.branch_id)|Expense.branch_id.is_(None))
    return list(db.scalars(stmt))

@router.post("",status_code=201)
def create_expense(payload:ExpenseIn,db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    if db.scalar(select(Expense).where(Expense.expense_number==payload.expense_number)):
        raise HTTPException(409,"رقم المصروف مستخدم مسبقًا")
    if payload.supplier_id is not None:
        supplier=db.get(Party,payload.supplier_id)
        if not supplier or supplier.party_type not in {"supplier","both"}: raise HTTPException(400,"المورد غير موجود")
        if user.branch_id is not None and supplier.branch_id not in (None,user.branch_id): raise HTTPException(403,"المورد تابع لفرع آخر")
    expense=Expense(**payload.model_dump(),created_by=user.id,branch_id=user.branch_id)
    db.add(expense);db.commit();db.refresh(expense);return expense
