from datetime import date, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.accounting.journal_service import create_journal
from app.auth import get_current_user
from app.db.session import get_db
from app.models.account import Account
from app.models.party import Party
from app.models.service_order import ServiceOrder
from app.models.settings import SystemSetting
from app.models.travel import Pilgrim
from app.models.user import User

router = APIRouter(prefix="/services", tags=["الخدمات"])

SERVICE_LABELS = {"flight": "الطيران", "bus": "الباصات", "visit": "الزيارات", "work_visa": "فيز العمل"}


class ServiceCreate(BaseModel):
    service_type: str
    reference_no: str = Field(min_length=1, max_length=60)
    service_date: date
    description: str = Field(min_length=1, max_length=500)
    details: dict | None = None
    pilgrim_id: int | None = None
    customer_id: int | None = None
    agent_id: int | None = None
    supplier_id: int | None = None
    sale_price: Decimal = Field(gt=0)
    supplier_cost: Decimal = Field(default=Decimal("0"), ge=0)


def _scope(user: User, branch_id: int | None) -> None:
    if user.branch_id is not None and branch_id not in (None, user.branch_id): raise HTTPException(403, "السجل تابع لفرع آخر")


def _party(db: Session, user: User, party_id: int | None, allowed: set[str], label: str, account_type: str) -> Party:
    if party_id is None: raise HTTPException(400, f"يجب تحديد {label}")
    party = db.get(Party, party_id)
    if not party or not party.is_active or party.party_type not in allowed: raise HTTPException(400, f"{label} غير موجود أو نوعه غير صحيح")
    _scope(user, party.branch_id)
    if party.account_id is None: raise HTTPException(400, f"{label} غير مربوط بحساب محاسبي")
    account = db.get(Account, party.account_id)
    if not account or not account.is_active or account.account_type != account_type: raise HTTPException(400, f"حساب {label} يجب أن يكون من نوع {account_type}")
    _scope(user, account.branch_id)
    return party


def _account_setting(db: Session, user: User, service_type: str, kind: str) -> Account:
    prefix = SERVICE_LABELS[service_type]; key = f"{service_type}_{kind}_account_id"; expected = "revenue" if kind == "revenue" else "cost_of_service"
    raw = db.scalar(select(SystemSetting.value).where(SystemSetting.key == key)); account = None
    if raw:
        try: account = db.get(Account, int(raw))
        except ValueError: raise HTTPException(400, f"إعداد {prefix} غير صالح")
    if account is None:
        stmt = select(Account).where(Account.account_type == expected, Account.is_active.is_(True))
        if user.branch_id is not None: stmt = stmt.where((Account.branch_id == user.branch_id) | Account.branch_id.is_(None))
        candidates = list(db.scalars(stmt.order_by(Account.code)))
        if len(candidates) != 1: raise HTTPException(400, f"اضبط حساب {prefix} {kind} في الإعدادات")
        account = candidates[0]
    if account.account_type != expected or not account.is_active: raise HTTPException(400, f"حساب {prefix} غير صالح")
    _scope(user, account.branch_id); return account


