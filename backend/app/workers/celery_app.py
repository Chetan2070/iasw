"""
Celery Application Configuration

Sets up Celery for async document processing.
"""

from celery import Celery

from app.config import settings

# Create Celery app
celery_app = Celery(
    "iasw",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.workers.tasks"],
)

# Celery configuration
celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # Timezone
    timezone="UTC",
    enable_utc=True,

    # Task tracking
    task_track_started=True,

    # Timeouts
    task_time_limit=settings.CELERY_TASK_TIME_LIMIT,
    task_soft_time_limit=settings.CELERY_TASK_SOFT_TIME_LIMIT,

    # Prefetch - process one task at a time for CPU-intensive work
    worker_prefetch_multiplier=1,

    # Acknowledgment - ack after completion for reliability
    task_acks_late=True,
    task_reject_on_worker_lost=True,

    # Retry policy
    task_default_retry_delay=60,  # 1 minute
    task_max_retries=3,

    # Result expiration
    result_expires=3600,  # 1 hour
)
