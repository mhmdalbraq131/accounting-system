from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.accounting.journal_service import create_journal
from app.auth import get_current_user
from app.db.session import get_db
from app.models.account import Account
from app.models.hajj import HajjQuota
from app.models.party import Party
from app.models.travel import Pilgrim, ProgramBooking, TravelProgram
from app.models.user import User
from app.models.settings import SystemSetting

router = APIRouter(prefix="/hajj", tags=["الحج"])
umrah_router = APIRouter(prefix="/umrah", tags=["العمرة"])


class QuotaCreate(BaseModel):
    name_ar: str = Field(min_length=1, max_length=200)
    season: str = Field(min_length=1, max_length=100)
    supplier_id: int
    total_units: int = Field(gt=0)
    unit_cost: Decimal = Field(ge=0)


class HajjBookingCreate(BaseModel):
    program_id: int
    pilgrim_id: int
    agent_id: int | None = None
    customer_id: int | None = None
    quota_id: int
    sale_price: Decimal = Field(gt=0)
    supplier_cost: Decimal | None = Field(default=None, ge=0)


class UmrahBookingCreate(BaseModel):
    program_id: int
    pilgrim_id: int
    agent_id: int | None = None
    customer_id: int | None = None
    supplier_id: int
    sale_price: Decimal = Field(gt=0)
    supplier_cost: Decimal = Field(default=Decimal("0"), ge=0)


def _scope(user: User, branch_id: int | None) -> None:
    if user.branch_id is not None and branch_id not in (None, user.branch_id):
        raise HTTPException(403, "السجل تابع لفرع آخر")


def _party(db: Session, user: User, party_id: int | None, allowed: set[str], label: str, required_account_type: str | None = None) -> Party:
    if party_id is None:
        raise HTTPException(400, f"يجب تحديد {label}")
    party = db.get(Party, party_id)
    if not party or party.party_type not in allowed or not party.is_active:
        raise HTTPException(400, f"{label} غير موجود أو نوعه غير صحيح")
    _scope(user, party.branch_id)
    if party.account_id is None:
        raise HTTPException(400, f"{label} غير مربوط بحساب محاسبي")
    account = db.get(Account, party.account_id)
    if not account or not account.is_active:
        raise HTTPException(400, f"حساب {label} غير موجود أو غير نشط")
    if required_account_type and account.account_type != required_account_type:
        raise HTTPException(400, f"حساب {label} يجب أن يكون من نوع {required_account_type}")
    _scope(user, account.branch_id)
    return party


def _setting_account(db: Session, user: User, key: str, expected_type: str, label: str) -> Account:
    raw = db.scalar(select(SystemSetting.value).where(SystemSetting.key == key))
    account = None
    if raw:
        try:
            account = db.get(Account, int(raw))
        except ValueError:
            raise HTTPException(400, f"إعداد {label} غير صحيح")
    if account is None:
        stmt = select(Account).where(Account.account_type == expected_type, Account.is_active.is_(True))
        if user.branch_id is not None:
            stmt = stmt.where((Account.branch_id == user.branch_id) | Account.branch_id.is_(None))
        candidates = list(db.scalars(stmt.order_by(Account.code)))
        if len(candidates) != 1:
            raise HTTPException(400, f"اضبط حساب {label} في الإعدادات أو اترك حسابًا واحدًا من نوع {expected_type}")
        account = candidates[0]
    if not account.is_active or account.account_type != expected_type:
        raise HTTPException(400, f"حساب {label} غير صالح")
    _scope(user, account.branch_id)
    return account


