from datetime import date, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.accounting.journal_service import create_journal
from app.auth import get_current_user, require_permission
from app.db.session import get_db
from app.models.account import Account
from app.models.audit_log import AuditLog
from app.models.journal import JournalEntry
from app.models.party import Party
from app.models.settings import SystemSetting
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
    supplier_id: int | None = None


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


def _branch_allowed(user: User, branch_id: int | None) -> bool:
    return user.branch_id is None or branch_id in (None, user.branch_id)


def _get_setting(db: Session, key: str) -> str | None:
    value = db.scalar(select(SystemSetting.value).where(SystemSetting.key == key))
    return value.strip() if value else None


def _resolve_account(db: Session, user: User, key: str, account_type: str, label: str) -> Account:
    configured = _get_setting(db, key)
    if configured:
        try:
            account_id = int(configured)
        except ValueError:
            raise HTTPException(400, f"إعداد {label} يجب أن يحتوي على رقم حساب صحيح")
        account = db.get(Account, account_id)
        if not account or not account.is_active:
            raise HTTPException(400, f"{label} المحدد في الإعدادات غير موجود أو غير نشط")
        allowed_types = {"expense", "cost_of_service"} if account_type == "cost_of_service" else {account_type}
        if account.account_type not in allowed_types:
            raise HTTPException(400, f"حساب {label} يجب أن يكون من نوع {account_type}")
        if not _branch_allowed(user, account.branch_id):
            raise HTTPException(403, f"{label} تابع لفرع آخر")
        return account

    account_types = ["expense", "cost_of_service"] if account_type == "cost_of_service" else [account_type]
    stmt = select(Account).where(Account.account_type.in_(account_types), Account.is_active.is_(True))
    if user.branch_id is not None:
        stmt = stmt.where((Account.branch_id == user.branch_id) | Account.branch_id.is_(None))
    candidates = list(db.scalars(stmt.order_by(Account.code)))
    if len(candidates) == 1:
        return candidates[0]
    raise HTTPException(400, f"يجب ضبط إعداد {label} أو ترك حساب واحد فقط من نوع {account_type}")


def _party_account(db: Session, user: User, party_id: int | None, expected: set[str], label: str) -> Account:
    if party_id is None:
        raise HTTPException(400, f"يجب تحديد {label}")
    party = db.get(Party, party_id)
    if not party or party.party_type not in expected:
        raise HTTPException(400, f"{label} غير موجود أو نوعه غير صحيح")
    if not _branch_allowed(user, party.branch_id):
        raise HTTPException(403, f"{label} تابع لفرع آخر")
    if party.account_id is None:
        raise HTTPException(400, f"{label} غير مربوط بحساب محاسبي")
    account = db.get(Account, party.account_id)
    if not account or not account.is_active:
        raise HTTPException(400, f"حساب {label} غير موجود أو غير نشط")
    if not _branch_allowed(user, account.branch_id):
        raise HTTPException(403, f"حساب {label} تابع لفرع آخر")
    return account


