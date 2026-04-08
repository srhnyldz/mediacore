from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

from celery import states
from celery.exceptions import Ignore
from yt_dlp import YoutubeDL

from app.core.celery_app import celery_app
from app.core.config import settings
from app.schemas.task import DownloadTaskRequest
from app.utils.filename import build_unique_path, sanitize_filename

AUDIO_OUTPUT_FORMATS = {"mp3", "wav"}
VIDEO_OUTPUT_FORMATS = {"avi", "mp4", "webm"}
DEFAULT_OUTPUT_FORMAT = "avi"
IGNORED_DOWNLOAD_SUFFIXES = {".part", ".webp", ".ytdl"}


@celery_app.task(
    bind=True,
    name="app.tasks.downloader.download_task",
)
def download_task(self: Any, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        request = DownloadTaskRequest.model_validate(payload)
        task_dir = Path(settings.download_root) / self.request.id
        task_dir.mkdir(parents=True, exist_ok=True)
        output_format = _normalize_output_format(request.output_format)

        self.update_state(
            state=states.STARTED,
            meta={
                "progress_percent": 0,
                "message": "Indirme hazirlaniyor.",
                "result": None,
            },
        )

        progress_hook = _build_progress_hook(task=self, source_url=str(request.url))
        ydl_options = _build_download_options(
            task_dir=task_dir,
            progress_hook=progress_hook,
            output_format=output_format,
        )

        with YoutubeDL(ydl_options) as ydl:
            info = ydl.extract_info(str(request.url), download=True)
            downloaded_path = _resolve_downloaded_file(
                info=info,
                task_dir=task_dir,
                output_format=output_format,
            )

        if _should_convert_media(downloaded_path, output_format):
            self.update_state(
                state="PROGRESS",
                meta={
                    "progress_percent": 97,
                    "message": "Dosya donusturuluyor.",
                    "result": {
                        "file_path": str(downloaded_path),
                        "file_name": downloaded_path.name,
                        "file_size_bytes": downloaded_path.stat().st_size
                        if downloaded_path.exists()
                        else None,
                        "source_url": str(request.url),
                    },
                },
            )
            downloaded_path = _convert_media_file(
                source_path=downloaded_path,
                task_dir=task_dir,
                output_format=output_format,
            )

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
                "output_format": output_format,
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
        # Celery'nin exception serilestirme akisi ile cakismamak icin
        # hata payload'ini state metadata olarak yazip gorevi ignore ediyoruz.
        self.update_state(state="ERROR", meta=error_payload)
        raise Ignore()


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


def _build_download_options(
    task_dir: Path,
    progress_hook,
    output_format: str,
) -> dict[str, Any]:
    options: dict[str, Any] = {
        "outtmpl": str(task_dir / "%(title)s-%(id)s.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "progress_hooks": [progress_hook],
        "restrictfilenames": False,
        "overwrites": True,
    }

    if output_format in AUDIO_OUTPUT_FORMATS:
        # Ses ciktilarinda en iyi ses akisini indirip donusumu kendimiz yonetiyoruz.
        options["format"] = "bestaudio/best"
        return options

    if output_format == "webm":
        # WebM istenince once zaten webm olan stream'leri tercih ederek agir yeniden encode'u azaltiriz.
        options["format"] = (
            "bestvideo[ext=webm]+bestaudio[ext=webm]/"
            "best[ext=webm]/bestvideo*+bestaudio/best"
        )
        options["merge_output_format"] = "webm"
        return options

    if output_format in VIDEO_OUTPUT_FORMATS:
        # Ayrik ses/video stream kaynaklarinda once guvenli bir ortak konteynira merge ediyoruz.
        options["format"] = "bestvideo*+bestaudio/best"
        options["merge_output_format"] = "mp4"

    return options


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


def _normalize_output_format(output_format: str | None) -> str:
    return (output_format or DEFAULT_OUTPUT_FORMAT).strip().lower()


def _resolve_downloaded_file(
    info: dict[str, Any],
    task_dir: Path,
    output_format: str,
) -> Path:
    preferred_suffix = f".{output_format.lower()}"
    existing_files = [
        path
        for path in task_dir.iterdir()
        if path.is_file() and not _is_ignored_download_file(path)
    ]
    preferred_existing = [
        path
        for path in existing_files
        if path.suffix.lower() == preferred_suffix and ".f" not in path.stem
    ]
    if preferred_existing:
        return max(preferred_existing, key=lambda item: item.stat().st_mtime)

    merged_candidates = [
        path for path in existing_files if ".f" not in path.stem and ".temp." not in path.name
    ]
    if merged_candidates:
        return max(merged_candidates, key=lambda item: item.stat().st_mtime)

    candidates = [
        info.get("_filename"),
        *((download.get("filepath"),) for download in info.get("requested_downloads", [])),
    ]

    preferred_candidates: list[Path] = []
    for candidate in candidates:
        if isinstance(candidate, tuple):
            candidate = candidate[0]
        if not candidate:
            continue
        path_obj = Path(candidate)
        if not path_obj.exists() or _is_ignored_download_file(path_obj):
            continue
        if path_obj.suffix.lower() == preferred_suffix:
            preferred_candidates.append(path_obj)
            continue
        return path_obj

    if preferred_candidates:
        return max(preferred_candidates, key=lambda item: item.stat().st_mtime)

    if existing_files:
        return max(existing_files, key=lambda item: item.stat().st_mtime)

    raise FileNotFoundError("Indirilen dosya bulunamadi.")


def _is_ignored_download_file(path: Path) -> bool:
    suffix = path.suffix.lower()
    if suffix in IGNORED_DOWNLOAD_SUFFIXES:
        return True
    return ".temp." in path.name


def _should_convert_media(source_path: Path, output_format: str) -> bool:
    return source_path.suffix.lower() != f".{output_format}"


def _convert_media_file(source_path: Path, task_dir: Path, output_format: str) -> Path:
    target_path = build_unique_path(task_dir / f"{source_path.stem}.{output_format}")
    command = _build_ffmpeg_command(
        source_path=source_path,
        target_path=target_path,
        output_format=output_format,
    )

    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        stderr_tail = (completed.stderr or "").strip().splitlines()[-8:]
        message = " | ".join(stderr_tail) if stderr_tail else "Unknown FFmpeg error."
        raise RuntimeError(f"FFmpeg conversion failed: {message}")

    return target_path


def _build_ffmpeg_command(
    source_path: Path,
    target_path: Path,
    output_format: str,
) -> list[str]:
    base_command = ["ffmpeg", "-y", "-i", str(source_path)]

    if output_format == "avi":
        return [
            *base_command,
            "-c:v",
            "mpeg4",
            "-q:v",
            "5",
            "-c:a",
            "libmp3lame",
            "-b:a",
            "192k",
            str(target_path),
        ]

    if output_format == "mp4":
        return [
            *base_command,
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "23",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            str(target_path),
        ]

    if output_format == "webm":
        return [
            *base_command,
            "-c:v",
            "libvpx",
            "-deadline",
            "realtime",
            "-cpu-used",
            "8",
            "-b:v",
            "0",
            "-c:a",
            "libopus",
            "-b:a",
            "128k",
            "-threads",
            "4",
            str(target_path),
        ]

    if output_format == "mp3":
        return [
            *base_command,
            "-vn",
            "-c:a",
            "libmp3lame",
            "-b:a",
            "192k",
            str(target_path),
        ]

    if output_format == "wav":
        return [
            *base_command,
            "-vn",
            "-c:a",
            "pcm_s16le",
            str(target_path),
        ]

    raise ValueError(f"Unsupported output format: {output_format}")
