from __future__ import annotations

from typing import Any

from app.core.celery_app import celery_app
from app.services.cleanup_service import cleanup_expired_downloads


@celery_app.task(
    bind=True,
    name="app.tasks.maintenance.cleanup_expired_downloads_task",
)
def cleanup_expired_downloads_task(self: Any) -> dict[str, Any]:
    # Bu gorev cron ya da scheduler ile tetiklenmeye hazir tutulur.
    return cleanup_expired_downloads()
