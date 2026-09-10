from fastapi import APIRouter, Depends
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
def list_accounts(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return list(db.scalars(select(Account).order_by(Account.code)))


@router.post("", response_model=AccountOut, status_code=201)
def create_account(payload: AccountCreate, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    account = Account(**payload.model_dump())
    db.add(account)
    db.commit()
    db.refresh(account)
    return account
