from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.accounting.journal_service import create_journal
from app.models.account import Account
from app.models.journal import JournalEntry
from app.models.voucher import Voucher

VALID_TYPES = {"receipt", "payment", "transfer"}


def create_voucher(db: Session, *, voucher_number: str, voucher_type: str, voucher_date: date,
                   amount: Decimal, description: str, source_account_id: int | None,
                   destination_account_id: int | None, created_by: int | None = None) -> Voucher:
    if voucher_type not in VALID_TYPES:
        raise ValueError("نوع السند غير مدعوم")
    amount = Decimal(str(amount))
    if amount <= 0:
        raise ValueError("مبلغ السند يجب أن يكون أكبر من صفر")
    if not source_account_id or not destination_account_id:
        raise ValueError("يجب تحديد حساب المصدر وحساب الوجهة")
    if source_account_id == destination_account_id:
        raise ValueError("لا يمكن أن يكون حساب المصدر والوجهة واحدًا")
    for account_id in (source_account_id, destination_account_id):
        account = db.get(Account, account_id)
        if not account or not account.is_active:
            raise ValueError("أحد الحسابات المحددة غير موجود أو غير نشط")

    voucher = Voucher(
        voucher_number=voucher_number, voucher_type=voucher_type, voucher_date=voucher_date,
        description=description, amount=amount, source_account_id=source_account_id,
        destination_account_id=destination_account_id, created_by=created_by,
        status="draft", created_at=datetime.utcnow(),
    )
    db.add(voucher)
    db.flush()
    return voucher


def _journal_lines(voucher: Voucher) -> list[dict]:
    # المصدر يُنقص (دائن)، والوجهة تُزاد (مدين).
    return [
        {"account_id": voucher.destination_account_id, "debit": voucher.amount},
        {"account_id": voucher.source_account_id, "credit": voucher.amount},
    ]


def post_voucher(db: Session, voucher: Voucher) -> Voucher:
    if voucher.status != "draft":
        raise ValueError("لا يمكن ترحيل سند ليس في حالة مسودة")
    entry = create_journal(
        db, entry_number=f"JV-{voucher.voucher_number}", entry_date=voucher.voucher_date,
        description=voucher.description, lines=_journal_lines(voucher),
        created_by=voucher.created_by, status="posted",
    )
    entry.posted_at = datetime.utcnow()
    voucher.journal_entry_id = entry.id
    voucher.status = "posted"
    voucher.posted_at = datetime.utcnow()
    db.flush()
    return voucher


def cancel_voucher(db: Session, voucher: Voucher) -> Voucher:
    if voucher.status != "posted" or not voucher.journal_entry_id:
        raise ValueError("لا يمكن إلغاء سند غير مرحّل")
    original = db.get(JournalEntry, voucher.journal_entry_id)
    if not original:
        raise ValueError("القيد المرتبط بالسند غير موجود")
    lines = [
        {"account_id": line.account_id, "debit": line.credit, "credit": line.debit}
        for line in original.lines
    ]
    reversal = create_journal(
        db, entry_number=f"REV-{voucher.voucher_number}", entry_date=voucher.voucher_date,
        description=f"عكس السند {voucher.voucher_number}: {voucher.description}",
        lines=lines, created_by=voucher.created_by, status="posted",
    )
    reversal.posted_at = datetime.utcnow()
    voucher.status = "cancelled"
    voucher.posted_at = datetime.utcnow()
    db.flush()
    return voucher
