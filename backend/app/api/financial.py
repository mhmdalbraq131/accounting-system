from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.auth import get_current_user
from app.db.session import get_db
from app.models.financial import FinancialAccount
from app.models.currency import Currency
from app.models.user import User

router=APIRouter(prefix="/financial-accounts",tags=["الصناديق والبنوك والمحافظ"])
class FinancialIn(BaseModel):
    name:str=Field(min_length=1,max_length=200)
    account_type:str
    ledger_account_id:int
    currency_id:int|None=None
    opening_balance:Decimal=Decimal("0")

@router.get("")
def list_financial(db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    stmt=select(FinancialAccount).order_by(FinancialAccount.account_type,FinancialAccount.name)
    if user.branch_id is not None: stmt=stmt.where((FinancialAccount.branch_id==user.branch_id)|FinancialAccount.branch_id.is_(None))
    return list(db.scalars(stmt))

@router.post("",status_code=201)
def create_financial(payload:FinancialIn,db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    if payload.account_type not in {"cashbox","bank","wallet"}: raise HTTPException(400,"نوع الحساب المالي غير صحيح")
    if payload.currency_id is not None:
        c=db.get(Currency,payload.currency_id)
        if not c or not c.is_active: raise HTTPException(400,"العملة غير موجودة أو غير نشطة")
    if payload.opening_balance<0: raise HTTPException(400,"الرصيد الافتتاحي لا يمكن أن يكون سالبًا")
    f=FinancialAccount(**payload.model_dump(),branch_id=user.branch_id)
    db.add(f);db.commit();db.refresh(f);return f
