from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.config import settings


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.include_router(api_router, prefix=settings.api_prefix)


@app.get("/health", tags=["system"])
async def healthcheck() -> dict[str, str]:
    # Basit health endpoint'i Coolify ve smoke testler icin faydalidir.
    return {"status": "ok", "version": settings.app_version}

