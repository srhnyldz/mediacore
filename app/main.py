from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.config import settings

web_dir = Path(__file__).resolve().parent / "web"
assets_dir = web_dir / "assets"

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.include_router(api_router, prefix=settings.api_prefix)
app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")


@app.get("/health", tags=["system"])
async def healthcheck() -> dict[str, str]:
    # Basit health endpoint'i Coolify ve smoke testler icin faydalidir.
    return {"status": "ok", "version": settings.app_version}


@app.get("/", include_in_schema=False)
async def serve_frontend() -> FileResponse:
    # Faz 1.2 MVP arayuzunu tek sayfa olarak servis ediyoruz.
    return FileResponse(web_dir / "index.html")
