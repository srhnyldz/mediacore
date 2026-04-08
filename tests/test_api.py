from fastapi.testclient import TestClient

from app.schemas.task import DownloadTaskAcceptedResponse, TaskStatusResponse
from app.services.task_service import TaskConflictError, TaskNotFoundError


def test_frontend_route_returns_html(test_client: TestClient) -> None:
    response = test_client.get("/")

    assert response.status_code == 200
    assert "YLZ MediaCore" in response.text


def test_converter_route_returns_html(test_client: TestClient) -> None:
    response = test_client.get("/convert")

    assert response.status_code == 200
    assert "Converter" in response.text


def test_ready_route_returns_ready_payload(monkeypatch, test_client: TestClient) -> None:
    monkeypatch.setattr(
        "app.main.get_readiness_status",
        lambda: {
            "status": "ready",
            "version": "v0.5.0",
            "checks": {"redis": {"ok": True}, "storage": {"ok": True}},
        },
    )

    response = test_client.get("/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_ready_route_returns_503_when_degraded(monkeypatch, test_client: TestClient) -> None:
    monkeypatch.setattr(
        "app.main.get_readiness_status",
        lambda: {
            "status": "degraded",
            "version": "v0.5.0",
            "checks": {"redis": {"ok": False}},
        },
    )

    response = test_client.get("/ready")

    assert response.status_code == 503


def test_create_download_task_returns_accepted(monkeypatch, test_client: TestClient) -> None:
    captured = {}

    def fake_enqueue_download_task(payload):
        captured["payload"] = payload
        return DownloadTaskAcceptedResponse(
            task_id="task-123",
            status="PENDING",
            message="Gorev kuyruga alindi.",
            task_kind="download",
        )

    monkeypatch.setattr(
        "app.api.v1.endpoints.tasks.enqueue_download_task",
        fake_enqueue_download_task,
    )
    monkeypatch.setattr(
        "app.api.v1.endpoints.tasks.enforce_download_rate_limit",
        lambda request: None,
    )

    response = test_client.post(
        "/api/v1/tasks/downloads",
        json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
    )

    assert response.status_code == 202
    assert response.json()["task_id"] == "task-123"
    assert response.json()["task_kind"] == "download"
    assert captured["payload"].output_format == "avi"


def test_create_convert_task_returns_accepted(monkeypatch, test_client: TestClient) -> None:
    def fake_enqueue_convert_upload_task(*, request_data, upload_file):
        assert request_data.conversion_type.value == "image"
        assert request_data.output_format == "png"
        assert upload_file.filename == "sample.jpg"
        return DownloadTaskAcceptedResponse(
            task_id="convert-123",
            status="PENDING",
            message="Convert gorevi kuyruga alindi.",
            task_kind="convert",
        )

    monkeypatch.setattr(
        "app.api.v1.endpoints.tasks.enqueue_convert_upload_task",
        fake_enqueue_convert_upload_task,
    )
    monkeypatch.setattr(
        "app.api.v1.endpoints.tasks.enforce_download_rate_limit",
        lambda request: None,
    )

    response = test_client.post(
        "/api/v1/tasks/conversions",
        data={"conversion_type": "image", "output_format": "png"},
        files={"file": ("sample.jpg", b"image-bytes", "image/jpeg")},
    )

    assert response.status_code == 202
    assert response.json()["task_kind"] == "convert"


def test_create_convert_task_returns_conflict(monkeypatch, test_client: TestClient) -> None:
    monkeypatch.setattr(
        "app.api.v1.endpoints.tasks.enforce_download_rate_limit",
        lambda request: None,
    )
    monkeypatch.setattr(
        "app.api.v1.endpoints.tasks.enqueue_convert_upload_task",
        lambda **kwargs: (_ for _ in ()).throw(TaskConflictError("Uploaded file is empty.")),
    )

    response = test_client.post(
        "/api/v1/tasks/conversions",
        data={"conversion_type": "pdf", "output_format": "jpg"},
        files={"file": ("empty.pdf", b"", "application/pdf")},
    )

    assert response.status_code == 409


def test_create_download_task_returns_429_when_rate_limited(monkeypatch, test_client: TestClient) -> None:
    from app.services.rate_limit_service import RateLimitExceededError

    monkeypatch.setattr(
        "app.api.v1.endpoints.tasks.enforce_download_rate_limit",
        lambda request: (_ for _ in ()).throw(RateLimitExceededError(30)),
    )

    response = test_client.post(
        "/api/v1/tasks/downloads",
        json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
    )

    assert response.status_code == 429
    assert response.headers["Retry-After"] == "30"


def test_fetch_task_status_returns_not_found(monkeypatch, test_client: TestClient) -> None:
    def fake_get_task_status(_task_id: str):
        raise TaskNotFoundError("missing-task")

    monkeypatch.setattr(
        "app.api.v1.endpoints.tasks.get_task_status",
        fake_get_task_status,
    )

    response = test_client.get("/api/v1/tasks/missing-task")

    assert response.status_code == 404
    assert "Gorev bulunamadi" in response.json()["detail"]


def test_fetch_task_status_returns_payload(monkeypatch, test_client: TestClient) -> None:
    def fake_get_task_status(_task_id: str):
        return TaskStatusResponse(
            task_id="task-123",
            status="SUCCESS",
            task_kind="convert",
            progress_percent=100,
            message="Donusturme tamamlandi.",
            result={
                "file_path": "/tmp/downloads/task-123/converted.png",
                "file_name": "converted.png",
                "file_size_bytes": 1234,
                "download_url": "/api/v1/tasks/task-123/download",
                "output_format": "png",
                "source_file_name": "source.jpg",
                "conversion_type": "image",
                "generated_files_count": 1,
            },
        )

    monkeypatch.setattr(
        "app.api.v1.endpoints.tasks.get_task_status",
        fake_get_task_status,
    )

    response = test_client.get("/api/v1/tasks/task-123")

    assert response.status_code == 200
    assert response.json()["status"] == "SUCCESS"
    assert response.json()["task_kind"] == "convert"
    assert response.json()["result"]["download_url"] == "/api/v1/tasks/task-123/download"


def test_download_task_file_returns_binary(monkeypatch, test_client: TestClient, tmp_path) -> None:
    download_dir = tmp_path / "task-123"
    download_dir.mkdir(parents=True, exist_ok=True)
    file_path = download_dir / "converted.png"
    file_path.write_bytes(b"image-data")

    monkeypatch.setattr("app.api.v1.endpoints.tasks.settings.download_root", str(tmp_path))

    def fake_get_task_status(_task_id: str):
        return TaskStatusResponse(
            task_id="task-123",
            status="SUCCESS",
            task_kind="convert",
            progress_percent=100,
            message="Donusturme tamamlandi.",
            result={
                "file_path": str(file_path),
                "file_name": "converted.png",
                "file_size_bytes": 10,
                "download_url": "/api/v1/tasks/task-123/download",
                "output_format": "png",
                "source_file_name": "source.jpg",
                "conversion_type": "image",
                "generated_files_count": 1,
            },
        )

    monkeypatch.setattr(
        "app.api.v1.endpoints.tasks.get_task_status",
        fake_get_task_status,
    )

    response = test_client.get("/api/v1/tasks/task-123/download")

    assert response.status_code == 200
    assert response.content == b"image-data"
