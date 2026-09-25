from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_permission
from app.db.session import get_db
from app.models.party import Party
from app.models.journal import JournalEntry, JournalLine
from app.models.travel import ProgramBooking, TravelProgram
from app.models.service_order import ServiceOrder
from app.models.voucher import Voucher
from app.models.user import User

router = APIRouter(prefix="/reports", tags=["تقارير الأطراف"])

SERVICE_LABELS = {
    "hajj": "الحج",
    "umrah": "العمرة",
    "flight": "الطيران",
    "bus": "الباصات",
    "visit": "الزيارات",
    "work_visa": "تأشيرات العمل",
}
ALL_SERVICES = {"all", *SERVICE_LABELS}


def _branch_ok(column, user: User):
    return (column == user.branch_id) | column.is_(None)


def _date_filter(stmt, column, from_date: date | None, to_date: date | None):
    if from_date:
        stmt = stmt.where(column >= from_date)
    if to_date:
        stmt = stmt.where(column <= to_date)
    return stmt


def _entry_rows(db: Session, entry_ids: set[int], party_account_id: int, user: User, from_date: date | None, to_date: date | None, service_type: str):
    if not entry_ids:
        return []
    stmt = (
        select(JournalLine, JournalEntry)
        .join(JournalEntry, JournalLine.journal_entry_id == JournalEntry.id)
        .where(
            JournalEntry.status == "posted",
            JournalLine.account_id == party_account_id,
            JournalEntry.id.in_(entry_ids),
        )
    )
    if user.branch_id is not None:
        stmt = stmt.where(_branch_ok(JournalEntry.branch_id, user))
    stmt = _date_filter(stmt, JournalEntry.entry_date, from_date, to_date)
    stmt = stmt.order_by(JournalEntry.entry_date, JournalEntry.id, JournalLine.id)
    rows = []
    for line, entry in db.execute(stmt).all():
        debit = Decimal(str(line.debit or 0))
        credit = Decimal(str(line.credit or 0))
        rows.append({
            "entry_id": entry.id,
            "entry_number": entry.entry_number,
            "entry_date": entry.entry_date,
            "description": line.description or entry.description,
            "service_type": service_type,
            "service_name": SERVICE_LABELS.get(service_type, service_type),
            "debit": debit,
            "credit": credit,
            "balance_delta": debit - credit,
        })
    return rows


def _linked_service_type(db: Session, voucher: Voucher) -> str | None:
    mapped = {
        "hajj_booking": "hajj",
        "umrah_booking": "umrah",
        "flight": "flight",
        "bus": "bus",
        "visit": "visit",
        "work_visa": "work_visa",
    }.get(voucher.linked_service_type)
    if mapped:
        return mapped
    if voucher.linked_service_type == "service_order":
        order = db.get(ServiceOrder, voucher.linked_service_id) if voucher.linked_service_id else None
        return order.service_type if order else None
    if voucher.linked_service_type == "visa_service":
        return "work_visa"
    return None


