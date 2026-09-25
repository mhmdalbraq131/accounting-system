from datetime import datetime
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.accounting.journal_service import create_journal
from app.auth import get_current_user, require_permission
from app.db.session import get_db
from app.models.account import Account
from app.models.expense import Expense
from app.models.journal import JournalEntry
from app.models.party import Party
from app.models.user import User

router = APIRouter(prefix="/expenses", tags=["المصروفات"])


class ExpenseIn(BaseModel):
    expense_number: str | None = Field(default=None, max_length=40)
    expense_date: date
    category: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=500)
    amount: Decimal = Field(gt=0)
    supplier_id: int | None = None
    program_id: int | None = None
    expense_account_id: int | None = None
    payment_account_id: int | None = None


def _branch_allowed(user: User, branch_id: int | None) -> bool:
    return user.branch_id is None or branch_id in (None, user.branch_id)


def _validate_account(db: Session, user: User, account_id: int, label: str) -> Account:
    account = db.get(Account, account_id)
    if not account or not account.is_active:
        raise HTTPException(400, f"{label} غير موجود أو غير نشط")
    if not _branch_allowed(user, account.branch_id):
        raise HTTPException(403, f"{label} تابع لفرع آخر")
    return account


def _resolve_expense_account(db: Session, user: User, account_id: int | None) -> int:
    if account_id is not None:
        account = _validate_account(db, user, account_id, "حساب المصروف")
        if account.account_type != "expense":
            raise HTTPException(400, "الحساب المختار يجب أن يكون من نوع المصروفات")
        return account.id

    stmt = select(Account).where(Account.account_type == "expense", Account.is_active.is_(True))
    if user.branch_id is not None:
        stmt = stmt.where((Account.branch_id == user.branch_id) | Account.branch_id.is_(None))
    candidates = list(db.scalars(stmt.order_by(Account.code)))
    if len(candidates) == 1:
        return candidates[0].id
    raise HTTPException(400, "يجب تحديد حساب المصروف؛ يوجد أكثر من حساب مصروف متاح أو لا يوجد حساب مصروف")


def _next_expense_number(db: Session, year: int) -> str:
    prefix = f"EXP-{year}-"
    existing = db.scalar(
        select(Expense.expense_number)
        .where(Expense.expense_number.like(f"{prefix}%"))
        .order_by(Expense.id.desc())
        .limit(1)
    )
    if not existing:
        return f"{prefix}000001"
    try:
        sequence = int(existing.rsplit("-", 1)[1]) + 1
    except (ValueError, IndexError):
        sequence = db.query(Expense).filter(Expense.expense_number.like(f"{prefix}%")).count() + 1
    return f"{prefix}{sequence:06d}"


