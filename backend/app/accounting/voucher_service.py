from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.accounting.journal_service import create_journal
from app.models.account import Account
from app.models.currency import Currency
from app.models.exchange_rate import ExchangeRate
from app.models.financial import FinancialAccount
from app.models.journal import JournalEntry
from app.models.party import Party
from app.models.service_order import ServiceOrder
from app.models.travel import ProgramBooking
from app.models.voucher import Voucher

VALID_TYPES = {"receipt", "payment", "transfer"}
PAYMENT_LINK_TYPES = {"hajj_booking", "umrah_booking", "service_order"}


def _financial_account_for_ledger(db: Session, ledger_account_id: int) -> FinancialAccount | None:
    return db.scalar(select(FinancialAccount).where(FinancialAccount.ledger_account_id == ledger_account_id, FinancialAccount.active.is_(True)))


def create_voucher(db: Session, *, voucher_number: str, voucher_type: str, voucher_date: date, amount: Decimal,
                   description: str, source_account_id: int | None, destination_account_id: int | None,
                   currency_id: int | None = None, exchange_rate: Decimal | None = None,
                   created_by: int | None = None, branch_id: int | None = None,
                   linked_service_type: str | None = None, linked_service_id: int | None = None,
                   manual_voucher_number: str | None = None) -> Voucher:
    voucher_number = voucher_number.strip()
    description = description.strip()
    manual_voucher_number = (manual_voucher_number or "").strip() or None
    if not voucher_number:
        raise ValueError("رقم السند النظامي مطلوب")
    if not description:
        raise ValueError("بيان السند مطلوب")
    if voucher_type not in VALID_TYPES:
        raise ValueError("نوع السند غير مدعوم")
    amount = Decimal(str(amount))
    if amount <= 0:
        raise ValueError("مبلغ السند يجب أن يكون أكبر من صفر")
    if not source_account_id or not destination_account_id:
        raise ValueError("يجب تحديد حساب المصدر وحساب الوجهة")
    if source_account_id == destination_account_id:
        raise ValueError("لا يمكن أن يكون حساب المصدر والوجهة واحدًا")
    if db.query(Voucher).filter(Voucher.voucher_number == voucher_number).first():
        raise ValueError("رقم السند النظامي مستخدم مسبقًا")
    if manual_voucher_number and db.query(Voucher).filter(Voucher.manual_voucher_number == manual_voucher_number).first():
        raise ValueError("رقم السند اليدوي مستخدم مسبقًا")

    source = db.get(Account, source_account_id)
    destination = db.get(Account, destination_account_id)
    if not source or not source.is_active or not destination or not destination.is_active:
        raise ValueError("أحد الحسابات المحددة غير موجود أو غير نشط")
    source_financial = _financial_account_for_ledger(db, source_account_id)
    destination_financial = _financial_account_for_ledger(db, destination_account_id)
    if voucher_type == "transfer":
        if not source_financial or not destination_financial:
            raise ValueError("سند التحويل يجب أن يكون بين صندوق أو بنك أو محفظة")
    elif voucher_type == "receipt":
        if not destination_financial:
            raise ValueError("سند القبض يجب أن يكون حساب الاستلام صندوقًا أو بنكًا أو محفظة")
    elif voucher_type == "payment":
        if not source_financial:
            raise ValueError("سند الصرف يجب أن يكون حساب الدفع صندوقًا أو بنكًا أو محفظة")

    if currency_id is not None:
        currency = db.get(Currency, currency_id)
        if not currency or not currency.is_active:
            raise ValueError("العملة غير موجودة أو غير نشطة")
        if currency.is_base:
            exchange_rate = Decimal("1")
        elif exchange_rate is None:
            rate = db.query(ExchangeRate).filter(ExchangeRate.currency_id == currency_id).order_by(ExchangeRate.effective_at.desc()).first()
            if not rate:
                raise ValueError("يجب تحديد سعر صرف للعملة")
            exchange_rate = rate.rate_to_base
        if Decimal(str(exchange_rate)) <= 0:
            raise ValueError("سعر الصرف يجب أن يكون أكبر من صفر")

    base_amount = amount * Decimal(str(exchange_rate)) if exchange_rate is not None else amount
    voucher = Voucher(
        voucher_number=voucher_number,
        manual_voucher_number=manual_voucher_number,
        voucher_type=voucher_type,
        voucher_date=voucher_date,
        description=description,
        amount=amount,
        source_account_id=source_account_id,
        destination_account_id=destination_account_id,
        created_by=created_by,
        branch_id=branch_id,
        linked_service_type=linked_service_type,
        linked_service_id=linked_service_id,
        status="draft",
        created_at=datetime.utcnow(),
        currency_id=currency_id,
        exchange_rate=exchange_rate,
        base_amount=base_amount,
    )
    db.add(voucher)
    db.flush()
    return voucher


