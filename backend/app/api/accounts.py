from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_permission
from app.db.session import get_db
from app.models.account import Account
from app.models.audit_log import AuditLog
from app.models.journal import JournalEntry, JournalLine
from app.models.user import User

router = APIRouter(prefix="/accounts", tags=["الحسابات"])

ACCOUNT_TYPES = {"asset", "liability", "equity", "revenue", "expense", "cost_of_service"}


class AccountCreate(BaseModel):
    code: str
    name_ar: str
    account_type: str
    parent_id: int | None = None
    opening_balance: Decimal = Decimal("0")


class AccountUpdate(BaseModel):
    name_ar: str
    account_type: str
    parent_id: int | None = None


class AccountOut(AccountCreate):
    id: int
    is_active: bool
    model_config = ConfigDict(from_attributes=True)


def _visible_account(db: Session, account_id: int, user: User) -> Account:
    account = db.get(Account, account_id)
    if not account:
        raise HTTPException(404, "الحساب غير موجود")
    if user.branch_id is not None and account.branch_id not in (None, user.branch_id):
        raise HTTPException(403, "الحساب تابع لفرع آخر")
    return account


def _validate_parent(db: Session, parent_id: int | None, account_id: int | None, user: User):
    if parent_id is None:
        return None
    if account_id is not None and parent_id == account_id:
        raise HTTPException(400, "لا يمكن أن يكون الحساب أبًا لنفسه")
    parent = _visible_account(db, parent_id, user)
    if not parent.is_active:
        raise HTTPException(400, "الحساب الأب غير نشط")
    return parent


@router.get("", response_model=list[AccountOut])
def list_accounts(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_permission(user, "accounts.view", db)
    stmt = select(Account).order_by(Account.code)
    if user.branch_id is not None:
        stmt = stmt.where((Account.branch_id == user.branch_id) | Account.branch_id.is_(None))
    return list(db.scalars(stmt))


@router.post("", response_model=AccountOut, status_code=201)
def create_account(payload: AccountCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_permission(user, "accounts.create", db)
    if not payload.code.strip() or not payload.name_ar.strip():
        raise HTTPException(400, "رمز واسم الحساب مطلوبان")
    if payload.account_type not in ACCOUNT_TYPES:
        raise HTTPException(400, "نوع الحساب غير صحيح")
    if payload.opening_balance < 0:
        raise HTTPException(400, "الرصيد الافتتاحي لا يمكن أن يكون سالبًا")
    if db.scalar(select(Account).where(Account.code == payload.code.strip())):
        raise HTTPException(409, "رمز الحساب مستخدم مسبقًا")
    _validate_parent(db, payload.parent_id, None, user)
    account = Account(
        code=payload.code.strip(),
        name_ar=payload.name_ar.strip(),
        account_type=payload.account_type,
        parent_id=payload.parent_id,
        branch_id=user.branch_id,
        opening_balance=payload.opening_balance,
    )
    db.add(account)
    db.flush()
    db.add(AuditLog(
        user_id=user.id, action="create", entity_type="account", entity_id=account.id,
        details=f'{{"code":"{account.code}","name_ar":"{account.name_ar}"}}',
    ))
    db.commit()
    db.refresh(account)
    return account


@router.put("/{account_id}", response_model=AccountOut)
def update_account(account_id: int, payload: AccountUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_permission(user, "accounts.update", db)
    account = _visible_account(db, account_id, user)
    if not payload.name_ar.strip():
        raise HTTPException(400, "اسم الحساب مطلوب")
    if payload.account_type not in ACCOUNT_TYPES:
        raise HTTPException(400, "نوع الحساب غير صحيح")
    _validate_parent(db, payload.parent_id, account.id, user)

    has_posted = db.scalar(
        select(JournalLine.id)
        .join(JournalEntry, JournalLine.journal_entry_id == JournalEntry.id)
        .where(JournalLine.account_id == account.id, JournalEntry.status == "posted")
        .limit(1)
    ) is not None
    if has_posted and payload.account_type != account.account_type:
        raise HTTPException(409, "لا يمكن تغيير نوع حساب لديه قيود مرحّلة")

    account.name_ar = payload.name_ar.strip()
    account.parent_id = payload.parent_id
    account.account_type = payload.account_type
    db.add(AuditLog(user_id=user.id, action="update", entity_type="account", entity_id=account.id))
    db.commit()
    db.refresh(account)
    return account


@router.post("/{account_id}/disable", response_model=AccountOut)
def disable_account(account_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_permission(user, "accounts.disable", db)
    account = _visible_account(db, account_id, user)
    if not account.is_active:
        return account

    child = db.scalar(select(Account.id).where(Account.parent_id == account.id, Account.is_active.is_(True)).limit(1))
    if child is not None:
        raise HTTPException(409, "لا يمكن تعطيل الحساب قبل تعطيل الحسابات الفرعية النشطة")

    account.is_active = False
    db.add(AuditLog(user_id=user.id, action="disable", entity_type="account", entity_id=account.id))
    db.commit()
    db.refresh(account)
    return account
