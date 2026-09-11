from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.auth import get_current_user, hash_password
from app.db.session import get_db
from app.models.branch import Branch
from app.models.role import Role, UserRole
from app.models.user import User

router = APIRouter(prefix="/users", tags=["المستخدمون والصلاحيات"])
class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    full_name: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=8, max_length=200)
    branch_id: int | None = None
    role_id: int | None = None

@router.get("/roles")
def list_roles(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.scalars(select(Role).where(Role.is_active.is_(True)).order_by(Role.name)).all()

@router.get("")
def list_users(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.scalars(select(User).order_by(User.full_name)).all()

@router.post("", status_code=201)
def create_user(payload: UserCreate, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    if db.scalar(select(User).where(User.username == payload.username)):
        raise HTTPException(409, "اسم المستخدم مستخدم مسبقًا")
    if payload.branch_id is not None and not db.get(Branch, payload.branch_id):
        raise HTTPException(400, "الفرع غير موجود")
    data=payload.model_dump(); role_id=data.pop("role_id"); password=data.pop("password")
    user=User(**data, password_hash=hash_password(password)); db.add(user); db.flush()
    if role_id is not None:
        if not db.get(Role, role_id): raise HTTPException(400, "الدور غير موجود")
        db.add(UserRole(user_id=user.id, role_id=role_id))
    db.commit(); db.refresh(user); return user