def _journal_lines(voucher: Voucher) -> list[dict]:
    posted_amount = voucher.base_amount or voucher.amount
    return [
        {"account_id": voucher.destination_account_id, "debit": posted_amount},
        {"account_id": voucher.source_account_id, "credit": posted_amount},
    ]


def _get_linked(db: Session, voucher: Voucher):
    if not voucher.linked_service_type or voucher.linked_service_id is None:
        return None
    if voucher.linked_service_type in {"hajj_booking", "umrah_booking"}:
        booking = db.get(ProgramBooking, voucher.linked_service_id)
        if not booking:
            raise ValueError("الخدمة المرتبطة بالسند غير موجودة")
        from app.models.travel import TravelProgram
        program_type = db.scalar(select(TravelProgram.program_type).where(TravelProgram.id == booking.program_id))
        expected = "hajj" if voucher.linked_service_type == "hajj_booking" else "umrah"
        if program_type != expected:
            label = "الحج" if expected == "hajj" else "العمرة"
            raise ValueError(f"نوع الخدمة لا يطابق حجز {label}")
        return booking
    if voucher.linked_service_type == "service_order":
        row = db.get(ServiceOrder, voucher.linked_service_id)
        if not row:
            raise ValueError("الخدمة المرتبطة بالسند غير موجودة")
        return row
    return None


def _apply_service_receipt(db: Session, voucher: Voucher, amount: Decimal, reverse: bool = False) -> None:
    if voucher.voucher_type != "receipt" or voucher.linked_service_type not in PAYMENT_LINK_TYPES:
        return
    row = _get_linked(db, voucher)
    if row is None:
        return
    delta = -amount if reverse else amount
    new_paid = Decimal(str(row.paid_amount or 0)) + delta
    sale = Decimal(str(row.sale_price))
    if new_paid < 0:
        raise ValueError("لا يمكن عكس السند لأن المدفوع سيصبح سالبًا")
    if new_paid > sale:
        raise ValueError("مبلغ سند القبض يتجاوز المتبقي على الخدمة")
    row.paid_amount = new_paid
    row.remaining_amount = sale - new_paid


def _apply_supplier_payment(db: Session, voucher: Voucher, amount: Decimal, reverse: bool = False) -> None:
    if voucher.voucher_type != "payment" or voucher.linked_service_type not in PAYMENT_LINK_TYPES:
        return
    row = _get_linked(db, voucher)
    if row is None:
        return
    delta = -amount if reverse else amount
    current = Decimal(str(getattr(row, "supplier_paid_amount", 0) or 0))
    cost = Decimal(str(getattr(row, "supplier_cost", 0) or 0))
    new_paid = current + delta
    if new_paid < 0:
        raise ValueError("لا يمكن عكس السند لأن مدفوع المورد سيصبح سالبًا")
    if new_paid > cost:
        raise ValueError("مبلغ سند الصرف يتجاوز تكلفة المورد المتبقية على الخدمة")
    row.supplier_paid_amount = new_paid


