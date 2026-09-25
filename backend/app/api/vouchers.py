from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_permission
from app.accounting.voucher_service import cancel_voucher, create_voucher, post_voucher
from app.db.session import get_db
from app.models.user import User
from app.models.voucher import Voucher
from app.models.financial import FinancialAccount
from app.models.account import Account
from app.models.settings import SystemSetting
from app.models.currency import Currency

router = APIRouter(prefix="/vouchers", tags=["السندات"])
VALID_LINK_TYPES = {"hajj_booking", "umrah_booking", "service_order"}


class VoucherCreate(BaseModel):
    voucher_number: str | None = None  # legacy clients may still send this; it is treated as manual reference.
    manual_voucher_number: str | None = None
    voucher_type: str
    voucher_date: date
    amount: Decimal
    description: str
    source_account_id: int
    destination_account_id: int
    currency_id: int | None = None
    exchange_rate: Decimal | None = None
    linked_service_type: str | None = None
    linked_service_id: int | None = None


class VoucherOut(VoucherCreate):
    id: int
    voucher_number: str
    manual_voucher_number: str | None
    status: str
    journal_entry_id: int | None
    model_config = ConfigDict(from_attributes=True)


def _setting_value(db: Session, key: str, default: str) -> str:
    value = db.scalar(select(SystemSetting.value).where(SystemSetting.key == key))
    return value or default


def _next_voucher_number(db: Session, voucher_type: str, voucher_date: date) -> str:
    prefix_defaults = {"receipt": "RV", "payment": "PV", "transfer": "TV"}
    key_map = {"receipt": "voucher_prefix_receipt", "payment": "voucher_prefix_payment", "transfer": "voucher_prefix_transfer"}
    prefix = _setting_value(db, key_map[voucher_type], prefix_defaults[voucher_type]).strip() or prefix_defaults[voucher_type]
    base = f"{prefix}-{voucher_date:%Y}-"
    rows = db.scalars(select(Voucher.voucher_number).where(Voucher.voucher_number.like(f"{base}%")).order_by(Voucher.id.desc()).limit(1000)).all()
    used = set()
    for value in rows:
        try:
            used.add(int(value.rsplit("-", 1)[1]))
        except (ValueError, IndexError):
            continue
    sequence = 1
    while sequence in used:
        sequence += 1
    return f"{base}{sequence:05d}"


def _validate_account_branch(db: Session, account_id: int, user: User) -> None:
    account = db.get(Account, account_id)
    if not account or not account.is_active:
        raise HTTPException(status_code=400, detail="أحد الحسابات المحددة غير موجود أو غير نشط")
    if user.branch_id is not None and account.branch_id not in (None, user.branch_id):
        raise HTTPException(status_code=403, detail="الحساب تابع لفرع آخر")


def _base_currency(db: Session) -> Currency | None:
    return db.scalar(select(Currency).where(Currency.is_base.is_(True), Currency.is_active.is_(True)))


@router.post("", response_model=VoucherOut, status_code=201)
def create(payload: VoucherCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_permission(user, "vouchers.create", db)
    if payload.voucher_type not in {"receipt", "payment", "transfer"}:
        raise HTTPException(status_code=400, detail="نوع السند غير مدعوم")
    if payload.linked_service_type is not None and payload.linked_service_type not in VALID_LINK_TYPES:
        raise HTTPException(status_code=400, detail="نوع الخدمة المرتبطة غير مدعوم")
    if payload.linked_service_type and payload.linked_service_id is None:
        raise HTTPException(status_code=400, detail="يجب تحديد رقم الخدمة المرتبطة")
    _validate_account_branch(db, payload.source_account_id, user)
    _validate_account_branch(db, payload.destination_account_id, user)

    base_currency = _base_currency(db)
    if not base_currency:
        raise HTTPException(status_code=409, detail="يجب تحديد العملة الأساسية للنظام من شاشة الإعدادات قبل إضافة أي سند")
    currency_id = payload.currency_id or base_currency.id

    legacy_manual = (payload.voucher_number or "").strip() or None
    manual_number = (payload.manual_voucher_number or "").strip() or legacy_manual
    voucher_number = _next_voucher_number(db, payload.voucher_type, payload.voucher_date)
    try:
        voucher = create_voucher(
            db,
            voucher_number=voucher_number,
            manual_voucher_number=manual_number,
            voucher_type=payload.voucher_type,
            voucher_date=payload.voucher_date,
            amount=payload.amount,
            description=payload.description,
            source_account_id=payload.source_account_id,
            destination_account_id=payload.destination_account_id,
            currency_id=currency_id,
            exchange_rate=payload.exchange_rate,
            created_by=user.id,
            branch_id=user.branch_id,
            linked_service_type=payload.linked_service_type,
            linked_service_id=payload.linked_service_id,
        )
        db.commit(); db.refresh(voucher); return voucher
    except ValueError as exc:
        db.rollback(); raise HTTPException(status_code=400, detail=str(exc))


@router.get("", response_model=list[VoucherOut])
def list_vouchers(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    stmt = select(Voucher).order_by(Voucher.voucher_date.desc(), Voucher.id.desc())
    if user.branch_id is not None:
        stmt = stmt.where((Voucher.branch_id == user.branch_id) | Voucher.branch_id.is_(None))
    return list(db.scalars(stmt))


@router.post("/{voucher_id}/post", response_model=VoucherOut)
def post(voucher_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_permission(user, "vouchers.post", db)
    voucher = db.get(Voucher, voucher_id)
    if not voucher: raise HTTPException(status_code=404, detail="السند غير موجود")
    if user.branch_id is not None and voucher.branch_id not in (None, user.branch_id): raise HTTPException(status_code=403, detail="السند تابع لفرع آخر")
    try:
        post_voucher(db, voucher); db.commit(); db.refresh(voucher); return voucher
    except ValueError as exc:
        db.rollback(); raise HTTPException(status_code=400, detail=str(exc))


@router.post("/{voucher_id}/cancel", response_model=VoucherOut)
def cancel(voucher_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_permission(user, "vouchers.cancel", db)
    voucher = db.get(Voucher, voucher_id)
    if not voucher: raise HTTPException(status_code=404, detail="السند غير موجود")
    if user.branch_id is not None and voucher.branch_id not in (None, user.branch_id): raise HTTPException(status_code=403, detail="السند تابع لفرع آخر")
    try:
        cancel_voucher(db, voucher); db.commit(); db.refresh(voucher); return voucher
    except ValueError as exc:
        db.rollback(); raise HTTPException(status_code=400, detail=str(exc))


@router.get("/{voucher_id}/print-data")
def print_data(voucher_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    voucher = db.get(Voucher, voucher_id)
    if not voucher: raise HTTPException(status_code=404, detail="السند غير موجود")
    if user.branch_id is not None and voucher.branch_id not in (None, user.branch_id): raise HTTPException(status_code=403, detail="السند تابع لفرع آخر")
    return {"voucher": VoucherOut.model_validate(voucher), "printed_by": user.full_name, "printed_by_username": user.username, "branch_id": user.branch_id} 
