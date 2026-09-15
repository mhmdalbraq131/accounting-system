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
    ("company_name", "وكالة مهراس للحج والعمرة والسفر", "string", "company", "اسم الوكالة"),
    ("company_phone", "", "string", "company", "رقم التواصل"),
    ("company_address", "", "string", "company", "عنوان الوكالة"),
    ("company_email", "", "string", "company", "البريد الإلكتروني"),
    ("company_website", "", "string", "company", "الموقع الإلكتروني"),
    ("company_logo_url", "", "string", "company", "رابط/مسار شعار الوكالة"),
    ("print_footer", "شكرًا لثقتكم بنا — نسعد بخدمتكم دائمًا", "string", "company", "عبارة تذييل المستندات المطبوعة"),
    ("print_show_logo", "true", "boolean", "company", "إظهار شعار الوكالة في الطباعة"),
    ("print_show_contact", "true", "boolean", "company", "إظهار بيانات التواصل في الطباعة"),
    ("currency", "YER", "string", "financial", "العملة الأساسية (تُدار من شاشة العملات)"),
    ("currency_name_ar", "ريال يمني", "string", "financial", "اسم العملة الأساسية بالعربية"),
    ("fiscal_year_start_month", "1", "integer", "financial", "شهر بداية السنة المالية"),
    ("voucher_prefix_receipt", "RV", "string", "financial", "بادئة سند القبض"),
    ("voucher_prefix_payment", "PV", "string", "financial", "بادئة سند الصرف"),
    ("voucher_prefix_transfer", "TV", "string", "financial", "بادئة سند التحويل"),
    ("travel_revenue_account_id", "", "integer", "travel_accounting", "حساب إيراد الحج والعمرة"),
    ("travel_cost_account_id", "", "integer", "travel_accounting", "حساب تكلفة الحج والعمرة"),
    ("visa_revenue_account_id", "", "integer", "travel_accounting", "حساب إيراد خدمات التأشيرات"),
    ("visa_cost_account_id", "", "integer", "travel_accounting", "حساب تكلفة خدمات التأشيرات"),
    ("flight_revenue_account_id", "", "integer", "service_accounting", "حساب إيراد الطيران"),
    ("flight_cost_account_id", "", "integer", "service_accounting", "حساب تكلفة الطيران"),
    ("bus_revenue_account_id", "", "integer", "service_accounting", "حساب إيراد الباصات"),
    ("bus_cost_account_id", "", "integer", "service_accounting", "حساب تكلفة الباصات"),
    ("visit_revenue_account_id", "", "integer", "service_accounting", "حساب إيراد الزيارات"),
    ("visit_cost_account_id", "", "integer", "service_accounting", "حساب تكلفة الزيارات"),
    ("work_visa_revenue_account_id", "", "integer", "service_accounting", "حساب إيراد فيز العمل"),
    ("work_visa_cost_account_id", "", "integer", "service_accounting", "حساب تكلفة فيز العمل"),
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


class BrandingOut(BaseModel):
    company_name: str
    company_phone: str
    company_address: str
    company_email: str
    company_website: str
    company_logo_url: str
    print_footer: str
    print_show_logo: bool
    print_show_contact: bool


def require_admin(user: User, db: Session) -> None:
    is_admin = db.scalar(
        select(Role.id)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user.id, Role.name.in_(["admin", "administrator", "مدير النظام"]))
    )
    if not is_admin:
        raise HTTPException(status_code=403, detail="صلاحية مدير النظام مطلوبة")


def _ensure_defaults(db: Session) -> dict[str, SystemSetting]:
    existing = {s.key: s for s in db.scalars(select(SystemSetting)).all()}
    changed = False
    for key, value, value_type, category, description in DEFAULT_SETTINGS:
        if key not in existing:
            item = SystemSetting(key=key, value=value, value_type=value_type, category=category, description_ar=description)
            db.add(item)
            existing[key] = item
            changed = True
    if changed:
        db.commit()
    return existing


def _branding(existing: dict[str, SystemSetting]) -> BrandingOut:
    def value(key: str, default: str = "") -> str:
        return existing.get(key).value if existing.get(key) else default

    return BrandingOut(
        company_name=value("company_name", "وكالة مهراس للحج والعمرة والسفر"),
        company_phone=value("company_phone"),
        company_address=value("company_address"),
        company_email=value("company_email"),
        company_website=value("company_website"),
        company_logo_url=value("company_logo_url"),
        print_footer=value("print_footer", "شكرًا لثقتكم بنا — نسعد بخدمتكم دائمًا"),
        print_show_logo=value("print_show_logo", "true").lower() == "true",
        print_show_contact=value("print_show_contact", "true").lower() == "true",
    )


@router.get("/branding", response_model=BrandingOut)
def get_branding(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _branding(_ensure_defaults(db))


@router.get("", response_model=list[SettingOut])
def list_settings(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_admin(user, db)
    existing = _ensure_defaults(db)
    return sorted(existing.values(), key=lambda s: (s.category, s.key))


@router.put("/{key}", response_model=SettingOut)
def update_setting(key: str, payload: SettingUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_admin(user, db)
    if key in {"currency", "currency_name_ar"}:
        raise HTTPException(status_code=409, detail="العملة الأساسية تُدار من شاشة العملات ولا يمكن تغييرها من الإعدادات العامة")
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
