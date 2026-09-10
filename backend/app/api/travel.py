from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db.session import get_db
from app.models.travel import Pilgrim, TravelProgram, VisaService
from app.models.user import User

router = APIRouter(prefix="/travel", tags=["الحج والعمرة"])


class ProgramCreate(BaseModel):
    code: str
    name_ar: str
    program_type: str
    season: str | None = None
    capacity: int = 0
    sale_price: Decimal = Decimal("0")
    supplier_cost: Decimal = Decimal("0")


class PilgrimCreate(BaseModel):
    full_name: str
    passport_number: str | None = None
    nationality: str | None = None
    phone: str | None = None
    customer_id: int | None = None


class VisaCreate(BaseModel):
    pilgrim_id: int
    customer_id: int | None = None
    supplier_id: int | None = None
    visa_type: str
    sale_price: Decimal
    supplier_cost: Decimal = Decimal("0")


@router.get("/programs")
def programs(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.scalars(select(TravelProgram).order_by(TravelProgram.id.desc())).all()


@router.post("/programs", status_code=201)
def create_program(payload: ProgramCreate, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    if payload.program_type not in {"umrah", "hajj"}:
        raise HTTPException(400, "نوع البرنامج يجب أن يكون عمرة أو حج")
    if payload.sale_price < 0 or payload.supplier_cost < 0 or payload.capacity < 0:
        raise HTTPException(400, "القيم المالية والسعة لا يمكن أن تكون سالبة")
    if db.scalar(select(TravelProgram).where(TravelProgram.code == payload.code)):
        raise HTTPException(409, "رمز البرنامج مستخدم مسبقًا")
    program = TravelProgram(**payload.model_dump())
    db.add(program)
    db.commit()
    db.refresh(program)
    return program


@router.get("/pilgrims")
def pilgrims(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.scalars(select(Pilgrim).order_by(Pilgrim.id.desc())).all()


@router.post("/pilgrims", status_code=201)
def create_pilgrim(payload: PilgrimCreate, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    pilgrim = Pilgrim(**payload.model_dump())
    db.add(pilgrim)
    db.commit()
    db.refresh(pilgrim)
    return pilgrim


@router.post("/visas", status_code=201)
def create_visa(payload: VisaCreate, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    if not db.get(Pilgrim, payload.pilgrim_id):
        raise HTTPException(404, "المعتمر أو الحاج غير موجود")
    if payload.sale_price < 0 or payload.supplier_cost < 0:
        raise HTTPException(400, "قيمة البيع والتكلفة لا يمكن أن تكون سالبة")
    visa = VisaService(**payload.model_dump())
    db.add(visa)
    db.commit()
    db.refresh(visa)
    return visa
