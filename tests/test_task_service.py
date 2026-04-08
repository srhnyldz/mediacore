from celery import states

from app.schemas.task import DownloadTaskRequest
from app.services import task_service


def test_enqueue_download_task_seeds_pending_state(monkeypatch) -> None:
    captured = {}

    class DummyAsyncResult:
        id = "task-123"

    def fake_apply_async(*args, **kwargs):
        captured["apply_async"] = kwargs
        return DummyAsyncResult()

    def fake_store_result(task_id, payload, state):
        captured["store_result"] = {
            "task_id": task_id,
            "payload": payload,
            "state": state,
        }

    monkeypatch.setattr(task_service.download_task, "apply_async", fake_apply_async)
    monkeypatch.setattr(task_service.celery_app.backend, "store_result", fake_store_result)

    response = task_service.enqueue_download_task(
        DownloadTaskRequest(url="https://example.com/video")
    )

    assert response.task_id == "task-123"
    assert captured["apply_async"]["queue"] == task_service.settings.celery_download_queue
    assert captured["store_result"]["state"] == states.PENDING


def test_get_task_status_raises_for_unknown_task(monkeypatch) -> None:
    monkeypatch.setattr(
        task_service.celery_app.backend,
        "get_task_meta",
        lambda _task_id: {"status": states.PENDING, "result": None},
    )

    try:
        task_service.get_task_status("unknown-task")
    except task_service.TaskNotFoundError as exc:
        assert "unknown-task" in str(exc)
    else:  # pragma: no cover - test guvencesi
        raise AssertionError("TaskNotFoundError bekleniyordu.")


def test_get_task_status_returns_success_payload(monkeypatch) -> None:
    monkeypatch.setattr(
        task_service.celery_app.backend,
        "get_task_meta",
        lambda _task_id: {
            "status": states.SUCCESS,
            "result": {
                "progress_percent": 100,
                "message": "Indirme tamamlandi.",
                "result": {
                    "file_path": "/tmp/downloads/task-123/video.mp4",
                    "file_name": "video.mp4",
                    "file_size_bytes": 2048,
                    "source_url": "https://example.com/video",
                },
            },
        },
    )

    response = task_service.get_task_status("task-123")

    assert response.status == states.SUCCESS
    assert response.result is not None
    assert response.result.file_name == "video.mp4"
    assert response.result.download_url == "/api/v1/tasks/task-123/download"


def test_get_task_status_maps_error_state_to_failure(monkeypatch) -> None:
    monkeypatch.setattr(
        task_service.celery_app.backend,
        "get_task_meta",
        lambda _task_id: {
            "status": "ERROR",
            "result": {
                "progress_percent": 0,
                "message": "Indirme basarisiz oldu.",
                "error_code": "DOWNLOAD_FAILED",
                "error_message": "yt-dlp failure",
                "result": None,
            },
        },
    )

    response = task_service.get_task_status("task-err")

    assert response.status == states.FAILURE
    assert response.error_code == "DOWNLOAD_FAILED"