@router.get("")
def list_expenses(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_permission(user, "expenses.view", db)
    stmt = select(Expense).order_by(Expense.expense_date.desc(), Expense.id.desc())
    if user.branch_id is not None:
        stmt = stmt.where((Expense.branch_id == user.branch_id) | Expense.branch_id.is_(None))
    return list(db.scalars(stmt))


@router.post("", status_code=201)
def create_expense(payload: ExpenseIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_permission(user, "expenses.create", db)
    expense_number = (payload.expense_number or "").strip() or _next_expense_number(db, payload.expense_date.year)
    if db.scalar(select(Expense).where(Expense.expense_number == expense_number)):
        raise HTTPException(409, "رقم المصروف مستخدم مسبقًا")

    expense_account_id = _resolve_expense_account(db, user, payload.expense_account_id)
    if payload.payment_account_id is not None:
        payment_account = _validate_account(db, user, payload.payment_account_id, "حساب الدفع")
        if payment_account.account_type not in {"asset"}:
            raise HTTPException(400, "حساب الدفع يجب أن يكون حساب أصول")
        if payload.payment_account_id == expense_account_id:
            raise HTTPException(400, "حساب المصروف وحساب الدفع يجب أن يكونا مختلفين")

    if payload.supplier_id is not None:
        supplier = db.get(Party, payload.supplier_id)
        if not supplier or supplier.party_type not in {"supplier", "both"}:
            raise HTTPException(400, "المورد غير موجود أو غير صالح")
        if not _branch_allowed(user, supplier.branch_id):
            raise HTTPException(403, "المورد تابع لفرع آخر")
        if payload.payment_account_id is None and supplier.account_id is None:
            raise HTTPException(400, "يجب ربط المورد بحساب محاسبي عند تسجيل مصروف غير مدفوع")

    expense = Expense(
        expense_number=expense_number,
        expense_date=payload.expense_date,
        category=payload.category,
        description=payload.description,
        amount=payload.amount,
        supplier_id=payload.supplier_id,
        program_id=payload.program_id,
        expense_account_id=expense_account_id,
        payment_account_id=payload.payment_account_id,
        created_by=user.id,
        branch_id=user.branch_id,
        status="draft",
    )
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense


@router.post("/{expense_id}/post")
def post_expense(expense_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_permission(user, "expenses.post", db)
    expense = db.get(Expense, expense_id)
    if not expense:
        raise HTTPException(404, "المصروف غير موجود")
    if not _branch_allowed(user, expense.branch_id):
        raise HTTPException(403, "المصروف تابع لفرع آخر")
    if expense.status != "draft":
        raise HTTPException(400, "لا يمكن ترحيل مصروف ليس في حالة مسودة")
    if expense.journal_entry_id:
        raise HTTPException(409, "المصروف مرتبط بقيد محاسبي مسبقًا")

    expense_account_id = _resolve_expense_account(db, user, expense.expense_account_id)
    credit_account_id = expense.payment_account_id
    if credit_account_id is None and expense.supplier_id is not None:
        supplier = db.get(Party, expense.supplier_id)
        if not supplier or supplier.account_id is None:
            raise HTTPException(400, "المورد غير مربوط بحساب محاسبي")
        if not _branch_allowed(user, supplier.branch_id):
            raise HTTPException(403, "المورد تابع لفرع آخر")
        credit_account_id = supplier.account_id

    if credit_account_id is None:
        raise HTTPException(400, "يجب تحديد حساب الدفع أو مورد مرتبط بحساب محاسبي")

    _validate_account(db, user, credit_account_id, "الحساب الدائن")
    if credit_account_id == expense_account_id:
        raise HTTPException(400, "الحساب المدين والدائن يجب أن يكونا مختلفين")

    try:
        entry = create_journal(
            db,
            entry_number=f"EXP-JV-{expense.expense_number}",
            entry_date=expense.expense_date,
            description=expense.description,
            lines=[
                {"account_id": expense_account_id, "debit": expense.amount, "credit": Decimal("0")},
                {"account_id": credit_account_id, "debit": Decimal("0"), "credit": expense.amount},
            ],
            created_by=expense.created_by,
            branch_id=expense.branch_id,
            status="posted",
        )
        entry.posted_at = datetime.utcnow()
        expense.expense_account_id = expense_account_id
        expense.journal_entry_id = entry.id
        expense.status = "posted"
        expense.posted_at = datetime.utcnow()
        db.commit()
        db.refresh(expense)
        return expense
    except ValueError as exc:
        db.rollback()
        raise HTTPException(400, str(exc))


@router.post("/{expense_id}/cancel")
def cancel_expense(expense_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_permission(user, "expenses.cancel", db)
    expense = db.get(Expense, expense_id)
    if not expense:
        raise HTTPException(404, "المصروف غير موجود")
    if not _branch_allowed(user, expense.branch_id):
        raise HTTPException(403, "المصروف تابع لفرع آخر")
    if expense.status != "posted" or not expense.journal_entry_id:
        raise HTTPException(400, "لا يمكن إلغاء مصروف غير مرحّل")

    original = db.get(JournalEntry, expense.journal_entry_id)
    if not original:
        raise HTTPException(409, "القيد المرتبط بالمصروف غير موجود")

    try:
        reversal = create_journal(
            db,
            entry_number=f"REV-EXP-{expense.expense_number}",
            entry_date=expense.expense_date,
            description=f"عكس المصروف {expense.expense_number}: {expense.description}",
            lines=[
                {"account_id": line.account_id, "debit": line.credit, "credit": line.debit}
                for line in original.lines
            ],
            created_by=user.id,
            branch_id=expense.branch_id,
            status="posted",
        )
        reversal.posted_at = datetime.utcnow()
        expense.status = "cancelled"
        db.commit()
        db.refresh(expense)
        return expense
    except ValueError as exc:
        db.rollback()
        raise HTTPException(400, str(exc))
