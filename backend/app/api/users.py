from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.auth import get_current_user, hash_password, require_permission, user_permission_codes, user_role_names
from app.db.session import get_db
from app.models.branch import Branch
from app.models.role import Permission, Role, RolePermission, UserRole
from app.models.user import User
from app.models.audit_log import AuditLog

router = APIRouter(prefix="/users", tags=["المستخدمون والصلاحيات"])


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    full_name: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=8, max_length=200)
    branch_id: int | None = None
    role_id: int | None = None


class UserUpdate(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    full_name: str = Field(min_length=1, max_length=200)
    password: str | None = Field(default=None, min_length=8, max_length=200)
    branch_id: int | None = None
    role_id: int | None = None
    is_active: bool = True


class RolePermissionsUpdate(BaseModel):
    permission_codes: list[str] = Field(default_factory=list)


def _user_out(user: User, db: Session) -> dict[str, object]:
    roles = sorted(user_role_names(user.id, db))
    permissions = sorted(user_permission_codes(user.id, db))
    return {
        "id": user.id,
        "username": user.username,
        "full_name": user.full_name,
        "branch_id": user.branch_id,
        "is_active": user.is_active,
        "role_names": roles,
        "permission_codes": permissions,
    }


@router.get("/roles")
def list_roles(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_permission(user, "users.manage", db)
    return db.scalars(select(Role).where(Role.is_active.is_(True)).order_by(Role.name)).all()


@router.get("/permissions")
def list_permissions(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_permission(user, "roles.manage", db)
    return db.scalars(select(Permission).order_by(Permission.code)).all()


@router.get("/roles/{role_id}/permissions")
def get_role_permissions(role_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_permission(user, "roles.manage", db)
    if not db.get(Role, role_id):
        raise HTTPException(404, "الدور غير موجود")
    return db.scalars(
        select(Permission)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .where(RolePermission.role_id == role_id)
        .order_by(Permission.code)
    ).all()


@router.put("/roles/{role_id}/permissions")
def update_role_permissions(role_id: int, payload: RolePermissionsUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_permission(user, "roles.manage", db)
    role = db.get(Role, role_id)
    if not role:
        raise HTTPException(404, "الدور غير موجود")
    permissions = db.scalars(select(Permission).where(Permission.code.in_(payload.permission_codes))).all() if payload.permission_codes else []
    missing = sorted(set(payload.permission_codes) - {p.code for p in permissions})
    if missing:
        raise HTTPException(400, f"صلاحيات غير معروفة: {', '.join(missing)}")
    db.execute(delete(RolePermission).where(RolePermission.role_id == role_id))
    db.add_all([RolePermission(role_id=role_id, permission_id=p.id) for p in permissions])
    db.commit()
    return {"role_id": role_id, "permission_codes": sorted(p.code for p in permissions)}


@router.get("")
def list_users(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_permission(user, "users.manage", db)
    return [_user_out(item, db) for item in db.scalars(select(User).order_by(User.full_name)).all()]


@router.post("", status_code=201)
def create_user(payload: UserCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_permission(user, "users.manage", db)
    if db.scalar(select(User).where(User.username == payload.username)):
        raise HTTPException(409, "اسم المستخدم مستخدم مسبقًا")
    if payload.branch_id is not None and not db.get(Branch, payload.branch_id):
        raise HTTPException(400, "الفرع غير موجود")
    data = payload.model_dump()
    role_id = data.pop("role_id")
    password = data.pop("password")
    new_user = User(**data, password_hash=hash_password(password))
    db.add(new_user)
    db.flush()
    if role_id is not None:
        if not db.get(Role, role_id):
            raise HTTPException(400, "الدور غير موجود")
        db.add(UserRole(user_id=new_user.id, role_id=role_id))
    db.add(AuditLog(user_id=user.id, action="create", entity_type="user", entity_id=new_user.id))
    db.commit()
    db.refresh(new_user)
    return _user_out(new_user, db)


@router.put("/{user_id}")
def update_user(user_id: int, payload: UserUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_permission(current_user, "users.manage", db)
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(404, "المستخدم غير موجود")
    duplicate = db.scalar(select(User).where(User.username == payload.username, User.id != user_id))
    if duplicate:
        raise HTTPException(409, "اسم المستخدم مستخدم مسبقًا")
    if payload.branch_id is not None and not db.get(Branch, payload.branch_id):
        raise HTTPException(400, "الفرع غير موجود")
    if payload.role_id is not None and not db.get(Role, payload.role_id):
        raise HTTPException(400, "الدور غير موجود")
    target.username = payload.username
    target.full_name = payload.full_name
    target.branch_id = payload.branch_id
    target.is_active = payload.is_active
    if payload.password:
        target.password_hash = hash_password(payload.password)
    db.execute(delete(UserRole).where(UserRole.user_id == user_id))
    if payload.role_id is not None:
        db.add(UserRole(user_id=user_id, role_id=payload.role_id))
    db.commit()
    db.refresh(target)
    return _user_out(target, db)
