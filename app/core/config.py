from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _read_version() -> str:
    version_path = Path(__file__).resolve().parents[2] / "VERSION"
    if version_path.exists():
        return f"v{version_path.read_text(encoding='utf-8').strip()}"
    return "v0.1.0"


class Settings(BaseSettings):
    app_name: str = "YLZ MediaCore API"
    api_prefix: str = "/api/v1"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    redis_url: str = "redis://redis:6379/0"
    redis_socket_timeout_seconds: int = 2
    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/1"
    download_root: str = "/tmp/downloads"
    celery_download_queue: str = "download"
    celery_convert_queue: str = "convert"
    celery_result_ttl_seconds: int = 86400
    celery_task_soft_time_limit_seconds: int = 900
    celery_task_time_limit_seconds: int = 960
    celery_worker_max_tasks_per_child: int = 50
    celery_visibility_timeout_seconds: int = 1800
    cleanup_max_age_hours: int = 24
    cleanup_batch_limit: int = 100
    download_request_rate_limit: int = 10
    download_request_rate_window_seconds: int = 60

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def app_version(self) -> str:
        # Surum bilgisini her zaman VERSION dosyasindan okuyarak .env drift'ini engelleriz.
        return _read_version()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
