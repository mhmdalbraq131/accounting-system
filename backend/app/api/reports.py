from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_permission
from app.db.session import get_db
from app.models.account import Account
from app.models.expense import Expense
from app.models.financial import FinancialAccount
from app.models.journal import JournalEntry, JournalLine
from app.models.party import Party
from app.models.travel import ProgramBooking, VisaService
from app.models.user import User

router = APIRouter(prefix="/reports", tags=["التقارير"])


def branch_condition(col, user: User):
    return True if user.branch_id is None else ((col == user.branch_id) | col.is_(None))


def apply_dates(stmt, col, from_date: date | None, to_date: date | None):
    if from_date:
        stmt = stmt.where(col >= from_date)
    if to_date:
        stmt = stmt.where(col <= to_date)
    return stmt


def _posted_entries(db: Session, user: User, from_date: date | None = None, to_date: date | None = None):
    stmt = select(JournalEntry).where(JournalEntry.status == "posted")
    if user.branch_id is not None:
        stmt = stmt.where((JournalEntry.branch_id == user.branch_id) | JournalEntry.branch_id.is_(None))
    stmt = apply_dates(stmt, JournalEntry.entry_date, from_date, to_date)
    return stmt.order_by(JournalEntry.entry_date, JournalEntry.id)


@router.get("/financial-summary")
def financial_summary(
    from_date: date | None = None,
    to_date: date | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_permission(user, "reports.view", db)
    # The summary is intentionally based on posted accounting entries.
    base = select(JournalLine).join(JournalEntry, JournalLine.journal_entry_id == JournalEntry.id).join(Account, JournalLine.account_id == Account.id)
    base = base.where(JournalEntry.status == "posted")
    if user.branch_id is not None:
        base = base.where((JournalEntry.branch_id == user.branch_id) | JournalEntry.branch_id.is_(None))
    if from_date:
        base = base.where(JournalEntry.entry_date >= from_date)
    if to_date:
        base = base.where(JournalEntry.entry_date <= to_date)

    revenue = db.scalar(
        select(func.coalesce(func.sum(JournalLine.credit - JournalLine.debit), 0))
        .join(JournalEntry, JournalLine.journal_entry_id == JournalEntry.id)
        .join(Account, JournalLine.account_id == Account.id)
        .where(JournalEntry.status == "posted", Account.account_type == "revenue")
        .where(*([] if user.branch_id is None else [((JournalEntry.branch_id == user.branch_id) | JournalEntry.branch_id.is_(None))]))
        .where(*([] if from_date is None else [JournalEntry.entry_date >= from_date]))
        .where(*([] if to_date is None else [JournalEntry.entry_date <= to_date]))
    ) or 0
    expenses = db.scalar(
        select(func.coalesce(func.sum(JournalLine.debit - JournalLine.credit), 0))
        .join(JournalEntry, JournalLine.journal_entry_id == JournalEntry.id)
        .join(Account, JournalLine.account_id == Account.id)
        .where(JournalEntry.status == "posted", Account.account_type == "expense")
        .where(*([] if user.branch_id is None else [((JournalEntry.branch_id == user.branch_id) | JournalEntry.branch_id.is_(None))]))
        .where(*([] if from_date is None else [JournalEntry.entry_date >= from_date]))
        .where(*([] if to_date is None else [JournalEntry.entry_date <= to_date]))
    ) or 0

    revenue = Decimal(str(revenue))
    expenses = Decimal(str(expenses))
    return {
        "from_date": from_date,
        "to_date": to_date,
        "revenue": revenue,
        "service_cost": Decimal("0"),
        "gross_profit": revenue,
        "expenses": expenses,
        "net_profit": revenue - expenses,
        "source": "posted_journals",
        "printed_by": user.full_name,
        "username": user.username,
        "branch_id": user.branch_id,
    }


@router.get("/journal")
def journal_report(
    from_date: date | None = None,
    to_date: date | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_permission(user, "reports.view", db)
    entries = db.scalars(_posted_entries(db, user, from_date, to_date)).all()
    return [
        {
            "id": entry.id,
            "entry_number": entry.entry_number,
            "entry_date": entry.entry_date,
            "description": entry.description,
            "branch_id": entry.branch_id,
            "created_by": entry.created_by,
            "posted_at": entry.posted_at,
            "lines": [
                {
                    "account_id": line.account_id,
                    "description": line.description,
                    "debit": line.debit,
                    "credit": line.credit,
                }
                for line in entry.lines
            ],
        }
        for entry in entries
    ]


@router.get("/ledger/{account_id}")
def ledger_report(
    account_id: int,
    from_date: date | None = None,
    to_date: date | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_permission(user, "reports.view", db)
    account = db.get(Account, account_id)
    if not account or not account.is_active:
        raise HTTPException(404, "الحساب غير موجود أو غير نشط")
    if user.branch_id is not None and account.branch_id not in (None, user.branch_id):
        raise HTTPException(403, "الحساب تابع لفرع آخر")

    opening = Decimal(str(account.opening_balance or 0))
    pre_stmt = (
        select(func.coalesce(func.sum(JournalLine.debit), 0), func.coalesce(func.sum(JournalLine.credit), 0))
        .join(JournalEntry, JournalLine.journal_entry_id == JournalEntry.id)
        .where(JournalEntry.status == "posted", JournalLine.account_id == account_id)
    )
    if user.branch_id is not None:
        pre_stmt = pre_stmt.where((JournalEntry.branch_id == user.branch_id) | JournalEntry.branch_id.is_(None))
    if from_date:
        pre_stmt = pre_stmt.where(JournalEntry.entry_date < from_date)
    pre_debit, pre_credit = db.execute(pre_stmt).one()
    running = opening + Decimal(str(pre_debit or 0)) - Decimal(str(pre_credit or 0))

    stmt = (
        select(JournalLine, JournalEntry)
        .join(JournalEntry, JournalLine.journal_entry_id == JournalEntry.id)
        .where(JournalEntry.status == "posted", JournalLine.account_id == account_id)
    )
    if user.branch_id is not None:
        stmt = stmt.where((JournalEntry.branch_id == user.branch_id) | JournalEntry.branch_id.is_(None))
    stmt = apply_dates(stmt, JournalEntry.entry_date, from_date, to_date).order_by(JournalEntry.entry_date, JournalEntry.id, JournalLine.id)

    rows = []
    for line, entry in db.execute(stmt).all():
        running += Decimal(str(line.debit)) - Decimal(str(line.credit))
        rows.append({
            "entry_id": entry.id,
            "entry_number": entry.entry_number,
            "entry_date": entry.entry_date,
            "description": line.description or entry.description,
            "debit": line.debit,
            "credit": line.credit,
            "balance": running,
        })

    return {
        "account_id": account.id,
        "code": account.code,
        "name_ar": account.name_ar,
        "account_type": account.account_type,
        "opening_balance": opening,
        "rows": rows,
        "closing_balance": running,
        "printed_by": user.full_name,
        "username": user.username,
    }


@router.get("/trial-balance")
def trial_balance(
    from_date: date | None = None,
    to_date: date | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_permission(user, "reports.view", db)
    accounts_stmt = select(Account).where(Account.is_active.is_(True))
    if user.branch_id is not None:
        accounts_stmt = accounts_stmt.where((Account.branch_id == user.branch_id) | Account.branch_id.is_(None))
    accounts = db.scalars(accounts_stmt.order_by(Account.code)).all()

    rows = []
    total_debit = Decimal("0")
    total_credit = Decimal("0")
    for account in accounts:
        stmt = (
            select(func.coalesce(func.sum(JournalLine.debit), 0), func.coalesce(func.sum(JournalLine.credit), 0))
            .join(JournalEntry, JournalLine.journal_entry_id == JournalEntry.id)
            .where(JournalEntry.status == "posted", JournalLine.account_id == account.id)
        )
        if user.branch_id is not None:
            stmt = stmt.where((JournalEntry.branch_id == user.branch_id) | JournalEntry.branch_id.is_(None))
        stmt = apply_dates(stmt, JournalEntry.entry_date, from_date, to_date)
        debit, credit = db.execute(stmt).one()
        net = Decimal(str(account.opening_balance or 0)) + Decimal(str(debit or 0)) - Decimal(str(credit or 0))
        debit_balance = net if net > 0 else Decimal("0")
        credit_balance = -net if net < 0 else Decimal("0")
        total_debit += debit_balance
        total_credit += credit_balance
        rows.append({
            "account_id": account.id,
            "code": account.code,
            "name_ar": account.name_ar,
            "account_type": account.account_type,
            "debit": debit_balance,
            "credit": credit_balance,
        })
    return {
        "from_date": from_date,
        "to_date": to_date,
        "rows": rows,
        "total_debit": total_debit,
        "total_credit": total_credit,
        "balanced": total_debit == total_credit,
        "printed_by": user.full_name,
        "username": user.username,
        "branch_id": user.branch_id,
    }


@router.get("/profit-loss")
def profit_loss(
    from_date: date | None = None,
    to_date: date | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = (
        select(Account.id, Account.code, Account.name_ar, Account.account_type,
               func.coalesce(func.sum(JournalLine.debit), 0).label("debit"),
               func.coalesce(func.sum(JournalLine.credit), 0).label("credit"))
        .join(JournalLine, JournalLine.account_id == Account.id)
        .join(JournalEntry, JournalLine.journal_entry_id == JournalEntry.id)
        .where(JournalEntry.status == "posted", Account.account_type.in_(["revenue", "expense"]))
        .group_by(Account.id, Account.code, Account.name_ar, Account.account_type)
        .order_by(Account.code)
    )
    if user.branch_id is not None:
        stmt = stmt.where((Account.branch_id == user.branch_id) | Account.branch_id.is_(None))
        stmt = stmt.where((JournalEntry.branch_id == user.branch_id) | JournalEntry.branch_id.is_(None))
    stmt = apply_dates(stmt, JournalEntry.entry_date, from_date, to_date)

    revenue_rows = []
    expense_rows = []
    revenue_total = Decimal("0")
    expense_total = Decimal("0")
    for account_id, code, name_ar, account_type, debit, credit in db.execute(stmt).all():
        amount = Decimal(str((credit - debit) if account_type == "revenue" else (debit - credit)))
        row = {"account_id": account_id, "code": code, "name_ar": name_ar, "amount": amount}
        if account_type == "revenue":
            revenue_rows.append(row)
            revenue_total += amount
        else:
            expense_rows.append(row)
            expense_total += amount
    return {
        "from_date": from_date,
        "to_date": to_date,
        "revenue": revenue_rows,
        "expenses": expense_rows,
        "total_revenue": revenue_total,
        "total_expenses": expense_total,
        "net_profit": revenue_total - expense_total,
        "printed_by": user.full_name,
        "username": user.username,
    }


@router.get("/cash-movement")
def cash_movement(
    from_date: date | None = None,
    to_date: date | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = select(FinancialAccount).where(FinancialAccount.is_active.is_(True))
    if user.branch_id is not None:
        stmt = stmt.where((FinancialAccount.branch_id == user.branch_id) | FinancialAccount.branch_id.is_(None))
    financial_accounts = db.scalars(stmt.order_by(FinancialAccount.name)).all()

    rows = []
    for fa in financial_accounts:
        q = (
            select(func.coalesce(func.sum(JournalLine.debit), 0), func.coalesce(func.sum(JournalLine.credit), 0))
            .join(JournalEntry, JournalLine.journal_entry_id == JournalEntry.id)
            .where(JournalEntry.status == "posted", JournalLine.account_id == fa.ledger_account_id)
        )
        if user.branch_id is not None:
            q = q.where((JournalEntry.branch_id == user.branch_id) | JournalEntry.branch_id.is_(None))
        q = apply_dates(q, JournalEntry.entry_date, from_date, to_date)
        debit, credit = db.execute(q).one()
        movement = Decimal(str(debit or 0)) - Decimal(str(credit or 0))
        rows.append({
            "financial_account_id": fa.id,
            "name": fa.name,
            "account_type": fa.account_type,
            "currency_id": fa.currency_id,
            "opening_balance": fa.opening_balance,
            "debit": debit,
            "credit": credit,
            "net_movement": movement,
            "closing_balance": Decimal(str(fa.opening_balance or 0)) + movement,
            "branch_id": fa.branch_id,
        })
    return {
        "from_date": from_date,
        "to_date": to_date,
        "rows": rows,
        "printed_by": user.full_name,
        "username": user.username,
        "branch_id": user.branch_id,
    }


@router.get("/party/{party_id}")
def party_report(
    party_id: int,
    from_date: date | None = None,
    to_date: date | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    party = db.get(Party, party_id)
    if not party:
        raise HTTPException(404, "الطرف غير موجود")
    if user.branch_id is not None and party.branch_id not in (None, user.branch_id):
        raise HTTPException(403, "الطرف تابع لفرع آخر")
    if party.account_id is None:
        return {
            "party_id": party.id,
            "party_name": party.name,
            "party_type": party.party_type,
            "total_debit": 0,
            "total_credit": 0,
            "balance": 0,
            "rows": [],
            "warning": "لم يتم ربط الطرف بحساب محاسبي",
            "printed_by": user.full_name,
            "username": user.username,
            "branch_id": user.branch_id,
        }

    stmt = (
        select(JournalLine, JournalEntry)
        .join(JournalEntry, JournalLine.journal_entry_id == JournalEntry.id)
        .where(JournalEntry.status == "posted", JournalLine.account_id == party.account_id)
    )
    if user.branch_id is not None:
        stmt = stmt.where((JournalEntry.branch_id == user.branch_id) | JournalEntry.branch_id.is_(None))
    stmt = apply_dates(stmt, JournalEntry.entry_date, from_date, to_date).order_by(JournalEntry.entry_date, JournalEntry.id, JournalLine.id)

    rows = []
    debit_total = Decimal("0")
    credit_total = Decimal("0")
    running = Decimal("0")
    for line, entry in db.execute(stmt).all():
        debit_total += Decimal(str(line.debit))
        credit_total += Decimal(str(line.credit))
        running += Decimal(str(line.debit)) - Decimal(str(line.credit))
        rows.append({
            "entry_id": entry.id,
            "entry_number": entry.entry_number,
            "entry_date": entry.entry_date,
            "description": line.description or entry.description,
            "debit": line.debit,
            "credit": line.credit,
            "balance": running,
        })
    return {
        "party_id": party.id,
        "party_name": party.name,
        "party_type": party.party_type,
        "account_id": party.account_id,
        "total_debit": debit_total,
        "total_credit": credit_total,
        "balance": running,
        "rows": rows,
        "printed_by": user.full_name,
        "username": user.username,
        "branch_id": user.branch_id,
    }
