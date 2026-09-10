from decimal import Decimal
from sqlalchemy.orm import Session

from app.models.journal import JournalEntry, JournalLine


class UnbalancedJournalError(ValueError):
    pass


def create_journal(
    db: Session,
    *,
    entry_number: str,
    entry_date,
    description: str,
    lines: list[dict],
    created_by: int | None = None,
    status: str = "draft",
) -> JournalEntry:
    if len(lines) < 2:
        raise ValueError("القيد يجب أن يحتوي على سطرين على الأقل")

    total_debit = sum((Decimal(str(line.get("debit", 0))) for line in lines), Decimal("0"))
    total_credit = sum((Decimal(str(line.get("credit", 0))) for line in lines), Decimal("0"))
    if total_debit != total_credit:
        raise UnbalancedJournalError("القيد غير متوازن: إجمالي المدين يجب أن يساوي إجمالي الدائن")
    if total_debit <= 0:
        raise ValueError("يجب أن يكون للقيد مبلغ أكبر من صفر")

    entry = JournalEntry(
        entry_number=entry_number,
        entry_date=entry_date,
        description=description,
        created_by=created_by,
        status=status,
    )
    db.add(entry)
    db.flush()

    for line in lines:
        debit = Decimal(str(line.get("debit", 0)))
        credit = Decimal(str(line.get("credit", 0)))
        if debit < 0 or credit < 0 or (debit > 0 and credit > 0):
            raise ValueError("كل سطر يجب أن يكون مدينًا أو دائنًا فقط وبقيمة غير سالبة")
        db.add(JournalLine(
            journal_entry_id=entry.id,
            account_id=line["account_id"],
            description=line.get("description"),
            debit=debit,
            credit=credit,
        ))

    db.flush()
    return entry