@router.get("/{service_type}")
def list_services(service_type: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if service_type not in SERVICE_LABELS: raise HTTPException(400, "نوع الخدمة غير مدعوم")
    stmt = select(ServiceOrder).where(ServiceOrder.service_type == service_type).order_by(ServiceOrder.id.desc())
    if user.branch_id is not None: stmt = stmt.where((ServiceOrder.branch_id == user.branch_id) | ServiceOrder.branch_id.is_(None))
    return list(db.scalars(stmt))


@router.post("", status_code=201)
def create_service(payload: ServiceCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if payload.service_type not in SERVICE_LABELS: raise HTTPException(400, "نوع الخدمة غير مدعوم")
    if db.scalar(select(ServiceOrder).where(ServiceOrder.reference_no == payload.reference_no)): raise HTTPException(409, "رقم الخدمة مستخدم مسبقًا")
    if payload.agent_id is None and payload.customer_id is None: raise HTTPException(400, "يجب تحديد الوكيل أو العميل المباشر")
    if payload.agent_id is not None and payload.customer_id is not None: raise HTTPException(400, "لا يجتمع الوكيل والعميل في نفس الخدمة")
    if payload.pilgrim_id is not None:
        pilgrim = db.get(Pilgrim, payload.pilgrim_id)
        if not pilgrim: raise HTTPException(404, "المستفيد غير موجود")
        _scope(user, pilgrim.branch_id)
    if payload.agent_id is not None: _party(db, user, payload.agent_id, {"agent"}, "الوكيل", "asset")
    if payload.customer_id is not None: _party(db, user, payload.customer_id, {"customer", "both"}, "العميل", "asset")
    if payload.supplier_cost > 0: _party(db, user, payload.supplier_id, {"supplier", "both"}, "المورد", "liability")
    row = ServiceOrder(**payload.model_dump(), paid_amount=Decimal("0"), remaining_amount=payload.sale_price, profit=payload.sale_price-payload.supplier_cost,
                       status="draft", branch_id=user.branch_id, created_by=user.id, created_at=datetime.utcnow())
    db.add(row); db.commit(); db.refresh(row); return row


@router.post("/{service_type}/{service_id}/post")
def post_service(service_type: str, service_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if service_type not in SERVICE_LABELS: raise HTTPException(400, "نوع الخدمة غير مدعوم")
    row = db.get(ServiceOrder, service_id)
    if not row or row.service_type != service_type: raise HTTPException(404, "الخدمة غير موجودة")
    _scope(user, row.branch_id)
    if row.status != "draft" or row.journal_entry_id: raise HTTPException(400, "الخدمة غير قابلة للترحيل")
    counterparty = _party(db, user, row.agent_id or row.customer_id, {"agent", "customer", "both"} if row.agent_id is None else {"agent"}, "الطرف", "asset")
    revenue = _account_setting(db, user, service_type, "revenue")
    lines = [{"account_id": counterparty.account_id, "debit": row.sale_price, "credit": Decimal("0"), "description": f"استحقاق خدمة {SERVICE_LABELS[service_type]} #{row.id}"},
             {"account_id": revenue.id, "debit": Decimal("0"), "credit": row.sale_price, "description": f"إيراد {SERVICE_LABELS[service_type]} #{row.id}"}]
    if row.supplier_cost > 0:
        supplier = _party(db, user, row.supplier_id, {"supplier", "both"}, "المورد", "liability")
        cost_account = _account_setting(db, user, service_type, "cost")
        lines.extend([{ "account_id": cost_account.id, "debit": row.supplier_cost, "credit": Decimal("0"), "description": f"تكلفة {SERVICE_LABELS[service_type]} #{row.id}"},
                      {"account_id": supplier.account_id, "debit": Decimal("0"), "credit": row.supplier_cost, "description": f"مستحق المورد لخدمة #{row.id}"}])
    try:
        entry = create_journal(db, entry_number=f"{service_type.upper()}-{row.id}", entry_date=row.service_date, description=row.description, lines=lines, created_by=user.id, branch_id=row.branch_id, status="posted")
    except ValueError as exc:
        db.rollback(); raise HTTPException(400, str(exc))
    entry.posted_at = datetime.utcnow(); row.journal_entry_id = entry.id; row.status = "posted"; db.commit(); db.refresh(row); return row


@router.post("/{service_type}/{service_id}/cancel")
def cancel_service(service_type: str, service_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if service_type not in SERVICE_LABELS: raise HTTPException(400, "نوع الخدمة غير مدعوم")
    row = db.get(ServiceOrder, service_id)
    if not row or row.service_type != service_type: raise HTTPException(404, "الخدمة غير موجودة")
    _scope(user, row.branch_id)
    if row.status == "cancelled": raise HTTPException(400, "الخدمة ملغاة مسبقًا")
    if Decimal(str(row.paid_amount or 0)) > 0:
        raise HTTPException(409, "لا يمكن إلغاء خدمة عليها تحصيلات؛ اعكس أو ألغِ سندات القبض المرتبطة أولًا")
    if row.journal_entry_id:
        original = db.get(__import__("app.models.journal", fromlist=["JournalEntry"]).JournalEntry, row.journal_entry_id)
        if not original: raise HTTPException(409, "القيد المرتبط بالخدمة غير موجود")
        try:
            create_journal(db, entry_number=f"REV-{service_type.upper()}-{row.id}", entry_date=date.today(), description=f"عكس خدمة {SERVICE_LABELS[service_type]} #{row.id}",
                           lines=[{"account_id": line.account_id, "debit": line.credit, "credit": line.debit} for line in original.lines], created_by=user.id, branch_id=row.branch_id, status="posted")
        except ValueError as exc:
            db.rollback(); raise HTTPException(400, str(exc))
    row.status = "cancelled"; db.commit(); db.refresh(row); return row