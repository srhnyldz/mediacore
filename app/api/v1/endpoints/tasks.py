from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Request, Response, UploadFile, status
from fastapi.responses import FileResponse

from app.core.config import settings
from app.schemas.task import (
    ConversionType,
    ConvertTaskAcceptedResponse,
    ConvertTaskRequest,
    DownloadTaskAcceptedResponse,
    DownloadTaskRequest,
    TaskStatusResponse,
)
from app.services.rate_limit_service import (
    RateLimitExceededError,
    enforce_download_rate_limit,
)
from app.services.task_service import (
    TaskConflictError,
    TaskNotFoundError,
    enqueue_convert_upload_task,
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
    request: Request,
    response: Response,
    payload: DownloadTaskRequest,
) -> DownloadTaskAcceptedResponse:
    try:
        enforce_download_rate_limit(request=request)
        return enqueue_download_task(payload)
    except RateLimitExceededError as exc:
        response.headers["Retry-After"] = str(exc.retry_after_seconds)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(exc),
            headers={"Retry-After": str(exc.retry_after_seconds)},
        ) from exc
    except Exception as exc:  # pragma: no cover - son savunma katmani
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Gorev kuyruga eklenemedi: {exc}",
        ) from exc


@router.post(
    "/conversions",
    response_model=ConvertTaskAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_convert_task(
    request: Request,
    response: Response,
    conversion_type: ConversionType = Form(...),
    output_format: str = Form(...),
    file: UploadFile = File(...),
) -> ConvertTaskAcceptedResponse:
    try:
        enforce_download_rate_limit(request=request)
        payload = ConvertTaskRequest(
            conversion_type=conversion_type,
            output_format=output_format,
        )
        return enqueue_convert_upload_task(
            request_data=payload,
            upload_file=file,
        )
    except RateLimitExceededError as exc:
        response.headers["Retry-After"] = str(exc.retry_after_seconds)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(exc),
            headers={"Retry-After": str(exc.retry_after_seconds)},
        ) from exc
    except TaskConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except Exception as exc:  # pragma: no cover - son savunma katmani
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Convert gorevi kuyruga eklenemedi: {exc}",
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


@router.get("/{task_id}/download")
async def download_task_file(task_id: str) -> FileResponse:
    task_status = get_task_status(task_id)

    if task_status.status != "SUCCESS" or task_status.result is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Download file is not ready yet for this task.",
        )

    file_path = task_status.result.file_path
    if not file_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Download file could not be resolved.",
        )

    resolved_path = _resolve_task_file_path(task_id=task_id, file_path=file_path)
    return FileResponse(
        resolved_path,
        filename=task_status.result.file_name or resolved_path.name,
        media_type="application/octet-stream",
    )


def _resolve_task_file_path(task_id: str, file_path: str) -> Path:
    try:
        candidate = Path(file_path).resolve(strict=True)
        task_root = (Path(settings.download_root) / task_id).resolve(strict=True)
        candidate.relative_to(task_root)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Download file does not exist on disk.",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Requested file is outside the task download directory.",
        ) from exc

    return candidate