def _post_service_journal(
    db: Session,
    *,
    entry_number: str,
    entry_date: date,
    description: str,
    branch_id: int | None,
    created_by: int,
    customer_account: Account,
    revenue_account: Account,
    sale_amount: Decimal,
    supplier_account: Account | None = None,
    cost_account: Account | None = None,
    cost_amount: Decimal = Decimal("0"),
) -> JournalEntry:
    if sale_amount <= 0:
        raise HTTPException(400, "سعر البيع يجب أن يكون أكبر من صفر عند الترحيل")
    if cost_amount > 0 and (supplier_account is None or cost_account is None):
        raise HTTPException(400, "يجب تحديد المورد وحساب التكلفة عند وجود تكلفة")

    lines = [
        {"account_id": customer_account.id, "debit": sale_amount, "credit": Decimal("0"), "description": description},
        {"account_id": revenue_account.id, "debit": Decimal("0"), "credit": sale_amount, "description": description},
    ]
    if cost_amount > 0:
        lines.extend([
            {"account_id": cost_account.id, "debit": cost_amount, "credit": Decimal("0"), "description": f"تكلفة: {description}"},
            {"account_id": supplier_account.id, "debit": Decimal("0"), "credit": cost_amount, "description": f"مستحق للمورد: {description}"},
        ])

    try:
        entry = create_journal(
            db,
            entry_number=entry_number,
            entry_date=entry_date,
            description=description,
            lines=lines,
            created_by=created_by,
            branch_id=branch_id,
            status="posted",
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    entry.posted_at = datetime.utcnow()
    return entry


@router.get("/programs")
def programs(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_permission(user, "travel.view", db)
    stmt = select(TravelProgram).order_by(TravelProgram.id.desc())
    if user.branch_id is not None:
        stmt = stmt.where((TravelProgram.branch_id == user.branch_id) | TravelProgram.branch_id.is_(None))
    return db.scalars(stmt).all()


@router.post("/programs", status_code=201)
def create_program(payload: ProgramCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_permission(user, "travel.create", db)
    if payload.program_type not in {"umrah", "hajj"}:
        raise HTTPException(400, "نوع البرنامج يجب أن يكون عمرة أو حج")
    if db.scalar(select(TravelProgram).where(TravelProgram.code == payload.code)):
        raise HTTPException(409, "رمز البرنامج مستخدم مسبقًا")
    if payload.supplier_id is not None:
        _party_account(db, user, payload.supplier_id, {"supplier", "both"}, "المورد")
    program = TravelProgram(**payload.model_dump(), branch_id=user.branch_id)
    db.add(program)
    db.flush()
    db.add(AuditLog(user_id=user.id, action="create", entity_type="travel_program", entity_id=program.id, details=f"إنشاء برنامج {program.name_ar}"))
    db.commit()
    db.refresh(program)
    return program


@router.get("/pilgrims")
def pilgrims(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_permission(user, "travel.view", db)
    stmt = select(Pilgrim).order_by(Pilgrim.id.desc())
    if user.branch_id is not None:
        stmt = stmt.where((Pilgrim.branch_id == user.branch_id) | Pilgrim.branch_id.is_(None))
    return db.scalars(stmt).all()


@router.post("/pilgrims", status_code=201)
def create_pilgrim(payload: PilgrimCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_permission(user, "travel.create", db)
    if payload.customer_id is not None:
        _party_account(db, user, payload.customer_id, {"customer", "both"}, "العميل")
    pilgrim = Pilgrim(**payload.model_dump(), branch_id=user.branch_id)
    db.add(pilgrim)
    db.flush()
    db.add(AuditLog(user_id=user.id, action="create", entity_type="pilgrim", entity_id=pilgrim.id, details=f"إنشاء مستفيد {pilgrim.full_name}"))
    db.commit()
    db.refresh(pilgrim)
    return pilgrim


@router.get("/bookings")
def bookings(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_permission(user, "travel.view", db)
    stmt = select(ProgramBooking).order_by(ProgramBooking.id.desc())
    if user.branch_id is not None:
        stmt = stmt.where((ProgramBooking.branch_id == user.branch_id) | ProgramBooking.branch_id.is_(None))
    return db.scalars(stmt).all()


@router.post("/bookings", status_code=201)
def create_booking(payload: BookingCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_permission(user, "travel.create", db)
    program = db.get(TravelProgram, payload.program_id)
    if not program or not program.is_active or not _branch_allowed(user, program.branch_id):
        raise HTTPException(404, "البرنامج غير موجود أو غير نشط")
    pilgrim = db.get(Pilgrim, payload.pilgrim_id)
    if not pilgrim or not _branch_allowed(user, pilgrim.branch_id):
        raise HTTPException(404, "المعتمر أو الحاج غير موجود")
    if payload.customer_id is not None:
        _party_account(db, user, payload.customer_id, {"customer", "both"}, "العميل")
    if payload.customer_type not in {"direct", "agency"}:
        raise HTTPException(400, "نوع العميل يجب أن يكون مباشر أو وكالة")
    booked = db.scalar(
        select(func.count(ProgramBooking.id)).where(
            ProgramBooking.program_id == program.id,
            ProgramBooking.status.in_(["reserved", "confirmed"]),
        )
    ) or 0
    if program.capacity and booked >= program.capacity:
        raise HTTPException(409, "لا توجد مقاعد متاحة في البرنامج")
    sale = payload.sale_price if payload.sale_price is not None else program.sale_price
    cost = payload.supplier_cost if payload.supplier_cost is not None else program.supplier_cost
    booking = ProgramBooking(
        program_id=program.id,
        pilgrim_id=payload.pilgrim_id,
        customer_id=payload.customer_id,
        sale_price=sale,
        supplier_cost=cost,
        paid_amount=Decimal("0"),
        remaining_amount=sale,
        profit=sale - cost,
        customer_type=payload.customer_type,
        branch_id=user.branch_id,
        status="reserved",
    )
    db.add(booking)
    db.flush()
    db.add(AuditLog(user_id=user.id, action="create", entity_type="program_booking", entity_id=booking.id, details=f"إنشاء حجز برنامج #{booking.id}"))
    db.commit()
    db.refresh(booking)
    return booking


@router.post("/bookings/{booking_id}/post")
def post_booking(booking_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_permission(user, "travel.post", db)
    booking = db.get(ProgramBooking, booking_id)
    if not booking:
        raise HTTPException(404, "الحجز غير موجود")
    if not _branch_allowed(user, booking.branch_id):
        raise HTTPException(403, "الحجز تابع لفرع آخر")
    if booking.status not in {"reserved", "confirmed"}:
        raise HTTPException(400, "لا يمكن ترحيل حجز غير نشط")
    if booking.journal_entry_id:
        raise HTTPException(409, "الحجز مرتبط بقيد محاسبي مسبقًا")
    if booking.customer_id is None:
        raise HTTPException(400, "يجب ربط الحجز بعميل قبل الترحيل")

    program = db.get(TravelProgram, booking.program_id)
    customer_account = _party_account(db, user, booking.customer_id, {"customer", "both"}, "العميل")
    revenue_account = _resolve_account(db, user, "travel_revenue_account_id", "revenue", "إيراد برامج الحج والعمرة")
    cost_account = None
    supplier_account = None
    if booking.supplier_cost > 0:
        if not program or program.supplier_id is None:
            raise HTTPException(400, "يجب تحديد مورد البرنامج قبل ترحيل تكلفة الحجز")
        supplier_account = _party_account(db, user, program.supplier_id, {"supplier", "both"}, "المورد")
        cost_account = _resolve_account(db, user, "travel_cost_account_id", "cost_of_service", "تكلفة برامج الحج والعمرة")

    entry = _post_service_journal(
        db,
        entry_number=f"TRAVEL-BOOK-{booking.id}",
        entry_date=booking.booked_at.date(),
        description=f"بيع برنامج الحج والعمرة - حجز #{booking.id}",
        branch_id=booking.branch_id,
        created_by=user.id,
        customer_account=customer_account,
        revenue_account=revenue_account,
        sale_amount=booking.sale_price,
        supplier_account=supplier_account,
        cost_account=cost_account,
        cost_amount=booking.supplier_cost,
    )
    booking.journal_entry_id = entry.id
    booking.status = "confirmed"
    db.add(AuditLog(user_id=user.id, action="post", entity_type="program_booking", entity_id=booking.id, details=f"ترحيل حجز برنامج #{booking.id}"))
    db.commit()
    db.refresh(booking)
    return booking


@router.post("/bookings/{booking_id}/cancel")
def cancel_booking(booking_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_permission(user, "travel.cancel", db)
    booking = db.get(ProgramBooking, booking_id)
    if not booking:
        raise HTTPException(404, "الحجز غير موجود")
    if not _branch_allowed(user, booking.branch_id):
        raise HTTPException(403, "الحجز تابع لفرع آخر")
    if booking.status == "cancelled":
        raise HTTPException(400, "الحجز ملغى مسبقًا")
    if not booking.journal_entry_id:
        booking.status = "cancelled"
        db.commit()
        db.refresh(booking)
        return booking
    original = db.get(JournalEntry, booking.journal_entry_id)
    if not original:
        raise HTTPException(409, "القيد المرتبط بالحجز غير موجود")
    try:
        reversal = create_journal(
            db,
            entry_number=f"REV-TRAVEL-BOOK-{booking.id}",
            entry_date=date.today(),
            description=f"عكس حجز برنامج #{booking.id}",
            lines=[{"account_id": line.account_id, "debit": line.credit, "credit": line.debit} for line in original.lines],
            created_by=user.id,
            branch_id=booking.branch_id,
            status="posted",
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(400, str(exc))
    reversal.posted_at = datetime.utcnow()
    booking.status = "cancelled"
    db.add(AuditLog(user_id=user.id, action="cancel", entity_type="program_booking", entity_id=booking.id, details=f"إلغاء حجز برنامج #{booking.id}"))
    db.commit()
    db.refresh(booking)
    return booking


@router.get("/visas")
def visas(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_permission(user, "travel.view", db)
    stmt = select(VisaService).order_by(VisaService.id.desc())
    if user.branch_id is not None:
        stmt = stmt.where((VisaService.branch_id == user.branch_id) | VisaService.branch_id.is_(None))
    return db.scalars(stmt).all()


@router.post("/visas", status_code=201)
def create_visa(payload: VisaCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_permission(user, "travel.create", db)
    _party_account(db, user, payload.customer_id, {"customer", "both"}, "العميل") if payload.customer_id is not None else None
    if payload.supplier_id is not None:
        _party_account(db, user, payload.supplier_id, {"supplier", "both"}, "المورد")
    pilgrim = db.get(Pilgrim, payload.pilgrim_id)
    if not pilgrim or not _branch_allowed(user, pilgrim.branch_id):
        raise HTTPException(404, "المعتمر أو الحاج غير موجود")
    visa = VisaService(
        **payload.model_dump(),
        profit=payload.sale_price - payload.supplier_cost,
        branch_id=user.branch_id,
        status="pending",
    )
    db.add(visa)
    db.flush()
    db.add(AuditLog(user_id=user.id, action="create", entity_type="visa_service", entity_id=visa.id, details=f"إنشاء خدمة تأشيرة #{visa.id}"))
    db.commit()
    db.refresh(visa)
    return visa


@router.post("/visas/{visa_id}/post")
def post_visa(visa_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_permission(user, "travel.post", db)
    visa = db.get(VisaService, visa_id)
    if not visa:
        raise HTTPException(404, "خدمة التأشيرة غير موجودة")
    if not _branch_allowed(user, visa.branch_id):
        raise HTTPException(403, "خدمة التأشيرة تابعة لفرع آخر")
    if visa.status not in {"pending", "approved"}:
        raise HTTPException(400, "لا يمكن ترحيل خدمة في حالتها الحالية")
    if visa.journal_entry_id:
        raise HTTPException(409, "خدمة التأشيرة مرتبطة بقيد محاسبي مسبقًا")
    customer_account = _party_account(db, user, visa.customer_id, {"customer", "both"}, "العميل")
    revenue_account = _resolve_account(db, user, "visa_revenue_account_id", "revenue", "إيراد خدمات التأشيرات")
    supplier_account = None
    cost_account = None
    if visa.supplier_cost > 0:
        supplier_account = _party_account(db, user, visa.supplier_id, {"supplier", "both"}, "المورد")
        cost_account = _resolve_account(db, user, "visa_cost_account_id", "cost_of_service", "تكلفة خدمات التأشيرات")

    entry = _post_service_journal(
        db,
        entry_number=f"TRAVEL-VISA-{visa.id}",
        entry_date=visa.created_at.date(),
        description=f"بيع خدمة تأشيرة #{visa.id} - {visa.visa_type}",
        branch_id=visa.branch_id,
        created_by=user.id,
        customer_account=customer_account,
        revenue_account=revenue_account,
        sale_amount=visa.sale_price,
        supplier_account=supplier_account,
        cost_account=cost_account,
        cost_amount=visa.supplier_cost,
    )
    visa.journal_entry_id = entry.id
    visa.status = "approved"
    db.add(AuditLog(user_id=user.id, action="post", entity_type="visa_service", entity_id=visa.id, details=f"ترحيل خدمة تأشيرة #{visa.id}"))
    db.commit()
    db.refresh(visa)
    return visa


@router.post("/visas/{visa_id}/cancel")
def cancel_visa(visa_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_permission(user, "travel.cancel", db)
    visa = db.get(VisaService, visa_id)
    if not visa:
        raise HTTPException(404, "خدمة التأشيرة غير موجودة")
    if not _branch_allowed(user, visa.branch_id):
        raise HTTPException(403, "خدمة التأشيرة تابعة لفرع آخر")
    if visa.status == "cancelled":
        raise HTTPException(400, "خدمة التأشيرة ملغاة مسبقًا")
    if not visa.journal_entry_id:
        visa.status = "cancelled"
        db.commit()
        db.refresh(visa)
        return visa
    original = db.get(JournalEntry, visa.journal_entry_id)
    if not original:
        raise HTTPException(409, "القيد المرتبط بخدمة التأشيرة غير موجود")
    try:
        reversal = create_journal(
            db,
            entry_number=f"REV-TRAVEL-VISA-{visa.id}",
            entry_date=date.today(),
            description=f"عكس خدمة التأشيرة #{visa.id}",
            lines=[{"account_id": line.account_id, "debit": line.credit, "credit": line.debit} for line in original.lines],
            created_by=user.id,
            branch_id=visa.branch_id,
            status="posted",
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(400, str(exc))
    reversal.posted_at = datetime.utcnow()
    visa.status = "cancelled"
    db.add(AuditLog(user_id=user.id, action="cancel", entity_type="visa_service", entity_id=visa.id, details=f"إلغاء خدمة تأشيرة #{visa.id}"))
    db.commit()
    db.refresh(visa)
    return visa
