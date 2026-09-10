from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db.session import get_db
from app.models.party import Party
from app.models.user import User

router = APIRouter(prefix="/parties", tags=["العملاء والموردون"])


class PartyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    party_type: str
    phone: str | None = Field(default=None, max_length=50)
    address: str | None = Field(default=None, max_length=300)


class PartyOut(PartyCreate):
    id: int
    is_active: bool
    model_config = ConfigDict(from_attributes=True)


@router.get("", response_model=list[PartyOut])
def list_parties(
    party_type: str | None = None,
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = select(Party).order_by(Party.id.desc())
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
    _: User = Depends(get_current_user),
):
    if payload.party_type not in {"customer", "supplier", "both"}:
        raise HTTPException(400, "نوع الطرف يجب أن يكون customer أو supplier أو both")
    party = Party(**payload.model_dump())
    db.add(party)
    db.commit()
    db.refresh(party)
    return party


@router.patch("/{party_id}", response_model=PartyOut)
def update_party(
    party_id: int,
    payload: PartyCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    party = db.get(Party, party_id)
    if not party:
        raise HTTPException(404, "الطرف غير موجود")
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
