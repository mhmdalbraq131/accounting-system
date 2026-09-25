from datetime import date
from decimal import Decimal
import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.accounting.journal_service import create_journal, UnbalancedJournalError, resolve_reversal_date
from app.api.deps import get_current_user, get_db, require_permission
from app.models.account import Account
from app.models.ar_ap import Invoice, Payment, PaymentAllocation
from app.models.audit_log import AuditLog
from app.models.fiscal_period import FiscalPeriod
from app.models.party import Party
from app.models.user import User

router = APIRouter(prefix="/ar-ap", tags=["الذمم والمدفوعات"])

class InvoiceCreate(BaseModel):
    invoice_number: str = Field(min_length=1, max_length=50)
    invoice_type: str = Field(pattern="^(sales|purchase)$")
    party_id: int
    invoice_date: date
    due_date: date | None = None
    description: str = Field(min_length=1, max_length=500)
    total_amount: Decimal = Field(gt=0)
    receivable_account_id: int
    revenue_account_id: int

class PaymentCreate(BaseModel):
    payment_number: str = Field(min_length=1, max_length=50)
    payment_type: str = Field(pattern="^(receipt|payment|transfer)$")
    party_id: int | None = None
    payment_date: date
    amount: Decimal = Field(gt=0)
    source_account_id: int
    target_account_id: int
    description: str = Field(min_length=1, max_length=500)

class AllocationCreate(BaseModel):
    invoice_id: int
    amount: Decimal = Field(gt=0)

def _branch_ok(user: User, branch_id: int | None):
    return user.branch_id is None or branch_id in (None, user.branch_id)

def _account(db, account_id, user):
    account=db.get(Account,account_id)
    if not account or not account.is_active: raise HTTPException(400,"الحساب غير موجود أو غير نشط")
    if user.branch_id is not None and account.branch_id not in (None,user.branch_id): raise HTTPException(403,"الحساب تابع لفرع آخر")
    return account

def _require_type(account: Account, allowed: set[str], label: str) -> Account:
    if account.account_type not in allowed:
        raise HTTPException(400, f"{label} يجب أن يكون من نوع: {', '.join(sorted(allowed))}")
    return account


def _party(db, party_id, user):
    party=db.get(Party,party_id)
    if not party or not party.is_active: raise HTTPException(400,"الطرف غير موجود أو غير نشط")
    if user.branch_id is not None and party.branch_id not in (None,user.branch_id): raise HTTPException(403,"الطرف تابع لفرع آخر")
    return party

def _row_invoice(x):
    return {"id":x.id,"invoice_number":x.invoice_number,"invoice_type":x.invoice_type,"party_id":x.party_id,
            "invoice_date":x.invoice_date,"due_date":x.due_date,"description":x.description,
            "total_amount":x.total_amount,"paid_amount":x.paid_amount,"remaining_amount":x.remaining_amount,
            "receivable_account_id":x.receivable_account_id,"revenue_account_id":x.revenue_account_id,
            "journal_entry_id":x.journal_entry_id,"status":x.status,"branch_id":x.branch_id}

def _row_payment(x):
    return {"id":x.id,"payment_number":x.payment_number,"payment_type":x.payment_type,"party_id":x.party_id,
            "payment_date":x.payment_date,"amount":x.amount,"allocated_amount":x.allocated_amount,
            "remaining_amount":x.remaining_amount,"source_account_id":x.source_account_id,
            "target_account_id":x.target_account_id,"description":x.description,
            "journal_entry_id":x.journal_entry_id,"status":x.status,"branch_id":x.branch_id}

