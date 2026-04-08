from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from redis import Redis

from app.core.config import settings
from app.services.redis_client import get_redis_client


def ensure_download_root() -> Path:
    download_root = Path(settings.download_root)
    download_root.mkdir(parents=True, exist_ok=True)
    return download_root


def get_readiness_status(redis_client: Redis | None = None) -> dict[str, Any]:
    checks: dict[str, dict[str, Any]] = {}
    ready = True

    download_root = ensure_download_root()
    storage_ready = download_root.exists() and download_root.is_dir() and os.access(
        download_root,
        os.W_OK,
    )
    checks["storage"] = {
        "ok": storage_ready,
        "path": str(download_root),
    }
    ready = ready and storage_ready

    client = redis_client or get_redis_client()
    try:
        redis_ok = bool(client.ping())
        checks["redis"] = {"ok": redis_ok}
        ready = ready and redis_ok
    except Exception as exc:  # pragma: no cover - gercek runtime savunmasi
        checks["redis"] = {"ok": False, "error": str(exc)}
        ready = False

    return {
        "status": "ready" if ready else "degraded",
        "version": settings.app_version,
        "checks": checks,
    }
