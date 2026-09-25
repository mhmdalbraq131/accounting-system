from datetime import date
import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_permission
from app.db.session import get_db
from app.models.accounting_dimension import AccountingDimension
from app.models.audit_log import AuditLog
from app.models.expense import Expense
from app.models.fiscal_period import FiscalPeriod
from app.models.journal import JournalEntry
from app.models.user import User

router = APIRouter(prefix="/accounting-controls", tags=["الضبط المحاسبي"])


class DimensionCreate(BaseModel):
    dimension_type: str = "cost_center"
    code: str = Field(min_length=1, max_length=40)
    name_ar: str = Field(min_length=1, max_length=200)
    branch_id: int | None = None


class DimensionOut(DimensionCreate):
    id: int
    is_active: bool
    model_config = ConfigDict(from_attributes=True)


@router.get("/dimensions", response_model=list[DimensionOut])
def list_dimensions(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    stmt = select(AccountingDimension).where(AccountingDimension.is_active.is_(True)).order_by(AccountingDimension.code)
    if user.branch_id is not None:
        stmt = stmt.where((AccountingDimension.branch_id == user.branch_id) | AccountingDimension.branch_id.is_(None))
    return list(db.scalars(stmt))


@router.post("/dimensions", response_model=DimensionOut, status_code=201)
def create_dimension(payload: DimensionCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_permission(user, "accounting.dimensions.manage", db)
    if not payload.code.strip() or not payload.name_ar.strip():
        raise HTTPException(400, "رمز واسم البعد المحاسبي مطلوبان")
    if db.scalar(select(AccountingDimension).where(AccountingDimension.code == payload.code.strip())):
        raise HTTPException(409, "رمز البعد المحاسبي مستخدم مسبقًا")
    branch_id = user.branch_id if payload.branch_id is None else payload.branch_id
    if user.branch_id is not None and branch_id != user.branch_id:
        raise HTTPException(403, "لا يمكنك إنشاء بعد لفرع آخر")
    row = AccountingDimension(
        dimension_type=payload.dimension_type.strip(),
        code=payload.code.strip(),
        name_ar=payload.name_ar.strip(),
        branch_id=branch_id,
    )
    db.add(row)
    db.flush()
    db.add(AuditLog(
        user_id=user.id, action="create", entity_type="accounting_dimension", entity_id=row.id,
        details=json.dumps({"code": row.code, "type": row.dimension_type}, ensure_ascii=False),
    ))
    db.commit()
    db.refresh(row)
    return row


class FiscalPeriodCreate(BaseModel):
    name: str
    start_date: date
    end_date: date
    branch_id: int | None = None


class FiscalPeriodOut(FiscalPeriodCreate):
    id: int
    is_closed: bool
    model_config = ConfigDict(from_attributes=True)


@router.post("/dimensions/{dimension_id}/disable", response_model=DimensionOut)
def disable_dimension(
    dimension_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_permission(user, "accounting.dimensions.manage", db)
    row = db.get(AccountingDimension, dimension_id)
    if not row:
        raise HTTPException(404, "البعد المحاسبي غير موجود")
    if user.branch_id is not None and row.branch_id not in (None, user.branch_id):
        raise HTTPException(403, "البعد المحاسبي تابع لفرع آخر")
    if not row.is_active:
        return row
    row.is_active = False
    db.add(AuditLog(
        user_id=user.id,
        action="disable",
        entity_type="accounting_dimension",
        entity_id=row.id,
        details=json.dumps({"code": row.code}, ensure_ascii=False),
    ))
    db.commit()
    db.refresh(row)
    return row


@router.get("/periods", response_model=list[FiscalPeriodOut])
def list_periods(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    stmt = select(FiscalPeriod).order_by(FiscalPeriod.start_date.desc())
    if user.branch_id is not None:
        stmt = stmt.where((FiscalPeriod.branch_id == user.branch_id) | FiscalPeriod.branch_id.is_(None))
    return list(db.scalars(stmt))


@router.post("/periods", response_model=FiscalPeriodOut, status_code=201)
def create_period(payload: FiscalPeriodCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_permission(user, "accounting.periods.manage", db)
    if not payload.name.strip():
        raise HTTPException(400, "اسم الفترة المحاسبية مطلوب")
    if payload.end_date < payload.start_date:
        raise HTTPException(400, "تاريخ نهاية الفترة يجب أن يكون بعد بدايتها")
    branch_id = user.branch_id if payload.branch_id is None else payload.branch_id
    if user.branch_id is not None and branch_id != user.branch_id:
        raise HTTPException(403, "لا يمكنك إنشاء فترة لفرع آخر")
    overlap = select(FiscalPeriod).where(
        FiscalPeriod.start_date <= payload.end_date,
        FiscalPeriod.end_date >= payload.start_date,
        FiscalPeriod.branch_id == branch_id if branch_id is None else FiscalPeriod.branch_id.in_([None, branch_id]),
    )
    if db.scalar(overlap):
        raise HTTPException(409, "الفترة تتداخل مع فترة محاسبية موجودة")
    row = FiscalPeriod(name=payload.name.strip(), start_date=payload.start_date, end_date=payload.end_date, branch_id=branch_id)
    db.add(row)
    db.flush()
    db.add(AuditLog(
        user_id=user.id, action="create", entity_type="fiscal_period", entity_id=row.id,
        details=json.dumps({"name": row.name}, ensure_ascii=False),
    ))
    db.commit()
    db.refresh(row)
    return row


@router.post("/periods/{period_id}/close")
def close_period(period_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_permission(user, "accounting.periods.manage", db)
    period = db.get(FiscalPeriod, period_id)
    if not period:
        raise HTTPException(404, "الفترة المحاسبية غير موجودة")
    if user.branch_id is not None and period.branch_id not in (None, user.branch_id):
        raise HTTPException(403, "الفترة تابعة لفرع آخر")
    if period.is_closed:
        return {"id": period.id, "is_closed": True, "already_closed": True}

    draft_journal = db.scalar(
        select(JournalEntry.id).where(
            JournalEntry.fiscal_period_id == period.id,
            JournalEntry.status == "draft",
        ).limit(1)
    )
    if draft_journal is not None:
        raise HTTPException(409, "لا يمكن إغلاق الفترة: توجد قيود مسودة يجب ترحيلها أو إلغاؤها أولًا")

    draft_expense = db.scalar(
        select(Expense.id).where(
            Expense.status == "draft",
            Expense.expense_date >= period.start_date,
            Expense.expense_date <= period.end_date,
            Expense.branch_id.is_(None) if period.branch_id is None else Expense.branch_id == period.branch_id,
        ).limit(1)
    )
    if draft_expense is not None:
        raise HTTPException(409, "لا يمكن إغلاق الفترة: توجد مصروفات مسودة ضمن الفترة")
    if period.branch_id is None:
        branch_draft_expense = db.scalar(
            select(Expense.id).where(
                Expense.status == "draft",
                Expense.expense_date >= period.start_date,
                Expense.expense_date <= period.end_date,
            ).limit(1)
        )
        if branch_draft_expense is not None:
            raise HTTPException(409, "لا يمكن إغلاق الفترة: توجد مصروفات مسودة ضمن الفترة")

    period.is_closed = True
    db.add(AuditLog(
        user_id=user.id, action="close", entity_type="fiscal_period", entity_id=period.id,
        details=json.dumps({"name": period.name}, ensure_ascii=False),
    ))
    db.commit()
    return {"id": period.id, "is_closed": True}


@router.get("/audit")
def list_audit_logs(db: Session = Depends(get_db), user: User = Depends(get_current_user), limit: int = 100):
    require_permission(user, "audit.read", db)
    limit = max(1, min(limit, 500))
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
    return list(db.scalars(stmt))
