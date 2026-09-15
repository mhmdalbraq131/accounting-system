"""seed role permissions for administration

Revision ID: 20260915_0008
Revises: 20260915_0007
Create Date: 2026-09-15
"""

from alembic import op
import sqlalchemy as sa

revision = "20260915_0008"
down_revision = "20260915_0007"
branch_labels = None
depends_on = None

PERMISSIONS = [
    ("settings.manage", "إدارة إعدادات النظام"),
    ("branches.manage", "إدارة الفروع"),
    ("users.manage", "إدارة المستخدمين"),
    ("roles.manage", "إدارة الأدوار والصلاحيات"),
]


def upgrade() -> None:
    bind = op.get_bind()
    for code, name_ar in PERMISSIONS:
        bind.execute(
            sa.text(
                "INSERT INTO permissions (code, name_ar) VALUES (:code, :name_ar) "
                "ON CONFLICT (code) DO UPDATE SET name_ar = excluded.name_ar"
            ),
            {"code": code, "name_ar": name_ar},
        )

    for role_name in ("admin", "administrator", "مدير النظام", "sub_admin", "نائب المدير", "مشرف الفرع"):
        bind.execute(
            sa.text(
                "INSERT INTO roles (name, is_active) VALUES (:name, true) "
                "ON CONFLICT (name) DO NOTHING"
            ),
            {"name": role_name},
        )

    admin_ids = bind.execute(
        sa.text("SELECT id FROM roles WHERE name IN ('admin','administrator','مدير النظام')")
    ).fetchall()
    permission_ids = bind.execute(sa.text("SELECT id FROM permissions")).fetchall()
    for (role_id,) in admin_ids:
        for (permission_id,) in permission_ids:
            bind.execute(
                sa.text(
                    "INSERT INTO role_permissions (role_id, permission_id) "
                    "VALUES (:role_id, :permission_id) ON CONFLICT DO NOTHING"
                ),
                {"role_id": role_id, "permission_id": permission_id},
            )

    # نائب المدير ومشرف الفرع يستطيعان إدارة المستخدمين/الفروع حسب النطاق
    # لاحقًا يمكن توسيع صلاحياتهما من شاشة الأدوار دون تعديل الكود.
    limited = bind.execute(
        sa.text("SELECT id FROM roles WHERE name IN ('sub_admin','نائب المدير','مشرف الفرع')")
    ).fetchall()
    limited_permissions = bind.execute(
        sa.text("SELECT id FROM permissions WHERE code IN ('users.manage','branches.manage')")
    ).fetchall()
    for (role_id,) in limited:
        for (permission_id,) in limited_permissions:
            bind.execute(
                sa.text(
                    "INSERT INTO role_permissions (role_id, permission_id) "
                    "VALUES (:role_id, :permission_id) ON CONFLICT DO NOTHING"
                ),
                {"role_id": role_id, "permission_id": permission_id},
            )


def downgrade() -> None:
    bind = op.get_bind()
    permission_codes = [code for code, _ in PERMISSIONS]
    for code in permission_codes:
        bind.execute(sa.text("DELETE FROM permissions WHERE code = :code"), {"code": code})
    for role_name in ("sub_admin", "نائب المدير", "مشرف الفرع"):
        bind.execute(sa.text("DELETE FROM roles WHERE name = :name"), {"name": role_name})
