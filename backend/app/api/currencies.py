from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.auth import get_current_user
from app.db.session import get_db
from app.models.currency import Currency
from app.models.exchange_rate import ExchangeRate
from app.models.user import User

router=APIRouter(prefix="/currencies",tags=["العملات وأسعار الصرف"])
class CurrencyIn(BaseModel):
    code:str=Field(min_length=2,max_length=10)
    name_ar:str=Field(min_length=1,max_length=100)
    symbol:str=Field(min_length=1,max_length=10)
    is_base:bool=False
class RateIn(BaseModel):
    currency_id:int
    rate_to_base:Decimal=Field(gt=0)

@router.get("")
def list_currencies(db:Session=Depends(get_db), user:User=Depends(get_current_user)):
    return db.scalars(select(Currency).order_by(Currency.is_base.desc(),Currency.code)).all()

@router.post("",status_code=201)
def create_currency(payload:CurrencyIn,db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    if db.scalar(select(Currency).where(Currency.code==payload.code.upper())): raise HTTPException(409,"رمز العملة مستخدم مسبقًا")
    if payload.is_base and db.scalar(select(Currency).where(Currency.is_base.is_(True))): raise HTTPException(400,"يوجد عملة أساسية بالفعل")
    c=Currency(code=payload.code.upper(),name_ar=payload.name_ar,symbol=payload.symbol,is_base=payload.is_base)
    db.add(c);db.commit();db.refresh(c);return c

@router.post("/rates",status_code=201)
def create_rate(payload:RateIn,db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    c=db.get(Currency,payload.currency_id)
    if not c: raise HTTPException(404,"العملة غير موجودة")
    r=ExchangeRate(currency_id=c.id,rate_to_base=payload.rate_to_base)
    db.add(r);db.commit();db.refresh(r);return r

@router.get("/{currency_id}/rate")
def latest_rate(currency_id:int,db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    c=db.get(Currency,currency_id)
    if not c: raise HTTPException(404,"العملة غير موجودة")
    r=db.scalar(select(ExchangeRate).where(ExchangeRate.currency_id==currency_id).order_by(ExchangeRate.effective_at.desc()))
    if not r and not c.is_base: raise HTTPException(404,"لا يوجد سعر صرف مسجل لهذه العملة")
    return {"currency_id":currency_id,"rate_to_base":Decimal("1") if c.is_base else r.rate_to_base,"effective_at":None if c.is_base else r.effective_at}
