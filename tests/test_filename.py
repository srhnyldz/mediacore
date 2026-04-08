from pathlib import Path

from app.utils.filename import build_unique_path, sanitize_filename


def test_sanitize_filename_keeps_extension() -> None:
    sanitized = sanitize_filename("Merhaba Dunya!!.mp4")

    assert sanitized == "Merhaba-Dunya.mp4"


def test_build_unique_path_generates_incremented_name(tmp_path: Path) -> None:
    existing = tmp_path / "sample.mp4"
    existing.write_text("data", encoding="utf-8")

    unique = build_unique_path(existing)

    assert unique.name == "sample-1.mp4"

