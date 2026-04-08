from __future__ import annotations

import subprocess
from pathlib import Path

from app.utils.filename import build_unique_path

AUDIO_OUTPUT_FORMATS = {"mp3", "wav"}
VIDEO_OUTPUT_FORMATS = {"avi", "mp4", "webm"}
SUPPORTED_OUTPUT_FORMATS = AUDIO_OUTPUT_FORMATS | VIDEO_OUTPUT_FORMATS
DEFAULT_OUTPUT_FORMAT = "avi"


def normalize_output_format(output_format: str | None) -> str:
    return (output_format or DEFAULT_OUTPUT_FORMAT).strip().lower()


def detect_output_format_from_path(file_path: str | Path | None) -> str | None:
    if not file_path:
        return None

    path_obj = Path(file_path)
    suffix = path_obj.suffix.lower().removeprefix(".")
    return suffix or None


def should_convert_media(source_path: Path, output_format: str) -> bool:
    return source_path.suffix.lower() != f".{output_format}"


def convert_media_file(source_path: Path, task_dir: Path, output_format: str) -> Path:
    target_path = build_unique_path(task_dir / f"{source_path.stem}.{output_format}")
    command = build_ffmpeg_command(
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


def build_ffmpeg_command(
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
