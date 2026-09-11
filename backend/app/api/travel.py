from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db.session import get_db
from app.models.travel import Pilgrim, ProgramBooking, TravelProgram, VisaService
from app.models.user import User

router = APIRouter(prefix="/travel", tags=["الحج والعمرة"])

class ProgramCreate(BaseModel):
    code: str = Field(min_length=1, max_length=40)
    name_ar: str = Field(min_length=1, max_length=200)
    program_type: str
    season: str | None = None
    capacity: int = Field(default=0, ge=0)
    sale_price: Decimal = Field(default=Decimal("0"), ge=0)
    supplier_cost: Decimal = Field(default=Decimal("0"), ge=0)

class PilgrimCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=200)
    passport_number: str | None = None
    nationality: str | None = None
    phone: str | None = None
    customer_id: int | None = None

class BookingCreate(BaseModel):
    program_id: int
    pilgrim_id: int
    customer_id: int | None = None
    sale_price: Decimal | None = Field(default=None, ge=0)
    supplier_cost: Decimal | None = Field(default=None, ge=0)
    customer_type: str = "direct"

class VisaCreate(BaseModel):
    pilgrim_id: int
    customer_id: int | None = None
    supplier_id: int | None = None
    visa_type: str
    sale_price: Decimal = Field(ge=0)
    supplier_cost: Decimal = Field(default=Decimal("0"), ge=0)

@router.get("/programs")
def programs(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    stmt=select(TravelProgram).order_by(TravelProgram.id.desc())
    if user.branch_id is not None: stmt=stmt.where((TravelProgram.branch_id==user.branch_id)|TravelProgram.branch_id.is_(None))
    return db.scalars(stmt).all()

@router.post("/programs", status_code=201)
def create_program(payload: ProgramCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if payload.program_type not in {"umrah", "hajj"}:
        raise HTTPException(400, "نوع البرنامج يجب أن يكون عمرة أو حج")
    if db.scalar(select(TravelProgram).where(TravelProgram.code == payload.code)):
        raise HTTPException(409, "رمز البرنامج مستخدم مسبقًا")
    program = TravelProgram(**payload.model_dump(), branch_id=user.branch_id)
    db.add(program); db.commit(); db.refresh(program)
    return program

@router.get("/pilgrims")
def pilgrims(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    stmt=select(Pilgrim).order_by(Pilgrim.id.desc())
    if user.branch_id is not None: stmt=stmt.where((Pilgrim.branch_id==user.branch_id)|Pilgrim.branch_id.is_(None))
    return db.scalars(stmt).all()

@router.post("/pilgrims", status_code=201)
def create_pilgrim(payload: PilgrimCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    pilgrim = Pilgrim(**payload.model_dump(), branch_id=user.branch_id)
    db.add(pilgrim); db.commit(); db.refresh(pilgrim)
    return pilgrim

@router.get("/bookings")
def bookings(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    stmt=select(ProgramBooking).order_by(ProgramBooking.id.desc())
    if user.branch_id is not None: stmt=stmt.where((ProgramBooking.branch_id==user.branch_id)|ProgramBooking.branch_id.is_(None))
    return db.scalars(stmt).all()

@router.post("/bookings", status_code=201)
def create_booking(payload: BookingCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    program = db.get(TravelProgram, payload.program_id)
    if not program or not program.is_active:
        raise HTTPException(404, "البرنامج غير موجود أو غير نشط")
    if not db.get(Pilgrim, payload.pilgrim_id):
        raise HTTPException(404, "المعتمر أو الحاج غير موجود")
    if payload.customer_type not in {"direct", "agency"}:
        raise HTTPException(400, "نوع العميل يجب أن يكون مباشر أو وكالة")
    booked = db.scalar(select(func.count(ProgramBooking.id)).where(ProgramBooking.program_id == program.id, ProgramBooking.status.in_(["reserved", "confirmed"]))) or 0
    if program.capacity and booked >= program.capacity:
        raise HTTPException(409, "لا توجد مقاعد متاحة في البرنامج")
    sale = payload.sale_price if payload.sale_price is not None else program.sale_price
    cost = payload.supplier_cost if payload.supplier_cost is not None else program.supplier_cost
    booking = ProgramBooking(
        program_id=program.id, pilgrim_id=payload.pilgrim_id, customer_id=payload.customer_id,
        sale_price=sale, supplier_cost=cost, paid_amount=Decimal("0"),
        remaining_amount=sale, profit=sale-cost, customer_type=payload.customer_type,
    )
    db.add(booking); db.commit(); db.refresh(booking)
    return booking

@router.get("/visas")
def visas(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    stmt=select(VisaService).order_by(VisaService.id.desc())
    if user.branch_id is not None: stmt=stmt.where((VisaService.branch_id==user.branch_id)|VisaService.branch_id.is_(None))
    return db.scalars(stmt).all()

@router.post("/visas", status_code=201)
def create_visa(payload: VisaCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not db.get(Pilgrim, payload.pilgrim_id):
        raise HTTPException(404, "المعتمر أو الحاج غير موجود")
    visa = VisaService(**payload.model_dump(), profit=payload.sale_price - payload.supplier_cost, branch_id=user.branch_id)
    db.add(visa); db.commit(); db.refresh(visa)
    return visa
