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

# Beat schedule for periodic tasks (configurable via env)
FEED_FETCH_INTERVAL_MINUTES = float(os.getenv("FEED_FETCH_INTERVAL_MINUTES", "15"))
COLLECTION_BUILD_INTERVAL_MINUTES = float(os.getenv("COLLECTION_BUILD_INTERVAL_MINUTES", "10"))
REVIEW_DISPATCH_INTERVAL_MINUTES = float(os.getenv("REVIEW_DISPATCH_INTERVAL_MINUTES", "5"))

celery.conf.beat_schedule = {
    "check-scheduled-groups": {
        "task": "app.tasks.check_scheduled_groups",
        "schedule": 2 * 60 * 60.0,  # Every 2 hours
    },
    "fetch-news-feeds": {
        "task": "app.tasks.fetch_all_news_feeds",
        "schedule": FEED_FETCH_INTERVAL_MINUTES * 60.0,
    },
    "create-collections": {
        "task": "app.tasks.create_collections_from_articles",
        "schedule": COLLECTION_BUILD_INTERVAL_MINUTES * 60.0,
    },
    "update-collection-status": {
        "task": "app.tasks.update_collection_status",
        "schedule": 30 * 60.0,  # Every 30 minutes
    },
    "send-articles-to-reviewer": {
        "task": "app.tasks.send_articles_to_reviewer",
        "schedule": REVIEW_DISPATCH_INTERVAL_MINUTES * 60.0,
    },
}
