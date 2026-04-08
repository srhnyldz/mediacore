from pathlib import Path
from types import SimpleNamespace

from app.tasks import converter


class DummyTask:
    def __init__(self, task_id: str = "convert-task-123") -> None:
        self.request = SimpleNamespace(id=task_id)
        self.states = []

    def update_state(self, state: str, meta: dict) -> None:
        self.states.append({"state": state, "meta": meta})


def test_convert_task_returns_success_payload(monkeypatch, tmp_path: Path) -> None:
    dummy_task = DummyTask()
    source_dir = tmp_path / "convert-task-123"
    source_dir.mkdir(parents=True, exist_ok=True)
    source_path = source_dir / "picture.jpg"
    source_path.write_text("image", encoding="utf-8")

    monkeypatch.setattr(converter.settings, "download_root", str(tmp_path))
    monkeypatch.setattr(
        converter,
        "validate_source_file_for_conversion",
        lambda source_path, conversion_type: None,
    )

    def fake_convert_uploaded_file(*, source_path, task_dir, conversion_type, output_format):
        assert conversion_type.value == "image"
        assert output_format == "png"
        target_path = task_dir / "converted.png"
        target_path.write_text("converted", encoding="utf-8")
        return target_path, 1

    monkeypatch.setattr(converter, "convert_uploaded_file", fake_convert_uploaded_file)

    result = converter.convert_task.run.__func__(
        dummy_task,
        payload={
            "conversion_type": "image",
            "source_file_path": str(source_path),
            "source_file_name": "picture.jpg",
            "source_media_type": "image/jpeg",
            "output_format": "png",
        },
    )

    assert result["progress_percent"] == 100
    assert result["task_kind"] == "convert"
    assert result["result"]["output_format"] == "png"
    assert result["result"]["source_file_name"] == "picture.jpg"
    assert result["result"]["generated_files_count"] == 1


def test_convert_task_stores_failure_payload(monkeypatch, tmp_path: Path) -> None:
    dummy_task = DummyTask()
    source_dir = tmp_path / "convert-task-123"
    source_dir.mkdir(parents=True, exist_ok=True)
    source_path = source_dir / "document.pdf"
    source_path.write_text("pdf", encoding="utf-8")

    monkeypatch.setattr(converter.settings, "download_root", str(tmp_path))
    monkeypatch.setattr(
        converter,
        "validate_source_file_for_conversion",
        lambda source_path, conversion_type: None,
    )
    monkeypatch.setattr(
        converter,
        "convert_uploaded_file",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("conversion failed")),
    )

    try:
        converter.convert_task.run.__func__(
            dummy_task,
            payload={
                "conversion_type": "pdf",
                "source_file_path": str(source_path),
                "source_file_name": "document.pdf",
                "source_media_type": "application/pdf",
                "output_format": "jpg",
            },
        )
    except Exception:
        pass

    assert dummy_task.states[-1]["state"] == "ERROR"
    assert dummy_task.states[-1]["meta"]["error_code"] == "CONVERT_FAILED"
