from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.accounting.journal_service import create_journal
from app.models.account import Account
from app.models.currency import Currency
from app.models.exchange_rate import ExchangeRate
from app.models.journal import JournalEntry
from app.models.voucher import Voucher

VALID_TYPES = {"receipt", "payment", "transfer"}


def create_voucher(db: Session, *, voucher_number: str, voucher_type: str, voucher_date: date,
                   amount: Decimal, description: str, source_account_id: int | None,
                   destination_account_id: int | None, currency_id: int | None = None, exchange_rate: Decimal | None = None, created_by: int | None = None) -> Voucher:
    voucher_number = voucher_number.strip()\n    description = description.strip()\n    if not voucher_number:\n        raise ValueError("رقم السند مطلوب")\n    if not description:\n        raise ValueError("بيان السند مطلوب")\n    if voucher_type not in VALID_TYPES:
        raise ValueError("نوع السند غير مدعوم")
    amount = Decimal(str(amount))
    if amount <= 0:
        raise ValueError("مبلغ السند يجب أن يكون أكبر من صفر")
    if not source_account_id or not destination_account_id:
        raise ValueError("يجب تحديد حساب المصدر وحساب الوجهة")
    if source_account_id == destination_account_id:
        raise ValueError("لا يمكن أن يكون حساب المصدر والوجهة واحدًا")
    if db.query(Voucher).filter(Voucher.voucher_number == voucher_number).first():\n        raise ValueError("رقم السند مستخدم مسبقًا")\n    for account_id in (source_account_id, destination_account_id):
        account = db.get(Account, account_id)
        if not account or not account.is_active:
            raise ValueError("أحد الحسابات المحددة غير موجود أو غير نشط")

    if currency_id is not None:
        currency = db.get(Currency, currency_id)
        if not currency or not currency.is_active: raise ValueError("العملة غير موجودة أو غير نشطة")
        if currency.is_base: exchange_rate = Decimal("1")
        elif exchange_rate is None:
            rate = db.query(ExchangeRate).filter(ExchangeRate.currency_id == currency_id).order_by(ExchangeRate.effective_at.desc()).first()
            if not rate: raise ValueError("يجب تحديد سعر صرف للعملة")
            exchange_rate = rate.rate_to_base
        if Decimal(str(exchange_rate)) <= 0: raise ValueError("سعر الصرف يجب أن يكون أكبر من صفر")
    voucher = Voucher(
        voucher_number=voucher_number, voucher_type=voucher_type, voucher_date=voucher_date,
        description=description, amount=amount, source_account_id=source_account_id,
        destination_account_id=destination_account_id, created_by=created_by,
        status="draft", created_at=datetime.utcnow(), currency_id=currency_id, exchange_rate=exchange_rate,
        base_amount=amount * Decimal(str(exchange_rate)) if exchange_rate is not None else amount,
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
