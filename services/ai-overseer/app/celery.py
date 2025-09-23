"""
Celery configuration for the AI Overseer service.
"""
import os
from celery import Celery

# Redis configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# Create Celery app
celery = Celery(
    "ai_overseer",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["app.tasks"]
)

# Celery configuration
celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Beat schedule for periodic tasks
celery.conf.beat_schedule = {
    "check-scheduled-groups": {
        "task": "app.tasks.check_scheduled_groups",
        "schedule": 60.0,  # Every minute
    },
    "fetch-news-feeds": {
        "task": "app.tasks.fetch_all_news_feeds",
        "schedule": 300.0,  # Every 5 minutes
    },
}