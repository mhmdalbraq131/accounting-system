from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.auth import get_current_user
from app.db.session import get_db
from app.models.branch import Branch
from app.models.user import User

router = APIRouter(prefix="/branches", tags=["الفروع"])
class BranchIn(BaseModel):
    code: str = Field(min_length=1, max_length=30)
    name_ar: str = Field(min_length=1, max_length=200)
    address: str | None = Field(default=None, max_length=300)
    phone: str | None = Field(default=None, max_length=50)
    is_main: bool = False

@router.get("")
def list_branches(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.scalars(select(Branch).order_by(Branch.is_main.desc(), Branch.name_ar)).all()

@router.post("", status_code=201)
def create_branch(payload: BranchIn, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    if db.scalar(select(Branch).where(Branch.code == payload.code)):
        raise HTTPException(409, "رمز الفرع مستخدم مسبقًا")
    if payload.is_main:
        for b in db.scalars(select(Branch).where(Branch.is_main.is_(True))).all(): b.is_main = False
    branch = Branch(**payload.model_dump())
    db.add(branch); db.commit(); db.refresh(branch)
    return branch

@router.put("/{branch_id}")
def update_branch(branch_id: int, payload: BranchIn, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    branch = db.get(Branch, branch_id)
    if not branch: raise HTTPException(404, "الفرع غير موجود")
    duplicate = db.scalar(select(Branch).where(Branch.code == payload.code, Branch.id != branch_id))
    if duplicate: raise HTTPException(409, "رمز الفرع مستخدم مسبقًا")
    if payload.is_main:
        for b in db.scalars(select(Branch).where(Branch.is_main.is_(True), Branch.id != branch_id)).all(): b.is_main = False
    for k,v in payload.model_dump().items(): setattr(branch,k,v)
    db.commit(); db.refresh(branch); return branch
