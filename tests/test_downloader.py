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
        "mp4",
    )

    assert resolved == target


def test_resolve_downloaded_file_prefers_merged_media_over_temp_parts(tmp_path: Path) -> None:
    chunk_video = tmp_path / "video.f399.mp4"
    merged_video = tmp_path / "video.mp4"
    temp_video = tmp_path / "video.temp.avi"
    thumbnail = tmp_path / "cover.webp"

    chunk_video.write_text("chunk", encoding="utf-8")
    merged_video.write_text("merged", encoding="utf-8")
    temp_video.write_text("temp", encoding="utf-8")
    thumbnail.write_text("thumb", encoding="utf-8")

    resolved = downloader._resolve_downloaded_file({}, tmp_path, "mp4")

    assert resolved == merged_video


def test_build_download_options_uses_bestaudio_for_audio_targets() -> None:
    options = downloader._build_download_options(
        task_dir=Path("/tmp/downloads/task-123"),
        progress_hook=lambda _data: None,
        output_format="mp3",
    )

    assert options["format"] == "bestaudio/best"
    assert "postprocessors" not in options


def test_build_download_options_uses_intermediate_mp4_merge_for_video_targets() -> None:
    options = downloader._build_download_options(
        task_dir=Path("/tmp/downloads/task-123"),
        progress_hook=lambda _data: None,
        output_format="avi",
    )

    assert options["format"] == "bestvideo*+bestaudio/best"
    assert options["merge_output_format"] == "mp4"


def test_build_download_options_prefers_native_webm_streams() -> None:
    options = downloader._build_download_options(
        task_dir=Path("/tmp/downloads/task-123"),
        progress_hook=lambda _data: None,
        output_format="webm",
    )

    assert "bestvideo[ext=webm]" in options["format"]
    assert options["merge_output_format"] == "webm"


def test_build_ffmpeg_command_uses_avi_safe_codecs(tmp_path: Path) -> None:
    command = downloader._build_ffmpeg_command(
        source_path=tmp_path / "input.mp4",
        target_path=tmp_path / "output.avi",
        output_format="avi",
    )

    assert command[:4] == ["ffmpeg", "-y", "-i", str(tmp_path / "input.mp4")]
    assert "mpeg4" in command
    assert "libmp3lame" in command


def test_build_ffmpeg_command_uses_fast_webm_profile(tmp_path: Path) -> None:
    command = downloader._build_ffmpeg_command(
        source_path=tmp_path / "input.mp4",
        target_path=tmp_path / "output.webm",
        output_format="webm",
    )

    assert "libvpx" in command
    assert "realtime" in command
    assert "8" in command


def test_convert_media_file_raises_with_ffmpeg_stderr(monkeypatch, tmp_path: Path) -> None:
    source_path = tmp_path / "input.mp4"
    source_path.write_text("video", encoding="utf-8")

    class FailedProcess:
        returncode = 1
        stderr = "line1\nline2\nConversion broke"

    def fake_run(command, capture_output, text, check):
        assert command[0] == "ffmpeg"
        assert capture_output is True
        assert text is True
        assert check is False
        return FailedProcess()

    monkeypatch.setattr(downloader.subprocess, "run", fake_run)

    try:
        downloader._convert_media_file(source_path, tmp_path, "avi")
    except RuntimeError as exc:
        assert "Conversion broke" in str(exc)
    else:  # pragma: no cover - test guvencesi
        raise AssertionError("RuntimeError bekleniyordu.")


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
        payload={
            "url": "https://example.com/video",
            "output_format": "mp4",
        },
    )

    assert result["progress_percent"] == 100
    assert result["result"]["file_name"] == "Title.mp4"
    assert result["result"]["output_format"] == "mp4"
    assert Path(result["result"]["file_path"]).exists()
    assert dummy_task.states[0]["state"] == "STARTED"


def test_normalize_output_format_falls_back_to_avi() -> None:
    assert downloader._normalize_output_format(None) == "avi"


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

    assert dummy_task.states
    assert dummy_task.states[-1]["state"] == "ERROR"
    assert dummy_task.states[-1]["meta"]["error_code"] == "DOWNLOAD_FAILED"