@router.get("/invoices")
def list_invoices(invoice_type: str | None = None, party_id: int | None = None, outstanding_only: bool = False,
                  db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_permission(user,"ar_ap.view",db)
    stmt=select(Invoice)
    if user.branch_id is not None: stmt=stmt.where((Invoice.branch_id==user.branch_id)|Invoice.branch_id.is_(None))
    if invoice_type: stmt=stmt.where(Invoice.invoice_type==invoice_type)
    if party_id: stmt=stmt.where(Invoice.party_id==party_id)
    if outstanding_only: stmt=stmt.where(Invoice.remaining_amount>0,Invoice.status=="posted")
    return [_row_invoice(x) for x in db.scalars(stmt.order_by(Invoice.invoice_date.desc(),Invoice.id.desc())).all()]

@router.post("/invoices")
def create_invoice(payload: InvoiceCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_permission(user,"ar_ap.create",db)
    if db.scalar(select(Invoice.id).where(Invoice.invoice_number==payload.invoice_number)): raise HTTPException(400,"رقم الفاتورة مستخدم مسبقًا")
    party=_party(db,payload.party_id,user)
    ar=_account(db,payload.receivable_account_id,user); income=_account(db,payload.revenue_account_id,user)
    if payload.invoice_type=="sales":
        _require_type(ar, {"asset"}, "حساب الذمم المدينة")
        _require_type(income, {"revenue"}, "حساب الإيراد")
    else:
        _require_type(ar, {"liability"}, "حساب الذمم الدائنة")
        _require_type(income, {"expense", "cost_of_service"}, "حساب تكلفة المشتريات")
    if payload.invoice_type=="sales" and party.party_type not in ("customer","agent"): raise HTTPException(400,"فاتورة المبيعات يجب أن تكون لعميل أو وكيل")
    if payload.invoice_type=="purchase" and party.party_type not in ("supplier","agent"): raise HTTPException(400,"فاتورة المشتريات يجب أن تكون لمورد أو وكيل")
    if payload.due_date and payload.due_date < payload.invoice_date: raise HTTPException(400,"تاريخ الاستحقاق لا يمكن أن يسبق تاريخ الفاتورة")
    x=Invoice(invoice_number=payload.invoice_number,invoice_type=payload.invoice_type,party_id=party.id,
              invoice_date=payload.invoice_date,due_date=payload.due_date,description=payload.description,
              total_amount=payload.total_amount,paid_amount=0,remaining_amount=payload.total_amount,
              receivable_account_id=ar.id,revenue_account_id=income.id,status="draft",branch_id=user.branch_id,created_by=user.id)
    db.add(x); db.flush()
    db.add(AuditLog(user_id=user.id,action="create",entity_type="invoice",entity_id=x.id,details=json.dumps({"invoice_number":x.invoice_number},ensure_ascii=False)))
    db.commit(); db.refresh(x); return _row_invoice(x)

@router.post("/invoices/{invoice_id}/post")
def post_invoice(invoice_id:int,db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    require_permission(user,"ar_ap.post",db)
    x=db.get(Invoice,invoice_id)
    if not x: raise HTTPException(404,"الفاتورة غير موجودة")
    if not _branch_ok(user,x.branch_id): raise HTTPException(403,"الفاتورة تابعة لفرع آخر")
    if x.status!="draft": raise HTTPException(400,"لا يمكن ترحيل الفاتورة بهذه الحالة")
    ar=_account(db,x.receivable_account_id,user); income=_account(db,x.revenue_account_id,user)
    if x.invoice_type=="sales":
        _require_type(ar, {"asset"}, "حساب الذمم المدينة")
        _require_type(income, {"revenue"}, "حساب الإيراد")
    else:
        _require_type(ar, {"liability"}, "حساب الذمم الدائنة")
        _require_type(income, {"expense", "cost_of_service"}, "حساب تكلفة المشتريات")
    if x.invoice_type=="sales":
        debit,credit=ar.id,income.id
    else:
        debit,credit=income.id,ar.id
    try:
        je=create_journal(db,entry_number=f"INV-{x.invoice_number}",entry_date=x.invoice_date,
                          description=x.description,created_by=user.id,branch_id=x.branch_id,status="posted",
                          lines=[{"account_id":debit,"debit":x.total_amount,"credit":0,"description":x.description},
                                 {"account_id":credit,"debit":0,"credit":x.total_amount,"description":x.description}])
    except (ValueError,UnbalancedJournalError) as exc: raise HTTPException(400,str(exc))
    x.journal_entry_id=je.id; x.status="posted"
    db.add(AuditLog(user_id=user.id,action="post",entity_type="invoice",entity_id=x.id,details=json.dumps({"journal_entry_id":je.id},ensure_ascii=False)))
    db.commit(); db.refresh(x); return _row_invoice(x)

@router.post("/invoices/{invoice_id}/cancel")
def cancel_invoice(invoice_id:int,db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    require_permission(user,"ar_ap.cancel",db)
    x=db.get(Invoice,invoice_id)
    if not x: raise HTTPException(404,"الفاتورة غير موجودة")
    if not _branch_ok(user,x.branch_id): raise HTTPException(403,"الفاتورة تابعة لفرع آخر")
    if x.status not in ("draft","posted"): raise HTTPException(400,"الفاتورة ملغاة مسبقًا")
    if x.paid_amount>0: raise HTTPException(400,"لا يمكن إلغاء فاتورة عليها مدفوعات؛ اعكس المدفوع أولًا")
    if x.status=="posted":
        ar=_account(db,x.receivable_account_id,user); income=_account(db,x.revenue_account_id,user)
        debit,credit=(ar.id,income.id) if x.invoice_type=="purchase" else (income.id,ar.id)
        try:
            je=create_journal(db,entry_number=f"REV-INV-{x.invoice_number}",entry_date=resolve_reversal_date(db, original.entry_date, booking.branch_id),description=f"عكس الفاتورة {x.invoice_number}",
                              created_by=user.id,branch_id=x.branch_id,status="posted",
                              lines=[{"account_id":debit,"debit":x.total_amount,"credit":0},{"account_id":credit,"debit":0,"credit":x.total_amount}])
        except (ValueError,UnbalancedJournalError) as exc: raise HTTPException(400,str(exc))
    x.status="cancelled"
    db.add(AuditLog(user_id=user.id,action="cancel",entity_type="invoice",entity_id=x.id,details=json.dumps({"invoice_number":x.invoice_number},ensure_ascii=False)))
    db.commit(); return _row_invoice(x)

@router.get("/payments")
def list_payments(payment_type:str|None=None,party_id:int|None=None,db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    require_permission(user,"ar_ap.view",db)
    stmt=select(Payment)
    if user.branch_id is not None: stmt=stmt.where((Payment.branch_id==user.branch_id)|Payment.branch_id.is_(None))
    if payment_type: stmt=stmt.where(Payment.payment_type==payment_type)
    if party_id: stmt=stmt.where(Payment.party_id==party_id)
    return [_row_payment(x) for x in db.scalars(stmt.order_by(Payment.payment_date.desc(),Payment.id.desc())).all()]

@router.post("/payments")
def create_payment(payload:PaymentCreate,db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    require_permission(user,"ar_ap.create",db)
    if db.scalar(select(Payment.id).where(Payment.payment_number==payload.payment_number)): raise HTTPException(400,"رقم الدفعة مستخدم مسبقًا")
    if payload.source_account_id==payload.target_account_id: raise HTTPException(400,"حساب المصدر والهدف يجب أن يكونا مختلفين")
    source=_account(db,payload.source_account_id,user); target=_account(db,payload.target_account_id,user)
    if payload.payment_type == "transfer":
        _require_type(source, {"asset"}, "حساب المصدر")
        _require_type(target, {"asset"}, "حساب الهدف")
    elif payload.payment_type == "receipt":
        _require_type(source, {"asset"}, "حساب الذمم/المصدر")
        _require_type(target, {"asset"}, "حساب الصندوق أو البنك")
    else:
        _require_type(source, {"asset"}, "حساب الصندوق أو البنك")
        _require_type(target, {"liability"}, "حساب الذمم الدائنة")
    if payload.party_id is not None: _party(db,payload.party_id,user)
    if payload.payment_type in ("receipt","payment") and payload.party_id is None: raise HTTPException(400,"الطرف مطلوب للقبض أو الصرف")
    x=Payment(payment_number=payload.payment_number,payment_type=payload.payment_type,party_id=payload.party_id,
              payment_date=payload.payment_date,amount=payload.amount,allocated_amount=0,remaining_amount=payload.amount,
              source_account_id=payload.source_account_id,target_account_id=payload.target_account_id,description=payload.description,
              status="draft",branch_id=user.branch_id,created_by=user.id)
    db.add(x); db.flush()
    db.add(AuditLog(user_id=user.id,action="create",entity_type="payment",entity_id=x.id,details=json.dumps({"payment_number":x.payment_number},ensure_ascii=False)))
    db.commit(); db.refresh(x); return _row_payment(x)

@router.post("/payments/{payment_id}/post")
def post_payment(payment_id:int,db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    require_permission(user,"ar_ap.post",db)
    x=db.get(Payment,payment_id)
    if not x: raise HTTPException(404,"الدفعة غير موجودة")
    if not _branch_ok(user,x.branch_id): raise HTTPException(403,"الدفعة تابعة لفرع آخر")
    if x.status!="draft": raise HTTPException(400,"لا يمكن ترحيل الدفعة بهذه الحالة")
    source=_account(db,x.source_account_id,user); target=_account(db,x.target_account_id,user)
    if x.payment_type=="receipt":
        debit_account, credit_account = source.id, target.id
    else:
        debit_account, credit_account = target.id, source.id
    try:
        je=create_journal(db,entry_number=f"PAY-{x.payment_number}",entry_date=x.payment_date,description=x.description,created_by=user.id,branch_id=x.branch_id,status="posted",
                          lines=[{"account_id":debit_account,"debit":x.amount,"credit":0},{"account_id":credit_account,"debit":0,"credit":x.amount}])
    except (ValueError,UnbalancedJournalError) as exc: raise HTTPException(400,str(exc))
    x.journal_entry_id=je.id; x.status="posted"
    db.add(AuditLog(user_id=user.id,action="post",entity_type="payment",entity_id=x.id,details=json.dumps({"journal_entry_id":je.id},ensure_ascii=False)))
    db.commit(); db.refresh(x); return _row_payment(x)

@router.post("/payments/{payment_id}/allocate")
def allocate_payment(payment_id:int,payload:AllocationCreate,db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    require_permission(user,"ar_ap.allocate",db)
    p=db.get(Payment,payment_id); inv=db.get(Invoice,payload.invoice_id)
    if not p or not inv: raise HTTPException(404,"الدفعة أو الفاتورة غير موجودة")
    if not _branch_ok(user,p.branch_id) or not _branch_ok(user,inv.branch_id): raise HTTPException(403,"العنصر تابع لفرع آخر")
    if p.status!="posted" or inv.status!="posted": raise HTTPException(400,"يجب ترحيل الدفعة والفاتورة أولًا")
    if p.party_id != inv.party_id: raise HTTPException(400,"الدفعة والفاتورة تخصان طرفين مختلفين")
    if payload.amount>p.remaining_amount: raise HTTPException(400,"المبلغ يتجاوز الرصيد غير المخصص للدفعة")
    if payload.amount>inv.remaining_amount: raise HTTPException(400,"المبلغ يتجاوز المتبقي على الفاتورة")
    if p.payment_type=="receipt" and inv.invoice_type!="sales": raise HTTPException(400,"سند القبض يخصص لفاتورة مبيعات")
    if p.payment_type=="payment" and inv.invoice_type!="purchase": raise HTTPException(400,"سند الصرف يخصص لفاتورة مشتريات")
    db.add(PaymentAllocation(payment_id=p.id,invoice_id=inv.id,amount=payload.amount))
    p.allocated_amount += payload.amount; p.remaining_amount -= payload.amount
    inv.paid_amount += payload.amount; inv.remaining_amount -= payload.amount
    if inv.remaining_amount==0: inv.status="paid"
    db.add(AuditLog(user_id=user.id,action="allocate",entity_type="payment",entity_id=p.id,details=json.dumps({"invoice_id":inv.id,"amount":str(payload.amount)},ensure_ascii=False)))
    db.commit(); db.refresh(p); return {"payment":_row_payment(p),"invoice":_row_invoice(inv)}

@router.post("/payments/{payment_id}/allocate/{allocation_id}/reverse")
def reverse_allocation(payment_id:int, allocation_id:int, db:Session=Depends(get_db), user:User=Depends(get_current_user)):
    require_permission(user,"ar_ap.allocate",db)
    p=db.get(Payment,payment_id)
    allocation=db.get(PaymentAllocation,allocation_id)
    if not p or not allocation or allocation.payment_id != p.id:
        raise HTTPException(404,"التخصيص غير موجود")
    if not _branch_ok(user,p.branch_id):
        raise HTTPException(403,"الدفعة تابعة لفرع آخر")
    inv=db.get(Invoice,allocation.invoice_id)
    if not inv:
        raise HTTPException(409,"الفاتورة المرتبطة بالتخصيص غير موجودة")
    if p.status!="posted" or inv.status not in ("posted","paid"):
        raise HTTPException(400,"لا يمكن عكس التخصيص في الحالة الحالية")
    amount=Decimal(str(allocation.amount))
    p.allocated_amount=max(Decimal("0"),Decimal(str(p.allocated_amount))-amount)
    p.remaining_amount=Decimal(str(p.remaining_amount))+amount
    inv.paid_amount=max(Decimal("0"),Decimal(str(inv.paid_amount))-amount)
    inv.remaining_amount=Decimal(str(inv.remaining_amount))+amount
    if inv.status=="paid":
        inv.status="posted"
    db.delete(allocation)
    db.add(AuditLog(user_id=user.id,action="allocate_reverse",entity_type="payment",entity_id=p.id,
                    details=json.dumps({"invoice_id":inv.id,"amount":str(amount)},ensure_ascii=False)))
    db.commit()
    db.refresh(p)
    return {"payment":_row_payment(p),"invoice":_row_invoice(inv)}

@router.post("/payments/{payment_id}/cancel")
def cancel_payment(payment_id:int,db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    require_permission(user,"ar_ap.cancel",db)
    x=db.get(Payment,payment_id)
    if not x: raise HTTPException(404,"الدفعة غير موجودة")
    if not _branch_ok(user,x.branch_id): raise HTTPException(403,"الدفعة تابعة لفرع آخر")
    if x.status not in ("draft","posted"): raise HTTPException(400,"الدفعة ملغاة مسبقًا")
    if x.allocated_amount>0: raise HTTPException(400,"لا يمكن إلغاء دفعة مخصصة لفواتير؛ عكس التخصيص أولًا")
    if x.status=="posted":
        source=_account(db,x.source_account_id,user); target=_account(db,x.target_account_id,user)
        if x.payment_type=="receipt":
            debit_account, credit_account = target.id, source.id
        else:
            debit_account, credit_account = source.id, target.id
        try:
            create_journal(db,entry_number=f"REV-PAY-{x.payment_number}",entry_date=resolve_reversal_date(db, original.entry_date, booking.branch_id),description=f"عكس الدفعة {x.payment_number}",
                           created_by=user.id,branch_id=x.branch_id,status="posted",
                           lines=[{"account_id":debit_account,"debit":x.amount,"credit":0},{"account_id":credit_account,"debit":0,"credit":x.amount}])
        except (ValueError,UnbalancedJournalError) as exc: raise HTTPException(400,str(exc))
    x.status="cancelled"
    db.add(AuditLog(user_id=user.id,action="cancel",entity_type="payment",entity_id=x.id,details=json.dumps({"payment_number":x.payment_number},ensure_ascii=False)))
    db.commit(); return _row_payment(x)

@router.get("/aging")
def aging(invoice_type:str="sales",as_of_date:date|None=None,db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    require_permission(user,"ar_ap.view",db)
    if invoice_type not in ("sales","purchase"): raise HTTPException(400,"نوع الذمم غير صحيح")
    as_of=as_of_date or date.today()
    stmt=select(Invoice,Party).join(Party,Invoice.party_id==Party.id).where(Invoice.invoice_type==invoice_type,Invoice.status.in_(("posted","paid")),Invoice.remaining_amount>0,Invoice.invoice_date<=as_of)
    if user.branch_id is not None: stmt=stmt.where((Invoice.branch_id==user.branch_id)|Invoice.branch_id.is_(None))
    rows=[]
    buckets={"current":Decimal("0"),"1_30":Decimal("0"),"31_60":Decimal("0"),"61_90":Decimal("0"),"over_90":Decimal("0")}
    for inv,party in db.execute(stmt).all():
        days=max(0,(as_of-(inv.due_date or inv.invoice_date)).days)
        bucket="current" if days<=0 else "1_30" if days<=30 else "31_60" if days<=60 else "61_90" if days<=90 else "over_90"
        buckets[bucket]+=Decimal(str(inv.remaining_amount))
        rows.append({"invoice_id":inv.id,"invoice_number":inv.invoice_number,"party_id":party.id,"party_name":party.name,"due_date":inv.due_date,"remaining_amount":inv.remaining_amount,"days_overdue":days,"bucket":bucket})
    return {"as_of_date":as_of,"invoice_type":invoice_type,"buckets":buckets,"rows":rows}
