from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db.session import get_db
from app.models.account import Account
from app.models.user import User

router = APIRouter(prefix="/accounts", tags=["الحسابات"])


class AccountCreate(BaseModel):
    code: str
    name_ar: str
    account_type: str
    parent_id: int | None = None


class AccountOut(AccountCreate):
    id: int
    is_active: bool
    model_config = ConfigDict(from_attributes=True)


@router.get("", response_model=list[AccountOut])
def list_accounts(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    stmt = select(Account).order_by(Account.code)
    if user.branch_id is not None: stmt = stmt.where((Account.branch_id == user.branch_id) | (Account.branch_id.is_(None)))
    return list(db.scalars(stmt))


@router.post("", response_model=AccountOut, status_code=201)
def create_account(payload: AccountCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if payload.account_type not in {"asset", "liability", "equity", "revenue", "expense"}: raise HTTPException(400, "نوع الحساب غير صحيح")
    if db.scalar(select(Account).where(Account.code == payload.code)): raise HTTPException(409, "رمز الحساب مستخدم مسبقًا")
    if payload.parent_id is not None:
        parent = db.get(Account, payload.parent_id)
        if not parent: raise HTTPException(400, "الحساب الأب غير موجود")
        if user.branch_id is not None and parent.branch_id not in (None, user.branch_id): raise HTTPException(403, "الحساب الأب تابع لفرع آخر")
    account = Account(**payload.model_dump(), branch_id=user.branch_id)
    db.add(account)
    db.commit()
    db.refresh(account)
    return account
