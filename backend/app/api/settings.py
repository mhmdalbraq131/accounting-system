from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db.session import get_db
from app.models.role import Role, UserRole
from app.models.settings import SystemSetting
from app.models.user import User

router = APIRouter(prefix="/settings", tags=["settings"])

DEFAULT_SETTINGS = [
    ("company_name", "وكالة الحج والعمرة", "string", "company", "اسم الوكالة"),
    ("company_phone", "", "string", "company", "رقم التواصل"),
    ("company_address", "", "string", "company", "عنوان الوكالة"),
    ("currency", "YER", "string", "financial", "العملة الأساسية"),
    ("currency_name_ar", "ريال يمني", "string", "financial", "اسم العملة بالعربية"),
    ("fiscal_year_start_month", "1", "integer", "financial", "شهر بداية السنة المالية"),
    ("voucher_prefix_receipt", "RV", "string", "financial", "بادئة سند القبض"),
    ("voucher_prefix_payment", "PV", "string", "financial", "بادئة سند الصرف"),
    ("voucher_prefix_transfer", "TV", "string", "financial", "بادئة سند التحويل"),
    ("default_program_type", "umrah", "string", "travel", "نوع البرنامج الافتراضي"),
    ("rtl", "true", "boolean", "interface", "اتجاه الواجهة من اليمين إلى اليسار"),
    ("date_format", "YYYY-MM-DD", "string", "interface", "تنسيق التاريخ"),
]


class SettingUpdate(BaseModel):
    value: str = Field(max_length=5000)


class SettingOut(BaseModel):
    key: str
    value: str
    value_type: str
    category: str
    description_ar: str | None
    is_editable: bool


def require_admin(user: User, db: Session) -> None:
    is_admin = db.scalar(
        select(Role.id)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user.id, Role.name.in_(["admin", "administrator", "مدير النظام"]))
    )
    if not is_admin:
        raise HTTPException(status_code=403, detail="صلاحية مدير النظام مطلوبة")


@router.get("", response_model=list[SettingOut])
def list_settings(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_admin(user, db)
    existing = {s.key: s for s in db.scalars(select(SystemSetting)).all()}
    changed = False
    for key, value, value_type, category, description in DEFAULT_SETTINGS:
        if key not in existing:
            db.add(SystemSetting(key=key, value=value, value_type=value_type, category=category, description_ar=description))
            changed = True
    if changed:
        db.commit()
    return db.scalars(select(SystemSetting).order_by(SystemSetting.category, SystemSetting.key)).all()


@router.put("/{key}", response_model=SettingOut)
def update_setting(key: str, payload: SettingUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_admin(user, db)
    setting = db.scalar(select(SystemSetting).where(SystemSetting.key == key))
    if not setting:
        raise HTTPException(status_code=404, detail="الإعداد غير موجود")
    if not setting.is_editable:
        raise HTTPException(status_code=403, detail="هذا الإعداد غير قابل للتعديل")
    if setting.value_type == "boolean" and payload.value.lower() not in {"true", "false"}:
        raise HTTPException(status_code=422, detail="القيمة يجب أن تكون true أو false")
    if setting.value_type == "integer":
        try:
            int(payload.value)
        except ValueError:
            raise HTTPException(status_code=422, detail="القيمة يجب أن تكون رقمًا صحيحًا")
    setting.value = payload.value
    db.commit()
    db.refresh(setting)
    return setting
