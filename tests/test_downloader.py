from pathlib import Path
from types import SimpleNamespace

from app.tasks import downloader


class DummyBackend:
    def __init__(self) -> None:
        self.calls = []

    def store_result(self, task_id, payload, state) -> None:
        self.calls.append(
            {"task_id": task_id, "payload": payload, "state": state}
        )


class DummyTask:
    def __init__(self, task_id: str = "task-123") -> None:
        self.request = SimpleNamespace(id=task_id)
        self.backend = DummyBackend()
        self.states = []

    def update_state(self, state: str, meta: dict) -> None:
        self.states.append({"state": state, "meta": meta})


def test_calculate_progress_percent_uses_total_bytes() -> None:
    percent = downloader._calculate_progress_percent(
        {"status": "downloading", "downloaded_bytes": 50, "total_bytes": 200}
    )

    assert percent == 25


def test_calculate_progress_percent_uses_percent_string() -> None:
    percent = downloader._calculate_progress_percent(
        {"status": "downloading", "_percent_str": "42.8%"}
    )

    assert percent == 42


def test_resolve_downloaded_file_prefers_existing_requested_download(tmp_path: Path) -> None:
    target = tmp_path / "video.mp4"
    target.write_text("data", encoding="utf-8")

    resolved = downloader._resolve_downloaded_file(
        {"requested_downloads": [{"filepath": str(target)}]},
        tmp_path,
    )

    assert resolved == target


def test_download_task_returns_success_payload(monkeypatch, tmp_path: Path) -> None:
    dummy_task = DummyTask()
    target_path = tmp_path / "Title!!.mp4"
    target_path.write_text("video", encoding="utf-8")

    monkeypatch.setattr(downloader.settings, "download_root", str(tmp_path))

    class DummyYoutubeDL:
        def __init__(self, options):
            self.options = options

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def extract_info(self, _url: str, download: bool):
            assert download is True
            return {"requested_downloads": [{"filepath": str(target_path)}]}

    monkeypatch.setattr(downloader, "YoutubeDL", DummyYoutubeDL)

    result = downloader.download_task.run.__func__(
        dummy_task,
        payload={"url": "https://example.com/video"},
    )

    assert result["progress_percent"] == 100
    assert result["result"]["file_name"] == "Title.mp4"
    assert Path(result["result"]["file_path"]).exists()
    assert dummy_task.states[0]["state"] == "STARTED"


def test_download_task_stores_failure_payload(monkeypatch, tmp_path: Path) -> None:
    dummy_task = DummyTask(task_id="task-fail")

    monkeypatch.setattr(downloader.settings, "download_root", str(tmp_path))

    class FailingYoutubeDL:
        def __init__(self, options):
            self.options = options

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def extract_info(self, _url: str, download: bool):
            raise RuntimeError("yt-dlp failure")

    monkeypatch.setattr(downloader, "YoutubeDL", FailingYoutubeDL)

    try:
        downloader.download_task.run.__func__(
            dummy_task,
            payload={"url": "https://example.com/video"},
        )
    except Exception:
        pass

    assert dummy_task.backend.calls
    assert dummy_task.backend.calls[0]["payload"]["error_code"] == "DOWNLOAD_FAILED"
