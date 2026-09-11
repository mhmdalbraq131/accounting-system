from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db.session import get_db
from app.models.party import Party
from app.models.account import Account
from app.models.journal import JournalEntry, JournalLine
from app.models.user import User

router = APIRouter(prefix="/parties", tags=["العملاء والموردون"])


class PartyCreate(BaseModel):
    account_id: int | None = None
    name: str = Field(min_length=1, max_length=200)
    party_type: str
    phone: str | None = Field(default=None, max_length=50)
    address: str | None = Field(default=None, max_length=300)
    code: str | None = Field(default=None, max_length=40)
    email: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=500)


class PartyOut(PartyCreate):
    id: int
    is_active: bool
    model_config = ConfigDict(from_attributes=True)


@router.get("", response_model=list[PartyOut])
def list_parties(
    party_type: str | None = None,
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = select(Party).order_by(Party.id.desc())
    if user.branch_id is not None:
        query = query.where((Party.branch_id == user.branch_id) | Party.branch_id.is_(None))
    if party_type:
        if party_type not in {"customer", "supplier", "both"}:
            raise HTTPException(400, "نوع الطرف يجب أن يكون customer أو supplier أو both")
        query = query.where(Party.party_type == party_type)
    if not include_inactive:
        query = query.where(Party.is_active.is_(True))
    return db.scalars(query).all()


@router.post("", response_model=PartyOut, status_code=201)
def create_party(
    payload: PartyCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if payload.party_type not in {"customer", "supplier", "both"}:
        raise HTTPException(400, "نوع الطرف يجب أن يكون customer أو supplier أو both")
    data = payload.model_dump()
    account_id = data.pop("account_id", None)
    if account_id is not None:
        account = db.get(Account, account_id)
        if not account or not account.is_active:
            raise HTTPException(400, "الحساب المالي غير موجود أو غير نشط")
    party = Party(**data, branch_id=user.branch_id)
    db.add(party)
    db.commit()
    db.refresh(party)
    return party


@router.patch("/{party_id}", response_model=PartyOut)
def update_party(
    party_id: int,
    payload: PartyCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    party = db.get(Party, party_id)
    if not party:
        raise HTTPException(404, "الطرف غير موجود")
    if user.branch_id is not None and party.branch_id not in (None, user.branch_id): raise HTTPException(403, "الطرف تابع لفرع آخر")
    if payload.party_type not in {"customer", "supplier", "both"}:
        raise HTTPException(400, "نوع الطرف يجب أن يكون customer أو supplier أو both")
    for key, value in payload.model_dump().items():
        setattr(party, key, value)
    db.commit()
    db.refresh(party)
    return party


@router.post("/{party_id}/disable", response_model=PartyOut)
def disable_party(
    party_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    party = db.get(Party, party_id)
    if not party:
        raise HTTPException(404, "الطرف غير موجود")
    party.is_active = False
    db.commit()
    db.refresh(party)
    return party


@router.get("/{party_id}/statement")
def party_statement(party_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    party = db.get(Party, party_id)
    if not party:
        raise HTTPException(404, "الطرف غير موجود")
    if user.branch_id is not None and party.branch_id not in (None, user.branch_id): raise HTTPException(403, "الطرف تابع لفرع آخر")
    if party.account_id is None:
        return {"party_id": party.id, "party_name": party.name, "party_type": party.party_type, "total_debit": 0, "total_credit": 0, "balance": 0, "warning": "لم يتم ربط الطرف بحساب محاسبي"}
    debit = db.scalar(select(func.coalesce(func.sum(JournalLine.debit), 0)).join(JournalEntry, JournalLine.journal_entry_id == JournalEntry.id).where(JournalEntry.status == "posted", JournalLine.account_id == party.account_id)) or 0
    credit = db.scalar(select(func.coalesce(func.sum(JournalLine.credit), 0)).join(JournalEntry, JournalLine.journal_entry_id == JournalEntry.id).where(JournalEntry.status == "posted", JournalLine.account_id == party.account_id)) or 0
    return {"party_id": party.id, "party_name": party.name, "party_type": party.party_type, "total_debit": debit, "total_credit": credit, "balance": debit - credit}
