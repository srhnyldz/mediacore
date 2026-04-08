from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.services.cleanup_service import cleanup_expired_downloads


def test_cleanup_expired_downloads_removes_old_task_directories(tmp_path: Path) -> None:
    old_dir = tmp_path / "old-task"
    old_dir.mkdir()
    old_file = old_dir / "video.mp4"
    old_file.write_bytes(b"old-data")

    recent_dir = tmp_path / "recent-task"
    recent_dir.mkdir()
    recent_file = recent_dir / "video.mp4"
    recent_file.write_bytes(b"recent-data")

    old_timestamp = (datetime.now(tz=UTC) - timedelta(hours=48)).timestamp()
    recent_timestamp = datetime.now(tz=UTC).timestamp()

    old_file.touch()
    recent_file.touch()
    old_dir.touch()
    recent_dir.touch()

    import os

    os.utime(old_dir, (old_timestamp, old_timestamp))
    os.utime(old_file, (old_timestamp, old_timestamp))
    os.utime(recent_dir, (recent_timestamp, recent_timestamp))
    os.utime(recent_file, (recent_timestamp, recent_timestamp))

    result = cleanup_expired_downloads(
        download_root=tmp_path,
        max_age_hours=24,
        batch_limit=10,
        now=datetime.now(tz=UTC),
    )

    assert result["deleted_count"] == 1
    assert str(old_dir) in result["deleted_paths"]
    assert result["freed_bytes"] == len(b"old-data")
    assert not old_dir.exists()
    assert recent_dir.exists()


def test_cleanup_expired_downloads_respects_batch_limit(tmp_path: Path) -> None:
    now = datetime.now(tz=UTC)
    old_timestamp = (now - timedelta(hours=48)).timestamp()

    import os

    for index in range(3):
        task_dir = tmp_path / f"task-{index}"
        task_dir.mkdir()
        file_path = task_dir / "asset.bin"
        file_path.write_bytes(b"x")
        os.utime(task_dir, (old_timestamp, old_timestamp))
        os.utime(file_path, (old_timestamp, old_timestamp))

    result = cleanup_expired_downloads(
        download_root=tmp_path,
        max_age_hours=24,
        batch_limit=2,
        now=now,
    )

    assert result["deleted_count"] == 2
