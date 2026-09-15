from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_permission
from app.db.session import get_db
from app.models.account import Account
from app.models.currency import Currency
from app.models.financial import FinancialAccount
from app.models.user import User

router = APIRouter(prefix="/financial-accounts", tags=["الصناديق والبنوك والمحافظ"])


class FinancialIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    account_type: str
    ledger_account_id: int
    currency_id: int | None = None
    opening_balance: Decimal = Decimal("0")
    branch_id: int | None = None
    is_active: bool = True


VALID_TYPES = {"cashbox", "bank", "wallet"}


def _validate(db: Session, payload: FinancialIn, user: User) -> None:
    if payload.account_type not in VALID_TYPES:
        raise HTTPException(400, "نوع الحساب المالي غير صحيح")
    ledger = db.get(Account, payload.ledger_account_id)
    if not ledger or not ledger.is_active:
        raise HTTPException(400, "الحساب المحاسبي غير موجود أو غير نشط")
    if ledger.account_type != "asset":
        raise HTTPException(400, "الحساب المالي يجب أن يرتبط بحساب أصول")
    if user.branch_id is not None and ledger.branch_id not in (None, user.branch_id):
        raise HTTPException(403, "الحساب المحاسبي تابع لفرع آخر")
    if payload.branch_id is not None and not db.get(__import__("app.models.branch", fromlist=["Branch"]).Branch, payload.branch_id):
        raise HTTPException(400, "الفرع غير موجود")
    if user.branch_id is not None and payload.branch_id not in (None, user.branch_id):
        raise HTTPException(403, "لا يمكنك إنشاء حساب مالي لفرع آخر")
    if payload.currency_id is not None:
        c = db.get(Currency, payload.currency_id)
        if not c or not c.is_active:
            raise HTTPException(400, "العملة غير موجودة أو غير نشطة")
    if payload.opening_balance < 0:
        raise HTTPException(400, "الرصيد الافتتاحي لا يمكن أن يكون سالبًا")


@router.get("")
def list_financial(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    stmt = select(FinancialAccount).order_by(FinancialAccount.account_type, FinancialAccount.name)
    if user.branch_id is not None:
        stmt = stmt.where((FinancialAccount.branch_id == user.branch_id) | (FinancialAccount.branch_id.is_(None)))
    return list(db.scalars(stmt))


@router.post("", status_code=201)
def create_financial(payload: FinancialIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_permission(user, "accounts.create", db)
    _validate(db, payload, user)
    f = FinancialAccount(**payload.model_dump(), branch_id=payload.branch_id if user.branch_id is None else user.branch_id)
    db.add(f)
    db.commit()
    db.refresh(f)
    return f


@router.put("/{financial_id}")
def update_financial(financial_id: int, payload: FinancialIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_permission(user, "accounts.create", db)
    row = db.get(FinancialAccount, financial_id)
    if not row:
        raise HTTPException(404, "الحساب المالي غير موجود")
    if user.branch_id is not None and row.branch_id not in (None, user.branch_id):
        raise HTTPException(403, "الحساب المالي تابع لفرع آخر")
    _validate(db, payload, user)
    row.name = payload.name
    row.account_type = payload.account_type
    row.ledger_account_id = payload.ledger_account_id
    row.currency_id = payload.currency_id
    row.opening_balance = payload.opening_balance
    row.is_active = payload.is_active
    if user.branch_id is None:
        row.branch_id = payload.branch_id
    db.commit()
    db.refresh(row)
    return row
