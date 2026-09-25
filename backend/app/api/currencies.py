from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_permission
from app.db.session import get_db
from app.models.currency import Currency
from app.models.exchange_rate import ExchangeRate
from app.models.user import User
from app.models.voucher import Voucher
from app.models.settings import SystemSetting

router = APIRouter(prefix="/currencies", tags=["العملات وأسعار الصرف"])

SUGGESTED_CURRENCIES = {
    "YER": {"name_ar": "الريال اليمني", "symbol": "ر.ي"},
    "SAR": {"name_ar": "الريال السعودي", "symbol": "ر.س"},
    "USD": {"name_ar": "الدولار الأمريكي", "symbol": "$"},
}


class CurrencyIn(BaseModel):
    code: str = Field(min_length=2, max_length=10)
    name_ar: str = Field(min_length=1, max_length=100)
    symbol: str = Field(min_length=1, max_length=10)
    is_base: bool = False


class RateIn(BaseModel):
    currency_id: int
    rate_to_base: Decimal = Field(gt=0)


def _base_currency_locked(db: Session) -> bool:
    return db.scalar(select(Voucher.id).limit(1)) is not None


def _sync_base_setting(db: Session, currency: Currency) -> None:
    setting = db.scalar(select(SystemSetting).where(SystemSetting.key == "currency"))
    if setting:
        setting.value = currency.code
    name_setting = db.scalar(select(SystemSetting).where(SystemSetting.key == "currency_name_ar"))
    if name_setting:
        name_setting.value = currency.name_ar


@router.get("")
def list_currencies(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.scalars(select(Currency).order_by(Currency.is_base.desc(), Currency.code)).all()
    locked = _base_currency_locked(db)
    return [
        {
            "id": c.id,
            "code": c.code,
            "name_ar": c.name_ar,
            "symbol": c.symbol,
            "is_base": c.is_base,
            "is_active": c.is_active,
            "is_suggested": c.code in SUGGESTED_CURRENCIES,
            "base_currency_locked": locked,
        }
        for c in rows
    ]


@router.post("", status_code=201)
def create_currency(payload: CurrencyIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_permission(user, "settings.manage", db)
    code = payload.code.upper().strip()
    if db.scalar(select(Currency).where(Currency.code == code)):
        raise HTTPException(409, "رمز العملة مستخدم مسبقًا")
    if payload.is_base:
        if _base_currency_locked(db):
            raise HTTPException(409, "لا يمكن تغيير العملة الأساسية بعد إضافة أي سند مالي")
        if db.scalar(select(Currency).where(Currency.is_base.is_(True))):
            raise HTTPException(400, "توجد عملة أساسية بالفعل؛ استخدم خيار تحديد العملة الأساسية لتغييرها قبل أول سند")
    c = Currency(code=code, name_ar=payload.name_ar, symbol=payload.symbol, is_base=payload.is_base)
    db.add(c)
    if payload.is_base:
        _sync_base_setting(db, c)
    db.commit()
    db.refresh(c)
    return c


@router.post("/{currency_id}/set-base")
def set_base_currency(currency_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_permission(user, "settings.manage", db)
    currency = db.get(Currency, currency_id)
    if not currency or not currency.is_active:
        raise HTTPException(404, "العملة غير موجودة أو غير نشطة")
    if _base_currency_locked(db) and not currency.is_base:
        raise HTTPException(409, "العملة الأساسية أصبحت مقفلة لأن النظام يحتوي على سندات مالية")

    current = db.scalar(select(Currency).where(Currency.is_base.is_(True), Currency.id != currency_id))
    if current:
        current.is_base = False
    currency.is_base = True
    _sync_base_setting(db, currency)
    db.commit()
    db.refresh(currency)
    return {
        "id": currency.id,
        "code": currency.code,
        "name_ar": currency.name_ar,
        "symbol": currency.symbol,
        "is_base": currency.is_base,
        "is_active": currency.is_active,
        "base_currency_locked": _base_currency_locked(db),
    }


@router.post("/rates", status_code=201)
def create_rate(payload: RateIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_permission(user, "settings.manage", db)
    c = db.get(Currency, payload.currency_id)
    if not c:
        raise HTTPException(404, "العملة غير موجودة")
    if c.is_base:
        raise HTTPException(400, "العملة الرسمية لا تحتاج سعر صرف؛ سعرها إلى نفسها يساوي 1")
    r = ExchangeRate(currency_id=c.id, rate_to_base=payload.rate_to_base)
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


@router.get("/{currency_id}/rate")
def latest_rate(currency_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    c = db.get(Currency, currency_id)
    if not c:
        raise HTTPException(404, "العملة غير موجودة")
    r = db.scalar(select(ExchangeRate).where(ExchangeRate.currency_id == currency_id).order_by(ExchangeRate.effective_at.desc()))
    if not r and not c.is_base:
        raise HTTPException(404, "لا يوجد سعر صرف مسجل لهذه العملة")
    return {
        "currency_id": currency_id,
        "rate_to_base": Decimal("1") if c.is_base else r.rate_to_base,
        "effective_at": None if c.is_base else r.effective_at,
    }
