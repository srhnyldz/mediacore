from enum import Enum

from pydantic import BaseModel, Field, HttpUrl


class TaskState(str, Enum):
    PENDING = "PENDING"
    STARTED = "STARTED"
    PROGRESS = "PROGRESS"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"


class DownloadTaskRequest(BaseModel):
    url: HttpUrl
    platform_hint: str | None = Field(default=None, max_length=50)
    output_format: str | None = Field(default=None, max_length=20)


class DownloadTaskAcceptedResponse(BaseModel):
    task_id: str
    status: TaskState
    message: str


class DownloadTaskResult(BaseModel):
    file_path: str | None = None
    file_name: str | None = None
    file_size_bytes: int | None = None
    source_url: str | None = None


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    progress_percent: int = 0
    message: str
    result: DownloadTaskResult | None = None
    error_code: str | None = None
    error_message: str | None = None

