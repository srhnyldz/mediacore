from fastapi import APIRouter, HTTPException, status

from app.schemas.task import (
    DownloadTaskAcceptedResponse,
    DownloadTaskRequest,
    TaskStatusResponse,
)
from app.services.task_service import (
    TaskNotFoundError,
    enqueue_download_task,
    get_task_status,
)


router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post(
    "/downloads",
    response_model=DownloadTaskAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_download_task(
    payload: DownloadTaskRequest,
) -> DownloadTaskAcceptedResponse:
    try:
        return enqueue_download_task(payload)
    except Exception as exc:  # pragma: no cover - son savunma katmani
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Gorev kuyruga eklenemedi: {exc}",
        ) from exc


@router.get("/{task_id}", response_model=TaskStatusResponse)
async def fetch_task_status(task_id: str) -> TaskStatusResponse:
    try:
        return get_task_status(task_id)
    except TaskNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

