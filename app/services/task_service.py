from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any
from uuid import uuid4

from celery import states
from fastapi import UploadFile

from app.core.celery_app import celery_app
from app.core.config import settings
from app.schemas.task import (
    ConvertTaskPayload,
    ConvertTaskRequest,
    DownloadTaskAcceptedResponse,
    DownloadTaskRequest,
    DownloadTaskResult,
    TaskAcceptedResponse,
    TaskKind,
    TaskState,
    TaskStatusResponse,
)
from app.tasks.converter import convert_task
from app.tasks.downloader import download_task
from app.utils.filename import build_unique_path, sanitize_filename

TERMINAL_FAILURE_STATES = {states.FAILURE, "ERROR"}


class TaskNotFoundError(Exception):
    def __init__(self, task_id: str) -> None:
        super().__init__(f"Gorev bulunamadi: {task_id}")


class TaskConflictError(Exception):
    pass


def enqueue_download_task(
    payload: DownloadTaskRequest,
) -> DownloadTaskAcceptedResponse:
    task_kwargs = {"payload": payload.model_dump(mode="json")}

    async_result = download_task.apply_async(
        kwargs=task_kwargs,
        queue=settings.celery_download_queue,
    )

    _seed_pending_state(
        task_id=async_result.id,
        message="Gorev kuyruga alindi.",
        task_kind=TaskKind.DOWNLOAD,
    )

    return TaskAcceptedResponse(
        task_id=async_result.id,
        status=TaskState.PENDING,
        message="Gorev kuyruga alindi.",
        task_kind=TaskKind.DOWNLOAD,
    )


def enqueue_convert_upload_task(
    *,
    request_data: ConvertTaskRequest,
    upload_file: UploadFile,
) -> TaskAcceptedResponse:
    task_id = str(uuid4())
    task_dir = Path(settings.download_root) / task_id
    task_dir.mkdir(parents=True, exist_ok=True)

    staged_file_path = _persist_uploaded_file(
        upload_file=upload_file,
        task_dir=task_dir,
    )

    payload = ConvertTaskPayload(
        conversion_type=request_data.conversion_type,
        output_format=request_data.output_format,
        source_file_path=str(staged_file_path),
        source_file_name=staged_file_path.name,
        source_media_type=upload_file.content_type,
    )

    async_result = convert_task.apply_async(
        kwargs={"payload": payload.model_dump(mode="json")},
        queue=settings.celery_convert_queue,
        task_id=task_id,
    )

    _seed_pending_state(
        task_id=async_result.id,
        message="Convert gorevi kuyruga alindi.",
        task_kind=TaskKind.CONVERT,
    )

    return TaskAcceptedResponse(
        task_id=async_result.id,
        status=TaskState.PENDING,
        message="Convert gorevi kuyruga alindi.",
        task_kind=TaskKind.CONVERT,
    )


def get_task_status(task_id: str) -> TaskStatusResponse:
    meta = celery_app.backend.get_task_meta(task_id)

    if _is_unknown_task(meta):
        raise TaskNotFoundError(task_id)

    state = meta.get("status", states.PENDING)
    payload = meta.get("result")

    if state in TERMINAL_FAILURE_STATES:
        return _build_failure_response(task_id=task_id, payload=payload)

    response_payload = payload if isinstance(payload, dict) else {}
    result_payload = response_payload.get("result")

    return TaskStatusResponse(
        task_id=task_id,
        status=str(state),
        task_kind=response_payload.get("task_kind"),
        progress_percent=int(response_payload.get("progress_percent", 0)),
        message=response_payload.get("message", _default_message_for_state(str(state))),
        result=_build_result(result_payload),
        error_code=response_payload.get("error_code"),
        error_message=response_payload.get("error_message"),
    )


def _persist_uploaded_file(*, upload_file: UploadFile, task_dir: Path) -> Path:
    original_name = upload_file.filename or "upload.bin"
    safe_name = sanitize_filename(original_name)
    staged_path = build_unique_path(task_dir / safe_name)

    upload_file.file.seek(0)
    with staged_path.open("wb") as target:
        shutil.copyfileobj(upload_file.file, target)

    if staged_path.stat().st_size == 0:
        staged_path.unlink(missing_ok=True)
        raise TaskConflictError("Uploaded file is empty.")

    return staged_path


def _is_unknown_task(meta: dict[str, Any] | None) -> bool:
    if meta is None:
        return True

    state = meta.get("status")
    result = meta.get("result")
    return state == states.PENDING and result is None


def _build_failure_response(task_id: str, payload: Any) -> TaskStatusResponse:
    if isinstance(payload, dict):
        return TaskStatusResponse(
            task_id=task_id,
            status=states.FAILURE,
            task_kind=payload.get("task_kind"),
            progress_percent=int(payload.get("progress_percent", 0)),
            message=payload.get("message", "Indirme basarisiz oldu."),
            result=_build_result(payload.get("result")),
            error_code=payload.get("error_code", "DOWNLOAD_FAILED"),
            error_message=payload.get("error_message", "Bilinmeyen islem hatasi."),
        )

    return TaskStatusResponse(
        task_id=task_id,
        status=states.FAILURE,
        progress_percent=0,
        message="Islem basarisiz oldu.",
        error_code="TASK_FAILED",
        error_message=str(payload),
    )


def _build_result(payload: Any) -> DownloadTaskResult | None:
    if not isinstance(payload, dict):
        return None

    normalized_payload = dict(payload)
    file_name = normalized_payload.get("file_name")
    file_path = normalized_payload.get("file_path")
    task_id = _extract_task_id_from_path(file_path)

    if task_id and file_name:
        normalized_payload["download_url"] = f"{settings.api_prefix}/tasks/{task_id}/download"

    return DownloadTaskResult.model_validate(normalized_payload)


def _default_message_for_state(state: str) -> str:
    messages = {
        TaskState.PENDING.value: "Gorev kuyrukta bekliyor.",
        TaskState.STARTED.value: "Gorev baslatildi.",
        TaskState.PROGRESS.value: "Gorev isleniyor.",
        TaskState.SUCCESS.value: "Gorev tamamlandi.",
        TaskState.FAILURE.value: "Gorev basarisiz oldu.",
        "ERROR": "Gorev basarisiz oldu.",
    }
    return messages.get(state, "Gorev durumu alindi.")


def _extract_task_id_from_path(file_path: Any) -> str | None:
    if not isinstance(file_path, str):
        return None

    try:
        path_obj = Path(file_path)
        download_root = Path(settings.download_root)
        relative_path = path_obj.relative_to(download_root)
    except (ValueError, TypeError):
        return None

    parts = relative_path.parts
    if not parts:
        return None

    return parts[0]


def _seed_pending_state(task_id: str, message: str, task_kind: TaskKind) -> None:
    celery_app.backend.store_result(
        task_id,
        {
            "progress_percent": 0,
            "message": message,
            "task_kind": task_kind.value,
            "result": None,
        },
        state=states.PENDING,
    )