@router.get("/party/{party_id}/services")
def party_services_report(
    party_id: int,
    service_type: str = "all",
    from_date: date | None = None,
    to_date: date | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_permission(user, "reports.view", db)
    if service_type not in ALL_SERVICES:
        raise HTTPException(400, "نوع الخدمة غير مدعوم")

    party = db.get(Party, party_id)
    if not party:
        raise HTTPException(404, "الطرف غير موجود")
    if user.branch_id is not None and party.branch_id not in (None, user.branch_id):
        raise HTTPException(403, "الطرف تابع لفرع آخر")

    base = {
        "party_id": party.id,
        "party_name": party.name,
        "party_type": party.party_type,
        "service_type": service_type,
        "service_name": "كل الخدمات" if service_type == "all" else SERVICE_LABELS[service_type],
        "printed_by": user.full_name,
        "username": user.username,
        "branch_id": user.branch_id,
    }
    if party.account_id is None:
        return {**base, "rows": [], "total_debit": Decimal("0"), "total_credit": Decimal("0"), "balance": Decimal("0"),
                "warning": "لم يتم ربط الطرف بحساب محاسبي"}

    selected = set(SERVICE_LABELS) if service_type == "all" else {service_type}
    rows = []

    party_booking_filter = or_(
        ProgramBooking.agent_id == party.id,
        ProgramBooking.customer_id == party.id,
        ProgramBooking.supplier_id == party.id,
    )
    booking_stmt = (
        select(ProgramBooking.id, ProgramBooking.journal_entry_id, TravelProgram.program_type)
        .join(TravelProgram, ProgramBooking.program_id == TravelProgram.id)
        .where(
            party_booking_filter,
            ProgramBooking.journal_entry_id.is_not(None),
            TravelProgram.program_type.in_(list(selected & {"hajj", "umrah"})),
        )
    )
    if user.branch_id is not None:
        booking_stmt = booking_stmt.where(_branch_ok(ProgramBooking.branch_id, user))
    booking_map = {int(journal_id): program_type for _, journal_id, program_type in db.execute(booking_stmt).all()}
    for st in selected & {"hajj", "umrah"}:
        ids = {eid for eid, typ in booking_map.items() if typ == st}
        rows.extend(_entry_rows(db, ids, party.account_id, user, from_date, to_date, st))

    service_types = selected & {"flight", "bus", "visit", "work_visa"}
    if service_types:
        order_stmt = select(ServiceOrder.id, ServiceOrder.journal_entry_id, ServiceOrder.service_type).where(
            or_(ServiceOrder.agent_id == party.id, ServiceOrder.customer_id == party.id, ServiceOrder.supplier_id == party.id),
            ServiceOrder.journal_entry_id.is_not(None),
            ServiceOrder.service_type.in_(list(service_types)),
        )
        if user.branch_id is not None:
            order_stmt = order_stmt.where(_branch_ok(ServiceOrder.branch_id, user))
        for _, journal_id, st in db.execute(order_stmt).all():
            rows.extend(_entry_rows(db, {int(journal_id)}, party.account_id, user, from_date, to_date, st))

    voucher_stmt = select(Voucher).where(
        Voucher.status == "posted",
        Voucher.linked_service_id.is_not(None),
        or_(Voucher.source_account_id == party.account_id, Voucher.destination_account_id == party.account_id),
    )
    if user.branch_id is not None:
        voucher_stmt = voucher_stmt.where(_branch_ok(Voucher.branch_id, user))
    voucher_stmt = _date_filter(voucher_stmt, Voucher.voucher_date, from_date, to_date)
    for voucher in db.scalars(voucher_stmt.order_by(Voucher.voucher_date, Voucher.id)).all():
        mapped = _linked_service_type(db, voucher)
        if mapped not in selected:
            continue
        if voucher.journal_entry_id:
            journal_rows = _entry_rows(db, {int(voucher.journal_entry_id)}, party.account_id, user, from_date, to_date, mapped)
            if journal_rows:
                rows.extend(journal_rows)
                continue
        amount = Decimal(str(voucher.base_amount or voucher.amount or 0))
        debit = amount if voucher.destination_account_id == party.account_id else Decimal("0")
        credit = amount if voucher.source_account_id == party.account_id else Decimal("0")
        rows.append({
            "entry_id": voucher.journal_entry_id,
            "entry_number": voucher.voucher_number,
            "entry_date": voucher.voucher_date,
            "description": voucher.description,
            "service_type": mapped,
            "service_name": SERVICE_LABELS[mapped],
            "debit": debit,
            "credit": credit,
            "balance_delta": debit - credit,
        })

    rows.sort(key=lambda r: (r["entry_date"], str(r["entry_number"])))
    total_debit = sum((Decimal(str(r["debit"] or 0)) for r in rows), Decimal("0"))
    total_credit = sum((Decimal(str(r["credit"] or 0)) for r in rows), Decimal("0"))
    running = Decimal("0")
    for row in rows:
        running += Decimal(str(row["balance_delta"] or 0))
        row["balance"] = running

    return {
        **base,
        "rows": rows,
        "total_debit": total_debit,
        "total_credit": total_credit,
        "balance": running,
    }
