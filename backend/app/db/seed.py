import os

from sqlalchemy import select

from app.auth import hash_password
from app.db.session import SessionLocal
from app.models.role import Permission, Role, RolePermission, UserRole
from app.models.user import User

DEFAULT_PERMISSIONS = [
    ("accounts.view", "عرض الحسابات"),
    ("accounts.create", "إضافة الحسابات"),
    ("vouchers.view", "عرض السندات"),
    ("vouchers.create", "إضافة السندات"),
    ("vouchers.post", "ترحيل السندات"),
    ("vouchers.cancel", "إلغاء السندات"),
    ("reports.view", "عرض التقارير"),
    ("settings.manage", "إدارة الإعدادات"),
]


def seed() -> None:
    username = os.getenv("ACCOUNTING_ADMIN_USER", "admin")
    password = os.getenv("ACCOUNTING_ADMIN_PASSWORD")
    if not password:
        raise RuntimeError("ACCOUNTING_ADMIN_PASSWORD غير مضبوط")

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.username == username))
        if not user:
            user = User(username=username, full_name="مدير النظام", password_hash=hash_password(password))
            db.add(user)
            db.flush()

        role = db.scalar(select(Role).where(Role.name == "admin"))
        if not role:
            role = Role(name="admin")
            db.add(role)
            db.flush()

        for code, name_ar in DEFAULT_PERMISSIONS:
            permission = db.scalar(select(Permission).where(Permission.code == code))
            if not permission:
                permission = Permission(code=code, name_ar=name_ar)
                db.add(permission)
                db.flush()
            if not db.scalar(select(RolePermission).where(RolePermission.role_id == role.id, RolePermission.permission_id == permission.id)):
                db.add(RolePermission(role_id=role.id, permission_id=permission.id))

        if not db.scalar(select(UserRole).where(UserRole.user_id == user.id, UserRole.role_id == role.id)):
            db.add(UserRole(user_id=user.id, role_id=role.id))
        db.commit()


if __name__ == "__main__":
    seed()
