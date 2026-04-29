from celery import Celery
from config import settings

celery_app = Celery(
    "bloxp",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["tasks.process_blog", "tasks.cleanup"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    beat_schedule={
        "cleanup-expired-jobs": {
            "task": "tasks.cleanup.cleanup_expired_jobs",
            "schedule": 3600,  # every hour
        },
    },
)
