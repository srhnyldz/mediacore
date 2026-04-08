from fastapi.testclient import TestClient

from app.schemas.task import DownloadTaskAcceptedResponse, TaskStatusResponse
from app.services.task_service import TaskNotFoundError


def test_frontend_route_returns_html(test_client: TestClient) -> None:
    response = test_client.get("/")

    assert response.status_code == 200
    assert "YLZ MediaCore" in response.text


def test_create_download_task_returns_accepted(
    monkeypatch,
    test_client: TestClient,
) -> None:
    captured = {}

    def fake_enqueue_download_task(payload):
        captured["payload"] = payload
        return DownloadTaskAcceptedResponse(
            task_id="task-123",
            status="PENDING",
            message="Gorev kuyruga alindi.",
        )

    monkeypatch.setattr(
        "app.api.v1.endpoints.tasks.enqueue_download_task",
        fake_enqueue_download_task,
    )

    response = test_client.post(
        "/api/v1/tasks/downloads",
        json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
    )

    assert response.status_code == 202
    assert response.json()["task_id"] == "task-123"
    assert captured["payload"].output_format == "avi"


def test_fetch_task_status_returns_not_found(
    monkeypatch,
    test_client: TestClient,
) -> None:
    def fake_get_task_status(_task_id: str):
        raise TaskNotFoundError("missing-task")

    monkeypatch.setattr(
        "app.api.v1.endpoints.tasks.get_task_status",
        fake_get_task_status,
    )

    response = test_client.get("/api/v1/tasks/missing-task")

    assert response.status_code == 404
    assert "Gorev bulunamadi" in response.json()["detail"]


def test_fetch_task_status_returns_payload(
    monkeypatch,
    test_client: TestClient,
) -> None:
    def fake_get_task_status(_task_id: str):
        return TaskStatusResponse(
            task_id="task-123",
            status="SUCCESS",
            progress_percent=100,
            message="Indirme tamamlandi.",
            result={
                "file_path": "/tmp/downloads/task-123/video.mp4",
                "file_name": "video.mp4",
                "file_size_bytes": 1234,
                "source_url": "https://example.com/video",
                "download_url": "/api/v1/tasks/task-123/download",
            },
        )

    monkeypatch.setattr(
        "app.api.v1.endpoints.tasks.get_task_status",
        fake_get_task_status,
    )

    response = test_client.get("/api/v1/tasks/task-123")

    assert response.status_code == 200
    assert response.json()["status"] == "SUCCESS"
    assert response.json()["result"]["download_url"] == "/api/v1/tasks/task-123/download"


def test_download_task_file_returns_binary(monkeypatch, test_client: TestClient, tmp_path) -> None:
    download_dir = tmp_path / "task-123"
    download_dir.mkdir(parents=True, exist_ok=True)
    file_path = download_dir / "video.mp4"
    file_path.write_bytes(b"video-data")

    monkeypatch.setattr("app.api.v1.endpoints.tasks.settings.download_root", str(tmp_path))

    def fake_get_task_status(_task_id: str):
        return TaskStatusResponse(
            task_id="task-123",
            status="SUCCESS",
            progress_percent=100,
            message="Indirme tamamlandi.",
            result={
                "file_path": str(file_path),
                "file_name": "video.mp4",
                "file_size_bytes": 10,
                "source_url": "https://example.com/video",
                "download_url": "/api/v1/tasks/task-123/download",
            },
        )

    monkeypatch.setattr(
        "app.api.v1.endpoints.tasks.get_task_status",
        fake_get_task_status,
    )

    response = test_client.get("/api/v1/tasks/task-123/download")

    assert response.status_code == 200
    assert response.content == b"video-data"
