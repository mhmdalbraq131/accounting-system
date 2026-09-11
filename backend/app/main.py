from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.accounts import router as accounts_router
from app.api.branches import router as branches_router
from app.api.auth import router as auth_router
from app.api.dashboard import router as dashboard_router
from app.api.parties import router as parties_router
from app.api.settings import router as settings_router
from app.api.travel import router as travel_router
from app.api.vouchers import router as vouchers_router
from app.core.config import settings

app = FastAPI(
    title="Accounting System API",
    version="0.7.0",
    description="واجهة API لنظام محاسبي مستقل لوكالة الحج والعمرة والسفر",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(accounts_router, prefix="/api/v1")
app.include_router(branches_router, prefix="/api/v1")
app.include_router(parties_router, prefix="/api/v1")
app.include_router(vouchers_router, prefix="/api/v1")
app.include_router(travel_router, prefix="/api/v1")
app.include_router(settings_router, prefix="/api/v1")
app.include_router(dashboard_router, prefix="/api/v1")


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1", tags=["system"])
def api_info() -> dict[str, str]:
    return {"name": "Accounting System API", "version": "v1"}
