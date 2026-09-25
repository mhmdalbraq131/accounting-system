import os
from pathlib import Path
from sqlalchemy import select
from app.auth import hash_password
from app.db.session import SessionLocal
from app.models.role import Permission, Role, RolePermission, UserRole
from app.models.user import User

def _load_env_file() -> None:
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = [part.strip() for part in line.split("=", 1)]
        os.environ.setdefault(key, value)

_load_env_file()

DEFAULT_PERMISSIONS = [
    ("accounts.view", "عرض الحسابات"),
    ("parties.view", "عرض الأطراف"),
    ("expenses.view", "عرض المصروفات"),
    ("accounts.create", "إضافة الحسابات"),
    ("accounts.update", "تعديل الحسابات"),
    ("accounts.disable", "تعطيل الحسابات"),
    ("parties.create", "إضافة الأطراف"),
    ("parties.update", "تعديل الأطراف"),
    ("parties.disable", "تعطيل الأطراف"),
    ("vouchers.view", "عرض السندات"),
    ("vouchers.create", "إضافة السندات"),
    ("vouchers.post", "ترحيل السندات"),
    ("vouchers.cancel", "إلغاء السندات"),
    ("reports.view", "عرض التقارير"),
    ("expenses.create", "إضافة المصروفات"),
    ("expenses.post", "ترحيل المصروفات"),
    ("expenses.cancel", "إلغاء المصروفات"),
    ("settings.manage", "إدارة الإعدادات"),
    ("branches.manage", "إدارة الفروع"),
    ("users.manage", "إدارة المستخدمين"),
    ("roles.manage", "إدارة الأدوار والصلاحيات"),
    ("accounting.dimensions.manage", "إدارة الأبعاد المحاسبية"),
    ("accounting.periods.manage", "إدارة الفترات المحاسبية"),
    ("audit.read", "عرض سجل التدقيق"),
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

        sub_admin = db.scalar(select(Role).where(Role.name == "sub_admin"))
        if not sub_admin:
            sub_admin = Role(name="sub_admin")
            db.add(sub_admin)
            db.flush()
        for code in ("branches.manage", "users.manage"):
            permission = db.scalar(select(Permission).where(Permission.code == code))
            if permission and not db.scalar(select(RolePermission).where(RolePermission.role_id == sub_admin.id, RolePermission.permission_id == permission.id)):
                db.add(RolePermission(role_id=sub_admin.id, permission_id=permission.id))

        if not db.scalar(select(UserRole).where(UserRole.user_id == user.id, UserRole.role_id == role.id)):
            db.add(UserRole(user_id=user.id, role_id=role.id))
        db.commit()

if __name__ == "__main__":
    seed()
