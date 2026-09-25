from datetime import datetime
from decimal import Decimal
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.accounting_dimension import AccountingDimension
from app.models.audit_log import AuditLog
from app.models.fiscal_period import FiscalPeriod
from app.models.journal import JournalEntry, JournalLine


class UnbalancedJournalError(ValueError):
    pass


def _resolve_period(db: Session, entry_date, branch_id: int | None, fiscal_period_id: int | None):
    if fiscal_period_id is not None:
        period = db.get(FiscalPeriod, fiscal_period_id)
        if not period:
            raise ValueError("الفترة المحاسبية غير موجودة")
        if period.start_date > entry_date or period.end_date < entry_date:
            raise ValueError("تاريخ القيد خارج الفترة المحاسبية المحددة")
        if period.is_closed:
            raise ValueError("الفترة المحاسبية مغلقة ولا تقبل قيودًا جديدة")
        if branch_id is not None and period.branch_id not in (None, branch_id):
            raise ValueError("الفترة المحاسبية تابعة لفرع آخر")
        return period

    period = db.scalar(
        select(FiscalPeriod).where(
            FiscalPeriod.start_date <= entry_date,
            FiscalPeriod.end_date >= entry_date,
            FiscalPeriod.is_closed.is_(False),
            FiscalPeriod.branch_id.is_(None) if branch_id is None else FiscalPeriod.branch_id.in_([None, branch_id]),
        ).order_by(FiscalPeriod.branch_id.desc().nulls_last())
    )
    if period is not None:
        return period

    configured_periods = db.scalar(select(FiscalPeriod.id).limit(1))
    if configured_periods is not None:
        raise ValueError("لا توجد فترة محاسبية مفتوحة تغطي تاريخ القيد")
    return None


def resolve_reversal_date(db: Session, original_date, branch_id: int | None):
    """Return an open fiscal-period date suitable for reversing a posted entry."""
    from datetime import date

    today = date.today()
    candidates = list(db.scalars(
        select(FiscalPeriod).where(
            FiscalPeriod.is_closed.is_(False),
            FiscalPeriod.branch_id.is_(None) if branch_id is None else FiscalPeriod.branch_id.in_([None, branch_id]),
            FiscalPeriod.end_date >= original_date,
        ).order_by(FiscalPeriod.start_date)
    ))
    for period in candidates:
        if period.start_date <= today <= period.end_date:
            return today
    for period in candidates:
        if period.start_date >= original_date:
            return period.start_date
    raise ValueError("لا توجد فترة محاسبية مفتوحة يمكن تسجيل قيد العكس فيها")


def create_journal(
    db: Session,
    *,
    entry_number: str,
    entry_date,
    description: str,
    lines: list[dict],
    created_by: int | None = None,
    branch_id: int | None = None,
    status: str = "draft",
    fiscal_period_id: int | None = None,
) -> JournalEntry:
    if not entry_number or not str(entry_number).strip():
        raise ValueError("رقم القيد مطلوب")
    if not description or not str(description).strip():
        raise ValueError("وصف القيد مطلوب")
    if len(lines) < 2:
        raise ValueError("القيد يجب أن يحتوي على سطرين على الأقل")
    if status not in {"draft", "posted"}:
        raise ValueError("حالة القيد غير صحيحة")
    if db.scalar(select(JournalEntry.id).where(JournalEntry.entry_number == entry_number)):
        raise ValueError("رقم القيد مستخدم مسبقًا")

    period = _resolve_period(db, entry_date, branch_id, fiscal_period_id)

    total_debit = sum((Decimal(str(line.get("debit", 0))) for line in lines), Decimal("0"))
    total_credit = sum((Decimal(str(line.get("credit", 0))) for line in lines), Decimal("0"))
    if total_debit != total_credit:
        raise UnbalancedJournalError("القيد غير متوازن: إجمالي المدين يجب أن يساوي إجمالي الدائن")
    if total_debit <= 0:
        raise ValueError("يجب أن يكون للقيد مبلغ أكبر من صفر")

    validated_lines: list[dict] = []
    for line in lines:
        account_id = line.get("account_id")
        if not account_id:
            raise ValueError("كل سطر يجب أن يحتوي على حساب")
        account = db.get(Account, account_id)
        if not account or not account.is_active:
            raise ValueError("الحساب غير موجود أو غير نشط")
        if branch_id is not None and account.branch_id not in (None, branch_id):
            raise ValueError("الحساب تابع لفرع آخر")

        debit = Decimal(str(line.get("debit", 0)))
        credit = Decimal(str(line.get("credit", 0)))
        if debit < 0 or credit < 0 or (debit > 0 and credit > 0):
            raise ValueError("كل سطر يجب أن يكون مدينًا أو دائنًا فقط وبقيمة غير سالبة")

        dimension_id = line.get("dimension_id")
        if dimension_id is not None:
            dimension = db.get(AccountingDimension, dimension_id)
            if not dimension or not dimension.is_active:
                raise ValueError("البعد المحاسبي غير موجود أو غير نشط")
            if branch_id is not None and dimension.branch_id not in (None, branch_id):
                raise ValueError("البعد المحاسبي تابع لفرع آخر")

        validated_lines.append({
            "account_id": account_id,
            "dimension_id": dimension_id,
            "description": line.get("description"),
            "debit": debit,
            "credit": credit,
        })

    entry = JournalEntry(
        entry_number=entry_number,
        entry_date=entry_date,
        description=description,
        created_by=created_by,
        branch_id=branch_id,
        fiscal_period_id=period.id if period else fiscal_period_id,
        status=status,
        posted_at=datetime.utcnow() if status == "posted" else None,
    )
    db.add(entry)
    db.flush()

    for line in validated_lines:
        db.add(JournalLine(journal_entry_id=entry.id, **line))

    db.flush()
    db.add(AuditLog(
        user_id=created_by,
        action="post" if status == "posted" else "create",
        entity_type="journal_entry",
        entity_id=entry.id,
        details=json.dumps({"entry_number": entry.entry_number, "status": status}, ensure_ascii=False),
    ))
    return entry
