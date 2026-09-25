from datetime import date, datetime
from decimal import Decimal
import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.accounting.journal_service import create_journal, _resolve_period
from app.auth import get_current_user, require_permission
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.models.journal import JournalEntry
from app.models.user import User

router = APIRouter(prefix="/journals", tags=["القيود اليومية"])


class JournalLineIn(BaseModel):
    account_id: int
    dimension_id: int | None = None
    description: str | None = Field(default=None, max_length=500)
    debit: Decimal = Decimal("0")
    credit: Decimal = Decimal("0")


class JournalCreate(BaseModel):
    entry_number: str = Field(min_length=1, max_length=40)
    entry_date: date
    description: str = Field(min_length=1, max_length=500)
    fiscal_period_id: int | None = None
    lines: list[JournalLineIn] = Field(min_length=2)


def _visible(entry: JournalEntry, user: User) -> None:
    if user.branch_id is not None and entry.branch_id not in (None, user.branch_id):
        raise HTTPException(403, "القيد تابع لفرع آخر")


def _serialize(entry: JournalEntry) -> dict:
    return {
        "id": entry.id,
        "entry_number": entry.entry_number,
        "entry_date": entry.entry_date,
        "description": entry.description,
        "status": entry.status,
        "created_by": entry.created_by,
        "branch_id": entry.branch_id,
        "fiscal_period_id": entry.fiscal_period_id,
        "posted_at": entry.posted_at,
        "lines": [
            {
                "id": line.id,
                "account_id": line.account_id,
                "dimension_id": line.dimension_id,
                "description": line.description,
                "debit": line.debit,
                "credit": line.credit,
            }
            for line in entry.lines
        ],
    }


@router.get("")
def list_journals(
    status: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_permission(user, "journals.view", db)
    stmt = select(JournalEntry).order_by(JournalEntry.entry_date.desc(), JournalEntry.id.desc())
    if user.branch_id is not None:
        stmt = stmt.where((JournalEntry.branch_id == user.branch_id) | JournalEntry.branch_id.is_(None))
    if status:
        if status not in {"draft", "posted", "cancelled"}:
            raise HTTPException(400, "حالة القيد غير صحيحة")
        stmt = stmt.where(JournalEntry.status == status)
    return [_serialize(entry) for entry in db.scalars(stmt).all()]


@router.post("", status_code=201)
def create_manual_journal(
    payload: JournalCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_permission(user, "journals.create", db)
    try:
        entry = create_journal(
            db,
            entry_number=payload.entry_number.strip(),
            entry_date=payload.entry_date,
            description=payload.description.strip(),
            lines=[line.model_dump() for line in payload.lines],
            created_by=user.id,
            branch_id=user.branch_id,
            status="draft",
            fiscal_period_id=payload.fiscal_period_id,
        )
        db.commit()
        db.refresh(entry)
        return _serialize(entry)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(400, str(exc))


@router.post("/{journal_id}/post")
def post_manual_journal(
    journal_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_permission(user, "journals.post", db)
    entry = db.get(JournalEntry, journal_id)
    if not entry:
        raise HTTPException(404, "القيد غير موجود")
    _visible(entry, user)
    if entry.status != "draft":
        raise HTTPException(400, "لا يمكن ترحيل قيد ليس في حالة مسودة")

    try:
        period = _resolve_period(db, entry.entry_date, entry.branch_id, entry.fiscal_period_id)
        if entry.fiscal_period_id is not None and period is None:
            raise ValueError("الفترة المحاسبية غير موجودة أو مغلقة")
        debit = sum((Decimal(str(line.debit or 0)) for line in entry.lines), Decimal("0"))
        credit = sum((Decimal(str(line.credit or 0)) for line in entry.lines), Decimal("0"))
        if debit != credit or debit <= 0:
            raise ValueError("القيد غير متوازن أو قيمته غير صالحة")
        entry.status = "posted"
        entry.posted_at = datetime.utcnow()
        db.add(AuditLog(
            user_id=user.id,
            action="post",
            entity_type="journal_entry",
            entity_id=entry.id,
            details=json.dumps({"entry_number": entry.entry_number}, ensure_ascii=False),
        ))
        db.commit()
        db.refresh(entry)
        return _serialize(entry)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(400, str(exc))


@router.post("/{journal_id}/cancel")
def cancel_manual_journal(
    journal_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_permission(user, "journals.cancel", db)
    entry = db.get(JournalEntry, journal_id)
    if not entry:
        raise HTTPException(404, "القيد غير موجود")
    _visible(entry, user)
    if entry.status == "cancelled":
        raise HTTPException(400, "القيد ملغى مسبقًا")

    if entry.status == "draft":
        entry.status = "cancelled"
        db.add(AuditLog(
            user_id=user.id, action="cancel", entity_type="journal_entry", entity_id=entry.id,
            details=json.dumps({"entry_number": entry.entry_number, "draft": True}, ensure_ascii=False),
        ))
        db.commit()
        db.refresh(entry)
        return _serialize(entry)

    try:
        reversal = create_journal(
            db,
            entry_number=f"REV-JV-{entry.entry_number}",
            entry_date=date.today(),
            description=f"عكس القيد {entry.entry_number}: {entry.description}",
            lines=[
                {
                    "account_id": line.account_id,
                    "dimension_id": line.dimension_id,
                    "description": line.description,
                    "debit": line.credit,
                    "credit": line.debit,
                }
                for line in entry.lines
            ],
            created_by=user.id,
            branch_id=entry.branch_id,
            status="posted",
        )
        reversal.posted_at = datetime.utcnow()
        entry.status = "cancelled"
        db.add(AuditLog(
            user_id=user.id, action="cancel", entity_type="journal_entry", entity_id=entry.id,
            details=json.dumps({"entry_number": entry.entry_number, "reversal_entry_id": reversal.id}, ensure_ascii=False),
        ))
        db.commit()
        db.refresh(entry)
        return {"cancelled": _serialize(entry), "reversal": _serialize(reversal)}
    except ValueError as exc:
        db.rollback()
        raise HTTPException(400, str(exc))
