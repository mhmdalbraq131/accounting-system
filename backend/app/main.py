from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.accounts import router as accounts_router
from app.api.ar_ap import router as ar_ap_router
from app.api.accounting_controls import router as accounting_controls_router
from app.api.branches import router as branches_router
from app.api.currencies import router as currencies_router
from app.api.financial import router as financial_router
from app.api.auth import router as auth_router
from app.api.dashboard import router as dashboard_router
from app.api.expenses import router as expenses_router
from app.api.journals import router as journals_router
from app.api.reports import router as reports_router
from app.api.party_services_report import router as party_services_report_router
from app.api.parties import router as parties_router
from app.api.settings import router as settings_router
from app.api.travel import router as travel_router
from app.api.hajj import router as hajj_router, umrah_router
from app.api.services import router as services_router
from app.api.vouchers import router as vouchers_router
from app.api.users import router as users_router
from app.core.config import settings
from app.db.schema_compat import ensure_schema_compatibility

ensure_schema_compatibility()

app = FastAPI(
    title="Accounting System API",
    version="0.9.2",
    description="واجهة API لنظام محاسبي مستقل لوكالة الحج والعمرة والسفر",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_origin_regex=(
        r"^https?://(?:localhost|127\.0\.0\.1|10(?:\.\d{1,3}){3}|192\.168(?:\.\d{1,3}){2}|"
        r"172\.(?:1[6-9]|2\d|3[0-1])(?:\.\d{1,3}){2})(?::\d+)?$"
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(accounts_router, prefix="/api/v1")
app.include_router(ar_ap_router, prefix="/api/v1")
app.include_router(accounting_controls_router, prefix="/api/v1")
app.include_router(branches_router, prefix="/api/v1")
app.include_router(currencies_router, prefix="/api/v1")
app.include_router(financial_router, prefix="/api/v1")
app.include_router(parties_router, prefix="/api/v1")
app.include_router(vouchers_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(travel_router, prefix="/api/v1")
app.include_router(hajj_router, prefix="/api/v1")
app.include_router(umrah_router, prefix="/api/v1")
app.include_router(services_router, prefix="/api/v1")
app.include_router(settings_router, prefix="/api/v1")
app.include_router(dashboard_router, prefix="/api/v1")
app.include_router(expenses_router, prefix="/api/v1")
app.include_router(journals_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")
app.include_router(party_services_report_router, prefix="/api/v1")

@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}

@app.get("/api/v1", tags=["system"])
def api_info() -> dict[str, str]:
    return {"name": "Accounting System API", "version": "v1"}
