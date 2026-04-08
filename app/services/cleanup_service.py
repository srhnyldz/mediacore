from __future__ import annotations

import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from app.core.config import settings


def cleanup_expired_downloads(
    *,
    download_root: Path | None = None,
    max_age_hours: int | None = None,
    batch_limit: int | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    root = download_root or Path(settings.download_root)
    max_age = max_age_hours or settings.cleanup_max_age_hours
    limit = batch_limit or settings.cleanup_batch_limit
    current_time = now or datetime.now(tz=UTC)
    cutoff = current_time - timedelta(hours=max_age)

    if not root.exists():
        return {
            "deleted_count": 0,
            "freed_bytes": 0,
            "deleted_paths": [],
            "cutoff_iso": cutoff.isoformat(),
        }

    deleted_paths: list[str] = []
    freed_bytes = 0

    candidate_dirs = sorted(
        [path for path in root.iterdir() if path.is_dir()],
        key=lambda item: item.stat().st_mtime,
    )

    for path in candidate_dirs:
        if len(deleted_paths) >= limit:
            break

        modified_at = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
        if modified_at >= cutoff:
            continue

        freed_bytes += _calculate_directory_size(path)
        shutil.rmtree(path, ignore_errors=False)
        deleted_paths.append(str(path))

    return {
        "deleted_count": len(deleted_paths),
        "freed_bytes": freed_bytes,
        "deleted_paths": deleted_paths,
        "cutoff_iso": cutoff.isoformat(),
    }


def _calculate_directory_size(path: Path) -> int:
    total = 0
    for child in path.rglob("*"):
        if child.is_file():
            total += child.stat().st_size
    return total
