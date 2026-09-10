from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.accounting.journal_service import create_journal
from app.models.account import Account
from app.models.voucher import Voucher


VALID_TYPES = {"receipt", "payment", "transfer"}


def create_voucher(
    db: Session,
    *,
    voucher_number: str,
    voucher_type: str,
    voucher_date: date,
    amount: Decimal,
    description: str,
    source_account_id: int | None,
    destination_account_id: int | None,
    created_by: int | None = None,
) -> Voucher:
    if voucher_type not in VALID_TYPES:
        raise ValueError("نوع السند غير مدعوم")
    amount = Decimal(str(amount))
    if amount <= 0:
        raise ValueError("مبلغ السند يجب أن يكون أكبر من صفر")
    if voucher_type == "transfer" and (not source_account_id or not destination_account_id):
        raise ValueError("سند التحويل يتطلب حساب المصدر وحساب الوجهة")
    if voucher_type != "transfer" and not destination_account_id:
        raise ValueError("السند المالي يتطلب حساب الوجهة")

    if source_account_id and not db.get(Account, source_account_id):
        raise ValueError("حساب المصدر غير موجود")
    if destination_account_id and not db.get(Account, destination_account_id):
        raise ValueError("حساب الوجهة غير موجود")

    voucher = Voucher(
        voucher_number=voucher_number,
        voucher_type=voucher_type,
        voucher_date=voucher_date,
        description=description,
        amount=amount,
        source_account_id=source_account_id,
        destination_account_id=destination_account_id,
        created_by=created_by,
        status="draft",
        created_at=datetime.utcnow(),
    )
    db.add(voucher)
    db.flush()
    return voucher


def post_voucher(db: Session, voucher: Voucher) -> Voucher:
    if voucher.status != "draft":
        raise ValueError("لا يمكن ترحيل سند ليس في حالة مسودة")

    if voucher.voucher_type == "receipt":
        lines = [
            {"account_id": voucher.destination_account_id, "debit": voucher.amount},
            {"account_id": voucher.source_account_id, "credit": voucher.amount},
        ]
    elif voucher.voucher_type == "payment":
        lines = [
            {"account_id": voucher.destination_account_id, "debit": voucher.amount},
            {"account_id": voucher.source_account_id, "credit": voucher.amount},
        ]
    else:
        lines = [
            {"account_id": voucher.destination_account_id, "debit": voucher.amount},
            {"account_id": voucher.source_account_id, "credit": voucher.amount},
        ]

    if any(line["account_id"] is None for line in lines):
        raise ValueError("لا يمكن ترحيل السند قبل تحديد الحسابات")

    entry = create_journal(
        db,
        entry_number=f"JV-{voucher.voucher_number}",
        entry_date=voucher.voucher_date,
        description=voucher.description,
        lines=lines,
        created_by=voucher.created_by,
        status="posted",
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
    voucher.status = "cancelled"
    db.flush()
    return voucher
