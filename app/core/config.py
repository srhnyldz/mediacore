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
    app_version: str = _read_version()
    api_prefix: str = "/api/v1"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/1"
    download_root: str = "/tmp/downloads"
    celery_download_queue: str = "download"
    celery_convert_queue: str = "convert"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