def _validate_linked_voucher(db: Session, voucher: Voucher) -> None:
    if not voucher.linked_service_type or voucher.linked_service_id is None:
        return
    if voucher.linked_service_type not in PAYMENT_LINK_TYPES:
        raise ValueError("نوع الخدمة المرتبطة غير مدعوم")
    if voucher.voucher_type not in {"receipt", "payment"}:
        raise ValueError("ربط الخدمة متاح حاليًا مع سندات القبض والصرف فقط")

    row = _get_linked(db, voucher)
    if getattr(row, "journal_entry_id", None) is None:
        raise ValueError("يجب ترحيل الخدمة قبل ربط سند مالي بها")
    if getattr(row, "status", None) == "cancelled":
        raise ValueError("لا يمكن ربط سند بخدمة ملغاة")

    amount = Decimal(str(voucher.base_amount or voucher.amount))
    if voucher.voucher_type == "receipt":
        party_id = getattr(row, "agent_id", None) or getattr(row, "customer_id", None)
        party = db.get(Party, party_id) if party_id else None
        if not party or party.account_id is None:
            raise ValueError("الطرف المالي للخدمة غير مربوط بحساب محاسبي")
        if voucher.source_account_id != party.account_id:
            raise ValueError("حساب مصدر سند القبض يجب أن يكون حساب الوكيل أو العميل المرتبط بالخدمة")
        if amount > Decimal(str(row.remaining_amount or 0)):
            raise ValueError("مبلغ التحصيل يتجاوز المتبقي على الخدمة")
    else:
        supplier_id = getattr(row, "supplier_id", None)
        supplier = db.get(Party, supplier_id) if supplier_id else None
        if not supplier or supplier.account_id is None:
            raise ValueError("مورد الخدمة غير مربوط بحساب محاسبي")
        if voucher.destination_account_id != supplier.account_id:
            raise ValueError("حساب وجهة سند الصرف يجب أن يكون حساب المورد المرتبط بالخدمة")
        supplier_cost = Decimal(str(getattr(row, "supplier_cost", 0) or 0))
        supplier_paid = Decimal(str(getattr(row, "supplier_paid_amount", 0) or 0))
        if supplier_cost <= 0:
            raise ValueError("لا توجد تكلفة مورد مستحقة لهذه الخدمة")
        if amount > supplier_cost - supplier_paid:
            raise ValueError("مبلغ الصرف يتجاوز المتبقي للمورد على الخدمة")


def post_voucher(db: Session, voucher: Voucher) -> Voucher:
    if voucher.status != "draft":
        raise ValueError("لا يمكن ترحيل سند ليس في حالة مسودة")
    _validate_linked_voucher(db, voucher)
    entry = create_journal(
        db,
        entry_number=f"JV-{voucher.voucher_number}",
        entry_date=voucher.voucher_date,
        description=voucher.description,
        lines=_journal_lines(voucher),
        created_by=voucher.created_by,
        branch_id=voucher.branch_id,
        status="posted",
    )
    entry.posted_at = datetime.utcnow()
    voucher.journal_entry_id = entry.id
    voucher.status = "posted"
    voucher.posted_at = datetime.utcnow()
    amount = voucher.base_amount or voucher.amount
    _apply_service_receipt(db, voucher, amount)
    _apply_supplier_payment(db, voucher, amount)
    db.flush()
    return voucher


def cancel_voucher(db: Session, voucher: Voucher) -> Voucher:
    if voucher.status != "posted" or not voucher.journal_entry_id:
        raise ValueError("لا يمكن إلغاء سند غير مرحّل")
    original = db.get(JournalEntry, voucher.journal_entry_id)
    if not original:
        raise ValueError("القيد المرتبط بالسند غير موجود")
    lines = [{"account_id": line.account_id, "debit": line.credit, "credit": line.debit} for line in original.lines]
    reversal = create_journal(
        db,
        entry_number=f"REV-{voucher.voucher_number}",
        entry_date=voucher.voucher_date,
        description=f"عكس السند {voucher.voucher_number}: {voucher.description}",
        lines=lines,
        created_by=voucher.created_by,
        branch_id=voucher.branch_id,
        status="posted",
    )
    reversal.posted_at = datetime.utcnow()
    amount = voucher.base_amount or voucher.amount
    _apply_service_receipt(db, voucher, amount, reverse=True)
    _apply_supplier_payment(db, voucher, amount, reverse=True)
    voucher.status = "cancelled"
    voucher.posted_at = datetime.utcnow()
    db.flush()
    return voucher
