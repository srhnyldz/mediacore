from enum import Enum
from typing import ClassVar

from pydantic import BaseModel, Field, HttpUrl, field_validator


class TaskState(str, Enum):
    PENDING = "PENDING"
    STARTED = "STARTED"
    PROGRESS = "PROGRESS"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"


class DownloadTaskRequest(BaseModel):
    allowed_output_formats: ClassVar[set[str]] = {
        "avi",
        "mp3",
        "mp4",
        "wav",
        "webm",
    }

    url: HttpUrl
    platform_hint: str | None = Field(default=None, max_length=50)
    output_format: str = Field(default="avi", max_length=20)

    @field_validator("output_format", mode="before")
    @classmethod
    def validate_output_format(cls, value: str | None) -> str:
        # API istemcisi alan gondermese bile worker tarafinda tutarli bir varsayilan kullaniriz.
        normalized = (value or "avi").strip().lower()
        if normalized not in cls.allowed_output_formats:
            raise ValueError("Unsupported output format.")
        return normalized


class DownloadTaskAcceptedResponse(BaseModel):
    task_id: str
    status: TaskState
    message: str


class DownloadTaskResult(BaseModel):
    file_path: str | None = None
    file_name: str | None = None
    file_size_bytes: int | None = None
    source_url: str | None = None
    download_url: str | None = None
    output_format: str | None = None


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    progress_percent: int = 0
    message: str
    result: DownloadTaskResult | None = None
    error_code: str | None = None
    error_message: str | None = None
