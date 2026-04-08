from celery import Celery
from kombu import Exchange, Queue

from app.core.config import settings


download_exchange = Exchange(settings.celery_download_queue, type="direct")
convert_exchange = Exchange(settings.celery_convert_queue, type="direct")


celery_app = Celery(
    "ylz_mediacore",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_track_started=True,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    enable_utc=True,
    timezone="UTC",
    result_expires=settings.celery_result_ttl_seconds,
    broker_connection_retry_on_startup=True,
    task_create_missing_queues=True,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=settings.celery_worker_max_tasks_per_child,
    task_soft_time_limit=settings.celery_task_soft_time_limit_seconds,
    task_time_limit=settings.celery_task_time_limit_seconds,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    broker_transport_options={
        "visibility_timeout": settings.celery_visibility_timeout_seconds,
    },
    task_default_queue=settings.celery_download_queue,
    task_default_exchange=download_exchange.name,
    task_default_exchange_type=download_exchange.type,
    task_default_routing_key=settings.celery_download_queue,
    task_queues=(
        Queue(
            settings.celery_download_queue,
            exchange=download_exchange,
            routing_key=settings.celery_download_queue,
        ),
        Queue(
            settings.celery_convert_queue,
            exchange=convert_exchange,
            routing_key=settings.celery_convert_queue,
        ),
    ),
    task_routes={
        "app.tasks.downloader.download_task": {
            "queue": settings.celery_download_queue,
            "exchange": download_exchange.name,
            "routing_key": settings.celery_download_queue,
        },
        "app.tasks.converter.convert_task": {
            "queue": settings.celery_convert_queue,
            "exchange": convert_exchange.name,
            "routing_key": settings.celery_convert_queue,
        },
        "app.tasks.maintenance.cleanup_expired_downloads_task": {
            "queue": settings.celery_convert_queue,
            "exchange": convert_exchange.name,
            "routing_key": settings.celery_convert_queue,
        },
    },
    imports=("app.tasks.downloader", "app.tasks.converter", "app.tasks.maintenance"),
)
