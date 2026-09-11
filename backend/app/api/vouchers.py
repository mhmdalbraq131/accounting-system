from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.accounting.voucher_service import cancel_voucher, create_voucher, post_voucher
from app.db.session import get_db
from app.models.user import User
from app.models.voucher import Voucher
from app.models.financial import FinancialAccount

router = APIRouter(prefix="/vouchers", tags=["السندات"])


class VoucherCreate(BaseModel):
    voucher_number: str
    voucher_type: str
    voucher_date: date
    amount: Decimal
    description: str
    source_account_id: int
    destination_account_id: int
    currency_id: int | None = None
    exchange_rate: Decimal | None = None


class VoucherOut(VoucherCreate):
    id: int
    status: str
    journal_entry_id: int | None
    model_config = ConfigDict(from_attributes=True)


@router.post("", response_model=VoucherOut, status_code=201)
def create(payload: VoucherCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        voucher = create_voucher(db, **payload.model_dump(), created_by=user.id)
        voucher.branch_id = user.branch_id
        db.commit()
        db.refresh(voucher)
        return voucher
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/{voucher_id}/post", response_model=VoucherOut)
def post(voucher_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    voucher = db.get(Voucher, voucher_id)
    if not voucher:
        raise HTTPException(status_code=404, detail="السند غير موجود")
    if user.branch_id is not None and voucher.branch_id not in (None, user.branch_id):
        raise HTTPException(status_code=403, detail="السند تابع لفرع آخر")
    if user.branch_id is not None:
        for account_id in (voucher.source_account_id, voucher.destination_account_id):
            fa = db.scalar(select(FinancialAccount).where(FinancialAccount.ledger_account_id == account_id, FinancialAccount.branch_id == user.branch_id))
            if fa is not None and fa.branch_id != user.branch_id: raise HTTPException(status_code=403, detail="الحساب المالي تابع لفرع آخر")
    try:
        post_voucher(db, voucher)
        db.commit()
        db.refresh(voucher)
        return voucher
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/{voucher_id}/cancel", response_model=VoucherOut)
def cancel(voucher_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    voucher = db.get(Voucher, voucher_id)
    if not voucher:
        raise HTTPException(status_code=404, detail="السند غير موجود")
    if user.branch_id is not None and voucher.branch_id not in (None, user.branch_id):
        raise HTTPException(status_code=403, detail="السند تابع لفرع آخر")
    try:
        cancel_voucher(db, voucher)
        db.commit()
        db.refresh(voucher)
        return voucher
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/{voucher_id}/print-data")
def print_data(voucher_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    voucher = db.get(Voucher, voucher_id)
    if not voucher:
        raise HTTPException(status_code=404, detail="السند غير موجود")
    if user.branch_id is not None and voucher.branch_id not in (None, user.branch_id):
        raise HTTPException(status_code=403, detail="السند تابع لفرع آخر")
    return {"voucher": VoucherOut.model_validate(voucher), "printed_by": user.full_name, "printed_by_username": user.username, "branch_id": user.branch_id}
