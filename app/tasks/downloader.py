from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from celery import states
from celery.exceptions import Ignore
from yt_dlp import YoutubeDL

from app.core.celery_app import celery_app
from app.core.config import settings
from app.schemas.task import DownloadTaskRequest
from app.utils.filename import build_unique_path, sanitize_filename


@celery_app.task(
    bind=True,
    name="app.tasks.downloader.download_task",
)
def download_task(self: Any, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        request = DownloadTaskRequest.model_validate(payload)
        task_dir = Path(settings.download_root) / self.request.id
        task_dir.mkdir(parents=True, exist_ok=True)

        self.update_state(
            state=states.STARTED,
            meta={
                "progress_percent": 0,
                "message": "Indirme hazirlaniyor.",
                "result": None,
            },
        )

        progress_hook = _build_progress_hook(task=self, source_url=str(request.url))
        ydl_options = _build_download_options(task_dir=task_dir, progress_hook=progress_hook)

        with YoutubeDL(ydl_options) as ydl:
            info = ydl.extract_info(str(request.url), download=True)
            downloaded_path = _resolve_downloaded_file(info=info, task_dir=task_dir)

        safe_name = sanitize_filename(downloaded_path.name)
        safe_path = downloaded_path

        # Yalnizca hedef isim degisiyorsa unique path uretiyoruz.
        if downloaded_path.name != safe_name:
            safe_path = build_unique_path(downloaded_path.with_name(safe_name))
            downloaded_path.rename(safe_path)

        file_size = safe_path.stat().st_size if safe_path.exists() else None

        return {
            "progress_percent": 100,
            "message": "Indirme tamamlandi.",
            "result": {
                "file_path": str(safe_path),
                "file_name": safe_path.name,
                "file_size_bytes": file_size,
                "source_url": str(request.url),
            },
        }
    except Exception as exc:
        error_payload = {
            "progress_percent": 0,
            "message": "Indirme basarisiz oldu.",
            "result": None,
            "error_code": "DOWNLOAD_FAILED",
            "error_message": str(exc),
        }
        # Ignore ile cikarak custom failure payload'ini Redis'te koruyoruz.
        self.backend.store_result(self.request.id, error_payload, state=states.FAILURE)
        raise Ignore() from exc


def _build_progress_hook(task: Any, source_url: str):
    def progress_hook(data: dict[str, Any]) -> None:
        status = data.get("status", "downloading")
        percent = _calculate_progress_percent(data)
        file_path = data.get("filename")

        result_payload = None
        if file_path:
            path_obj = Path(file_path)
            result_payload = {
                "file_path": str(path_obj),
                "file_name": path_obj.name,
                "file_size_bytes": data.get("downloaded_bytes"),
                "source_url": source_url,
            }

        if status == "finished":
            message = "Dosya sonlandiriliyor."
        else:
            message = "Icerik indiriliyor."

        task.update_state(
            state="PROGRESS",
            meta={
                "progress_percent": percent,
                "message": message,
                "result": result_payload,
            },
        )

    return progress_hook


def _build_download_options(task_dir: Path, progress_hook):
    return {
        "outtmpl": str(task_dir / "%(title)s-%(id)s.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "progress_hooks": [progress_hook],
        "restrictfilenames": False,
        "overwrites": True,
    }


def _calculate_progress_percent(data: dict[str, Any]) -> int:
    if data.get("status") == "finished":
        return 95

    downloaded = data.get("downloaded_bytes") or 0
    total = data.get("total_bytes") or data.get("total_bytes_estimate") or 0

    if total:
        return max(1, min(99, int(downloaded * 100 / total)))

    percent_text = data.get("_percent_str")
    if isinstance(percent_text, str):
        normalized = re.sub(r"[^0-9.]", "", percent_text)
        if normalized:
            return max(1, min(99, int(float(normalized))))

    return 0


def _resolve_downloaded_file(info: dict[str, Any], task_dir: Path) -> Path:
    candidates = [
        info.get("_filename"),
        *((download.get("filepath"),) for download in info.get("requested_downloads", [])),
    ]

    for candidate in candidates:
        if isinstance(candidate, tuple):
            candidate = candidate[0]
        if not candidate:
            continue
        path_obj = Path(candidate)
        if path_obj.exists():
            return path_obj

    existing_files = [path for path in task_dir.iterdir() if path.is_file()]
    if existing_files:
        return max(existing_files, key=lambda item: item.stat().st_mtime)

    raise FileNotFoundError("Indirilen dosya bulunamadi.")
