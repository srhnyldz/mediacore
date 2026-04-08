from __future__ import annotations

from pathlib import Path
from typing import Any

from celery import states
from celery.exceptions import Ignore

from app.core.celery_app import celery_app
from app.core.config import settings
from app.schemas.task import ConvertTaskPayload, TaskKind
from app.services.file_conversion_service import (
    convert_uploaded_file,
    validate_source_file_for_conversion,
)
from app.utils.filename import build_unique_path, sanitize_filename


@celery_app.task(
    bind=True,
    name="app.tasks.converter.convert_task",
)
def convert_task(self: Any, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        request = ConvertTaskPayload.model_validate(payload)
        source_path = Path(request.source_file_path).resolve(strict=True)
        task_dir = Path(settings.download_root) / self.request.id
        task_dir.mkdir(parents=True, exist_ok=True)

        self.update_state(
            state=states.STARTED,
            meta={
                "progress_percent": 0,
                "message": "Donusturme hazirlaniyor.",
                "task_kind": TaskKind.CONVERT.value,
                "result": None,
            },
        )

        validate_source_file_for_conversion(
            source_path=source_path,
            conversion_type=request.conversion_type,
        )

        self.update_state(
            state="PROGRESS",
            meta={
                "progress_percent": 20,
                "message": "Dosya yuklendi, donusturme baslatiliyor.",
                "task_kind": TaskKind.CONVERT.value,
                "result": {
                    "file_path": str(source_path),
                    "file_name": source_path.name,
                    "file_size_bytes": source_path.stat().st_size,
                    "source_file_name": request.source_file_name,
                    "conversion_type": request.conversion_type.value,
                    "output_format": request.output_format,
                },
            },
        )

        converted_path, generated_files_count = convert_uploaded_file(
            source_path=source_path,
            task_dir=task_dir,
            conversion_type=request.conversion_type,
            output_format=request.output_format,
        )

        safe_name = sanitize_filename(converted_path.name)
        safe_path = converted_path
        if converted_path.name != safe_name:
            safe_path = build_unique_path(converted_path.with_name(safe_name))
            converted_path.rename(safe_path)

        file_size = safe_path.stat().st_size if safe_path.exists() else None

        return {
            "progress_percent": 100,
            "message": "Donusturme tamamlandi.",
            "task_kind": TaskKind.CONVERT.value,
            "result": {
                "file_path": str(safe_path),
                "file_name": safe_path.name,
                "file_size_bytes": file_size,
                "output_format": request.output_format,
                "source_file_name": request.source_file_name,
                "conversion_type": request.conversion_type.value,
                "generated_files_count": generated_files_count,
            },
        }
    except Exception as exc:
        error_payload = {
            "progress_percent": 0,
            "message": "Donusturme basarisiz oldu.",
            "task_kind": TaskKind.CONVERT.value,
            "result": None,
            "error_code": "CONVERT_FAILED",
            "error_message": str(exc),
        }
        self.update_state(state="ERROR", meta=error_payload)
        raise Ignore()
