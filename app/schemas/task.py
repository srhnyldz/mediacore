from enum import Enum
from typing import ClassVar

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator

from app.services.media_service import DEFAULT_OUTPUT_FORMAT, SUPPORTED_OUTPUT_FORMATS


class TaskState(str, Enum):
    PENDING = "PENDING"
    STARTED = "STARTED"
    PROGRESS = "PROGRESS"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"


class TaskKind(str, Enum):
    DOWNLOAD = "download"
    CONVERT = "convert"


class ConversionType(str, Enum):
    IMAGE = "image"
    PDF = "pdf"


class OutputFormatMixin(BaseModel):
    allowed_output_formats: ClassVar[set[str]] = SUPPORTED_OUTPUT_FORMATS

    output_format: str = Field(default=DEFAULT_OUTPUT_FORMAT, max_length=20)

    @field_validator("output_format", mode="before")
    @classmethod
    def validate_output_format(cls, value: str | None) -> str:
        normalized = (value or DEFAULT_OUTPUT_FORMAT).strip().lower()
        if normalized not in cls.allowed_output_formats:
            raise ValueError("Unsupported output format.")
        return normalized


class DownloadTaskRequest(OutputFormatMixin):
    url: HttpUrl
    platform_hint: str | None = Field(default=None, max_length=50)


class ConvertTaskRequest(OutputFormatMixin):
    allowed_output_formats: ClassVar[set[str]] = {"jpg", "jpeg", "png", "webp"}
    allowed_conversion_formats: ClassVar[dict[ConversionType, set[str]]] = {
        ConversionType.IMAGE: {"jpg", "jpeg", "png", "webp"},
        ConversionType.PDF: {"jpg", "jpeg", "png"},
    }

    conversion_type: ConversionType

    @model_validator(mode="after")
    def validate_output_format_for_conversion(self) -> "ConvertTaskRequest":
        allowed_formats = self.allowed_conversion_formats[self.conversion_type]
        if self.output_format not in allowed_formats:
            raise ValueError("Unsupported output format for the selected conversion.")
        return self


class ConvertTaskPayload(ConvertTaskRequest):
    source_file_path: str
    source_file_name: str
    source_media_type: str | None = None


class TaskAcceptedResponse(BaseModel):
    task_id: str
    status: TaskState
    message: str
    task_kind: TaskKind


DownloadTaskAcceptedResponse = TaskAcceptedResponse
ConvertTaskAcceptedResponse = TaskAcceptedResponse


class DownloadTaskResult(BaseModel):
    file_path: str | None = None
    file_name: str | None = None
    file_size_bytes: int | None = None
    source_url: str | None = None
    download_url: str | None = None
    output_format: str | None = None
    source_file_name: str | None = None
    conversion_type: ConversionType | None = None
    generated_files_count: int | None = None


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    task_kind: TaskKind | None = None
    progress_percent: int = 0
    message: str
    result: DownloadTaskResult | None = None
    error_code: str | None = None
    error_message: str | None = None
