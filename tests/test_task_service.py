from io import BytesIO

from celery import states
from fastapi import UploadFile

from app.schemas.task import ConvertTaskRequest, DownloadTaskRequest, TaskKind
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
    assert response.task_kind == TaskKind.DOWNLOAD
    assert captured["apply_async"]["queue"] == task_service.settings.celery_download_queue
    assert captured["store_result"]["state"] == states.PENDING


def test_enqueue_convert_upload_task_persists_file_and_seeds_pending_state(monkeypatch, tmp_path) -> None:
    captured = {}
    monkeypatch.setattr(task_service.settings, "download_root", str(tmp_path))

    class DummyAsyncResult:
        id = "convert-123"

    def fake_apply_async(*args, **kwargs):
        captured["apply_async"] = kwargs
        return DummyAsyncResult()

    def fake_store_result(task_id, payload, state):
        captured["store_result"] = {
            "task_id": task_id,
            "payload": payload,
            "state": state,
        }

    monkeypatch.setattr(task_service.convert_task, "apply_async", fake_apply_async)
    monkeypatch.setattr(task_service.celery_app.backend, "store_result", fake_store_result)
    monkeypatch.setattr(task_service, "uuid4", lambda: "convert-123")

    upload = UploadFile(
        file=BytesIO(b"image-bytes"),
        filename="example.jpg",
        headers={"content-type": "image/jpeg"},
    )

    response = task_service.enqueue_convert_upload_task(
        request_data=ConvertTaskRequest(conversion_type="image", output_format="png"),
        upload_file=upload,
    )

    assert response.task_id == "convert-123"
    assert response.task_kind == TaskKind.CONVERT
    assert captured["apply_async"]["queue"] == task_service.settings.celery_convert_queue
    assert captured["apply_async"]["task_id"] == "convert-123"
    assert captured["apply_async"]["kwargs"]["payload"]["source_file_name"] == "example.jpg"
    assert captured["store_result"]["state"] == states.PENDING


def test_enqueue_convert_upload_task_raises_for_empty_file(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(task_service.settings, "download_root", str(tmp_path))
    monkeypatch.setattr(task_service, "uuid4", lambda: "convert-123")

    upload = UploadFile(
        file=BytesIO(b""),
        filename="empty.pdf",
        headers={"content-type": "application/pdf"},
    )

    try:
        task_service.enqueue_convert_upload_task(
            request_data=ConvertTaskRequest(conversion_type="pdf", output_format="jpg"),
            upload_file=upload,
        )
    except task_service.TaskConflictError as exc:
        assert "empty" in str(exc).lower()
    else:  # pragma: no cover
        raise AssertionError("TaskConflictError bekleniyordu.")


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
                "message": "Donusturme tamamlandi.",
                "task_kind": TaskKind.CONVERT.value,
                "result": {
                    "file_path": "/tmp/downloads/task-123/converted.png",
                    "file_name": "converted.png",
                    "file_size_bytes": 2048,
                    "source_file_name": "example.jpg",
                    "output_format": "png",
                    "conversion_type": "image",
                    "generated_files_count": 1,
                },
            },
        },
    )

    response = task_service.get_task_status("task-123")

    assert response.status == states.SUCCESS
    assert response.task_kind == TaskKind.CONVERT
    assert response.result is not None
    assert response.result.file_name == "converted.png"
    assert response.result.download_url == "/api/v1/tasks/task-123/download"


def test_get_task_status_maps_error_state_to_failure(monkeypatch) -> None:
    monkeypatch.setattr(
        task_service.celery_app.backend,
        "get_task_meta",
        lambda _task_id: {
            "status": "ERROR",
            "result": {
                "progress_percent": 0,
                "message": "Donusturme basarisiz oldu.",
                "task_kind": TaskKind.CONVERT.value,
                "error_code": "CONVERT_FAILED",
                "error_message": "bad file",
                "result": None,
            },
        },
    )

    response = task_service.get_task_status("task-err")

    assert response.status == states.FAILURE
    assert response.error_code == "CONVERT_FAILED"