def _create_service_booking(db: Session, user: User, *, program: TravelProgram, pilgrim: Pilgrim, agent_id: int | None, customer_id: int | None, supplier_id: int, sale_price: Decimal, supplier_cost: Decimal, quota_id: int | None = None) -> ProgramBooking:
    if agent_id is None and customer_id is None:
        raise HTTPException(400, "يجب تحديد الوكيل أو العميل المباشر")
    if agent_id is not None and customer_id is not None:
        raise HTTPException(400, "لا يجتمع الوكيل والعميل المباشر في نفس الخدمة")
    _party(db, user, supplier_id, {"supplier", "both"}, "المورد", "liability")
    if agent_id is not None:
        _party(db, user, agent_id, {"agent"}, "الوكيل", "asset")
    else:
        _party(db, user, customer_id, {"customer", "both"}, "العميل", "asset")
    if sale_price <= 0:
        raise HTTPException(400, "سعر البيع يجب أن يكون أكبر من صفر")
    if supplier_cost < 0:
        raise HTTPException(400, "تكلفة المورد لا يمكن أن تكون سالبة")
    booking = ProgramBooking(
        program_id=program.id,
        pilgrim_id=pilgrim.id,
        customer_id=customer_id,
        agent_id=agent_id,
        quota_id=quota_id,
        supplier_id=supplier_id,
        sale_price=sale_price,
        supplier_cost=supplier_cost,
        paid_amount=Decimal("0"),
        remaining_amount=sale_price,
        profit=sale_price - supplier_cost,
        customer_type="agency" if agent_id is not None else "direct",
        status="reserved",
        branch_id=user.branch_id,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


@router.get("/quotas")
def list_quotas(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    stmt = select(HajjQuota).order_by(HajjQuota.id.desc())
    if user.branch_id is not None:
        stmt = stmt.where((HajjQuota.branch_id == user.branch_id) | HajjQuota.branch_id.is_(None))
    rows = list(db.scalars(stmt))
    return [
        {"id": row.id, "name_ar": row.name_ar, "season": row.season, "supplier_id": row.supplier_id,
         "total_units": row.total_units, "used_units": row.used_units,
         "remaining_units": max(row.total_units - row.used_units, 0),
         "unit_cost": row.unit_cost, "status": row.status, "branch_id": row.branch_id}
        for row in rows
    ]


@router.post("/quotas", status_code=201)
def create_quota(payload: QuotaCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    supplier = _party(db, user, payload.supplier_id, {"supplier", "both"}, "مورد الحصة", "liability")
    quota = HajjQuota(name_ar=payload.name_ar.strip(), season=payload.season.strip(), supplier_id=supplier.id,
                      total_units=payload.total_units, used_units=0, unit_cost=payload.unit_cost,
                      branch_id=user.branch_id, status="open")
    db.add(quota)
    db.commit()
    db.refresh(quota)
    return quota


@router.get("/bookings")
def list_hajj_bookings(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    stmt = select(ProgramBooking).join(TravelProgram, TravelProgram.id == ProgramBooking.program_id).where(TravelProgram.program_type == "hajj")
    if user.branch_id is not None:
        stmt = stmt.where((ProgramBooking.branch_id == user.branch_id) | ProgramBooking.branch_id.is_(None))
    return list(db.scalars(stmt.order_by(ProgramBooking.id.desc())))


@router.post("/bookings", status_code=201)
def create_hajj_booking(payload: HajjBookingCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    program = db.get(TravelProgram, payload.program_id)
    if not program or not program.is_active or program.program_type != "hajj":
        raise HTTPException(404, "برنامج الحج غير موجود أو غير نشط")
    _scope(user, program.branch_id)
    pilgrim = db.get(Pilgrim, payload.pilgrim_id)
    if not pilgrim:
        raise HTTPException(404, "الحاج غير موجود")
    _scope(user, pilgrim.branch_id)
    quota = db.scalar(select(HajjQuota).where(HajjQuota.id == payload.quota_id).with_for_update())
    if not quota:
        raise HTTPException(404, "حصة الحج غير موجودة")
    _scope(user, quota.branch_id)
    if quota.status != "open":
        raise HTTPException(409, "حصة الحج مغلقة")
    if quota.used_units >= quota.total_units:
        raise HTTPException(409, "اكتملت حصة الحجاج لهذا المورد")
    cost = payload.supplier_cost if payload.supplier_cost is not None else quota.unit_cost
    quota.used_units += 1
    booking = _create_service_booking(db, user, program=program, pilgrim=pilgrim, agent_id=payload.agent_id,
                                       customer_id=payload.customer_id, supplier_id=quota.supplier_id,
                                       sale_price=payload.sale_price, supplier_cost=cost, quota_id=quota.id)
    return booking


@router.post("/bookings/{booking_id}/post")
def post_hajj_booking(booking_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    booking = db.get(ProgramBooking, booking_id)
    if not booking or not _branch_match := True:
        pass
    if not booking:
        raise HTTPException(404, "حجز الحج غير موجود")
    _scope(user, booking.branch_id)
    if booking.status != "reserved" or booking.journal_entry_id:
        raise HTTPException(400, "الحجز غير قابل للترحيل")
    program = db.get(TravelProgram, booking.program_id)
    if not program or program.program_type != "hajj":
        raise HTTPException(400, "الحجز ليس من حج")
    counterparty = _party(db, user, booking.agent_id or booking.customer_id,
                          {"agent", "customer", "both"} if booking.agent_id is None else {"agent"},
                          "الطرف", "asset")
    supplier = _party(db, user, booking.supplier_id, {"supplier", "both"}, "مورد الحج", "liability")
    revenue = _setting_account(db, user, "travel_revenue_account_id", "revenue", "إيراد الحج والعمرة")
    lines = [
        {"account_id": counterparty.account_id, "debit": booking.sale_price, "credit": Decimal("0"), "description": f"استحقاق خدمات الحج للحجز #{booking.id}"},
        {"account_id": revenue.id, "debit": Decimal("0"), "credit": booking.sale_price, "description": f"إيراد الحج للحجز #{booking.id}"},
    ]
    if booking.supplier_cost > 0:
        cost_account = _setting_account(db, user, "travel_cost_account_id", "expense", "تكلفة الحج والعمرة")
        lines.extend([
            {"account_id": cost_account.id, "debit": booking.supplier_cost, "credit": Decimal("0"), "description": f"تكلفة حج للحجز #{booking.id}"},
            {"account_id": supplier.account_id, "debit": Decimal("0"), "credit": booking.supplier_cost, "description": f"مستحق مورد الحج للحجز #{booking.id}"},
        ])
    entry = create_journal(db, entry_number=f"HAJJ-BOOK-{booking.id}", entry_date=booking.booked_at.date(),
                           description=f"ترحيل خدمة حج للحجز #{booking.id}", lines=lines, created_by=user.id,
                           branch_id=booking.branch_id, status="posted")
    booking.journal_entry_id = entry.id
    booking.status = "confirmed"
    db.commit()
    db.refresh(booking)
    return booking


@router.post("/bookings/{booking_id}/cancel")
def cancel_hajj_booking(booking_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    booking = db.get(ProgramBooking, booking_id)
    if not booking:
        raise HTTPException(404, "حجز الحج غير موجود")
    _scope(user, booking.branch_id)
    if booking.status == "cancelled":
        raise HTTPException(400, "الحجز ملغى مسبقًا")
    if booking.journal_entry_id:
        original = db.get(__import__("app.models.journal", fromlist=["JournalEntry"]).JournalEntry, booking.journal_entry_id)
        if not original:
            raise HTTPException(409, "القيد المرتبط بالحجز غير موجود")
        try:
            create_journal(db, entry_number=f"REV-HAJJ-BOOK-{booking.id}", entry_date=date.today(),
                           description=f"عكس حجز الحج #{booking.id}",
                           lines=[{"account_id": l.account_id, "debit": l.credit, "credit": l.debit} for l in original.lines],
                           created_by=user.id, branch_id=booking.branch_id, status="posted")
        except ValueError as exc:
            db.rollback(); raise HTTPException(400, str(exc))
    if booking.quota_id:
        quota = db.get(HajjQuota, booking.quota_id)
        if quota and quota.used_units > 0:
            quota.used_units -= 1
    booking.status = "cancelled"
    db.commit()
    db.refresh(booking)
    return booking


@router.get("/agents/{agent_id}/balance")
def agent_balance(agent_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    agent = _party(db, user, agent_id, {"agent"}, "الوكيل", "asset")
    debit = db.scalar(select(func.coalesce(func.sum(ProgramBooking.sale_price), 0)).where(ProgramBooking.agent_id == agent.id, ProgramBooking.status == "confirmed")) or Decimal("0")
    paid = db.scalar(select(func.coalesce(func.sum(ProgramBooking.paid_amount), 0)).where(ProgramBooking.agent_id == agent.id, ProgramBooking.status == "confirmed")) or Decimal("0")
    return {"agent_id": agent.id, "agent_name": agent.name, "debit": debit, "paid": paid, "remaining": debit - paid}


@umrah_router.get("/bookings")
def list_umrah_bookings(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    stmt = select(ProgramBooking).join(TravelProgram, TravelProgram.id == ProgramBooking.program_id).where(TravelProgram.program_type == "umrah")
    if user.branch_id is not None:
        stmt = stmt.where((ProgramBooking.branch_id == user.branch_id) | ProgramBooking.branch_id.is_(None))
    return list(db.scalars(stmt.order_by(ProgramBooking.id.desc())))


@umrah_router.post("/bookings", status_code=201)
def create_umrah_booking(payload: UmrahBookingCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    program = db.get(TravelProgram, payload.program_id)
    if not program or not program.is_active or program.program_type != "umrah":
        raise HTTPException(404, "برنامج العمرة غير موجود أو غير نشط")
    _scope(user, program.branch_id)
    pilgrim = db.get(Pilgrim, payload.pilgrim_id)
    if not pilgrim:
        raise HTTPException(404, "المعتمر غير موجود")
    _scope(user, pilgrim.branch_id)
    booked = db.scalar(select(func.count(ProgramBooking.id)).where(ProgramBooking.program_id == program.id, ProgramBooking.status == "confirmed")) or 0
    if program.capacity and booked >= program.capacity:
        raise HTTPException(409, "لا توجد مقاعد متاحة في برنامج العمرة")
    return _create_service_booking(db, user, program=program, pilgrim=pilgrim, agent_id=payload.agent_id,
                                   customer_id=payload.customer_id, supplier_id=payload.supplier_id,
                                   sale_price=payload.sale_price, supplier_cost=payload.supplier_cost)


@umrah_router.post("/bookings/{booking_id}/post")
def post_umrah_booking(booking_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    booking = db.get(ProgramBooking, booking_id)
    if not booking:
        raise HTTPException(404, "حجز العمرة غير موجود")
    _scope(user, booking.branch_id)
    if booking.status != "reserved" or booking.journal_entry_id:
        raise HTTPException(400, "الحجز غير قابل للترحيل")
    program = db.get(TravelProgram, booking.program_id)
    if not program or program.program_type != "umrah":
        raise HTTPException(400, "الحجز ليس من عمرة")
    counterparty = _party(db, user, booking.agent_id or booking.customer_id,
                          {"agent", "customer", "both"} if booking.agent_id is None else {"agent"},
                          "الطرف", "asset")
    supplier = _party(db, user, booking.supplier_id, {"supplier", "both"}, "مورد العمرة", "liability")
    revenue = _setting_account(db, user, "travel_revenue_account_id", "revenue", "إيراد الحج والعمرة")
    lines = [
        {"account_id": counterparty.account_id, "debit": booking.sale_price, "credit": Decimal("0"), "description": f"استحقاق خدمة عمرة #{booking.id}"},
        {"account_id": revenue.id, "debit": Decimal("0"), "credit": booking.sale_price, "description": f"إيراد العمرة للحجز #{booking.id}"},
    ]
    if booking.supplier_cost > 0:
        cost_account = _setting_account(db, user, "travel_cost_account_id", "expense", "تكلفة الحج والعمرة")
        lines.extend([
            {"account_id": cost_account.id, "debit": booking.supplier_cost, "credit": Decimal("0"), "description": f"تكلفة عمرة #{booking.id}"},
            {"account_id": supplier.account_id, "debit": Decimal("0"), "credit": booking.supplier_cost, "description": f"مستحق مورد العمرة #{booking.id}"},
        ])
    entry = create_journal(db, entry_number=f"UMRAH-BOOK-{booking.id}", entry_date=booking.booked_at.date(),
                           description=f"ترحيل خدمة عمرة للحجز #{booking.id}", lines=lines, created_by=user.id,
                           branch_id=booking.branch_id, status="posted")
    booking.journal_entry_id = entry.id
    booking.status = "confirmed"
    db.commit()
    db.refresh(booking)
    return booking


@umrah_router.post("/bookings/{booking_id}/cancel")
def cancel_umrah_booking(booking_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    booking = db.get(ProgramBooking, booking_id)
    if not booking:
        raise HTTPException(404, "حجز العمرة غير موجود")
    _scope(user, booking.branch_id)
    if booking.status == "cancelled":
        raise HTTPException(400, "الحجز ملغى مسبقًا")
    if booking.journal_entry_id:
        original = db.get(__import__("app.models.journal", fromlist=["JournalEntry"]).JournalEntry, booking.journal_entry_id)
        if not original:
            raise HTTPException(409, "القيد المرتبط بالحجز غير موجود")
        try:
            create_journal(db, entry_number=f"REV-UMRAH-BOOK-{booking.id}", entry_date=date.today(),
                           description=f"عكس حجز العمرة #{booking.id}",
                           lines=[{"account_id": l.account_id, "debit": l.credit, "credit": l.debit} for l in original.lines],
                           created_by=user.id, branch_id=booking.branch_id, status="posted")
        except ValueError as exc:
            db.rollback(); raise HTTPException(400, str(exc))
    booking.status = "cancelled"
    db.commit()
    db.refresh(booking)
    return booking
