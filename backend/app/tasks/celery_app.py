from celery import Celery
from celery.schedules import crontab

from app.config import settings

celery_app = Celery(
    "orbitalwatch",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "ingest-tles-every-4h": {
            "task": "app.tasks.ingestion.ingest_tles",
            "schedule": crontab(minute=0, hour="*/4"),
        },
        "ingest-cdms-every-4h": {
            "task": "app.tasks.ingestion.ingest_cdms",
            "schedule": crontab(minute=30, hour="*/4"),
        },
        "precompute-positions-every-60s": {
            "task": "app.tasks.ingestion.precompute_positions",
            "schedule": 60.0,
        },
    },
)
