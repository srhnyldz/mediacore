from app.core.celery_app import celery_app

# Task kayitlarinin import edilmesi worker auto-discovery icin yeterlidir.
from app.tasks import converter, downloader  # noqa: F401

__all__ = ["celery_app"]

