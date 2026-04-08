from typing import Any

from app.core.celery_app import celery_app


@celery_app.task(
    bind=True,
    name="app.tasks.converter.convert_task",
)
def convert_task(self: Any, payload: dict[str, Any]) -> dict[str, Any]:
    # Faz 1'de sadece mimari yer tutucu olarak kayitli tutulur.
    return {
        "progress_percent": 0,
        "message": "Convert gorevi Faz 2'de aktiflestirilecek.",
        "result": payload,
    }

