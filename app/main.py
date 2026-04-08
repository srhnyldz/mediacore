from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Response, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.config import settings
from app.services.system_service import ensure_download_root, get_readiness_status

web_dir = Path(__file__).resolve().parent / "web"
assets_dir = web_dir / "assets"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    ensure_download_root()
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.include_router(api_router, prefix=settings.api_prefix)
app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")


@app.get("/health", tags=["system"])
async def healthcheck() -> dict[str, str]:
    # Basit health endpoint'i Coolify ve smoke testler icin faydalidir.
    return {"status": "ok", "version": settings.app_version}


@app.get("/ready", tags=["system"])
async def readiness(response: Response) -> dict[str, object]:
    readiness_payload = get_readiness_status()
    if readiness_payload["status"] != "ready":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return readiness_payload


@app.get("/", include_in_schema=False)
async def serve_frontend() -> FileResponse:
    # Download panelini ayri sayfa olarak servis ediyoruz.
    return FileResponse(web_dir / "index.html")


@app.get("/convert", include_in_schema=False)
async def serve_converter_frontend() -> FileResponse:
    # Upload tabanli donusturucuyu ayri sayfada tutuyoruz.
    return FileResponse(web_dir / "convert.html")
