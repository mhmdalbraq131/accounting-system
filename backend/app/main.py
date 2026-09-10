from fastapi import FastAPI

app = FastAPI(
    title="Accounting System API",
    version="0.1.0",
    description="واجهة API للنظام المحاسبي المستقل",
)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1", tags=["system"])
def api_info() -> dict[str, str]:
    return {"name": "Accounting System API", "version": "v1"}
