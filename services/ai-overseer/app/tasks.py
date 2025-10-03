"""
Celery tasks for the AI Overseer service.
"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import os
from uuid import UUID

import httpx
from celery import current_task
from sqlalchemy.orm import Session

from shared.database import get_db_session
from shared.models import PodcastGroup, NewsFeed, Article, Episode, EpisodeStatus, news_feed_assignment, Collection
from shared.schemas import GenerationRequest, GenerationResponse
from .celery import celery
from .services import EpisodeGenerationService, NewsFeedService, TextGenerationService, WriterService, PresenterService, PublishingService

logger = logging.getLogger(__name__)


# ----------------------------
# Adaptive Cadence definitions
# Simple, explicit cadence buckets measured in days
CADENCE_BUCKETS: List[Tuple[str, int]] = [
    ("daily", 1),
    ("three_day", 3),
    ("weekly", 7),
]

MIN_FEEDS_THRESHOLD_DEFAULT = int(os.getenv("MIN_FEEDS_THRESHOLD", "3"))

def _get_ready_collections() -> List[Dict[str, Any]]:
    """Fetch ready collections from Collections Service.
    Returns a list of collection dicts with fields: collection_id, group_id, items, status, metadata
    """
    try:
        import asyncio
        import httpx

        async def _fetch() -> List[Dict[str, Any]]:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get("http://collections:8011/collections/ready")
                resp.raise_for_status()
                return resp.json()

        return asyncio.run(_fetch())
    except Exception as e:
        logger.warning(f"Could not fetch ready collections: {e}")
        return []


def _count_items(collection: Dict[str, Any], item_type: str) -> int:
    items = collection.get("items", [])
    return sum(1 for it in items if it.get("item_type") == item_type)


def _collection_freshness_hours(collection: Dict[str, Any]) -> Optional[float]:
    """Compute freshness based on newest feed item's publish_date if present."""
    try:
        from dateutil import parser as dateparser  # optional dependency; falls back if missing
    except Exception:
        dateparser = None

    newest = None
    for it in collection.get("items", []):
        if it.get("item_type") == "feed":
            pd = it.get("content", {}).get("publish_date")
            if pd and dateparser:
                try:
                    dt = dateparser.parse(pd)
                except Exception:
                    dt = None
            else:
                dt = None
            if dt and (newest is None or dt > newest):
                newest = dt

    if not newest:
        return None
    return (datetime.utcnow() - newest.replace(tzinfo=None)).total_seconds() / 3600.0


def _rank_collection(collection: Dict[str, Any]) -> Tuple[int, float, int]:
    """Rank tuple: (priority_score, -completeness_score, freshness_hours or large)
    Higher priority_score first; lower freshness hours first; more completeness (feeds/reviews) increases score.
    """
    # Priority tags
    priority_tags = set((collection.get("metadata", {}) or {}).get("priority_tags", []))
    has_breaking = 1 if ("breaking" in {t.lower() for t in priority_tags}) else 0

    # Completeness (feeds + reviews)
    feed_count = _count_items(collection, "feed")
    review_count = _count_items(collection, "review")
    completeness = feed_count + review_count

    # Freshness (hours)
    freshness = _collection_freshness_hours(collection)
    freshness_val = freshness if freshness is not None else 99999.0

    # Priority score favors breaking and larger completeness
    priority_score = has_breaking * 100 + min(completeness, 20)

    return (priority_score, -completeness, freshness_val)


def _select_best_collection(candidates: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not candidates:
        return None
    ranked = sorted(candidates, key=_rank_collection, reverse=True)
    return ranked[0]


def _current_bucket_for_group(db: Session, group: PodcastGroup) -> Tuple[str, int]:
    """Decide which cadence bucket applies based on content readiness first, then time spacing.
    Priority:
      1) If threshold met for Daily, choose Daily
      2) Else if threshold met for 3-Day, choose 3-Day
      3) Else choose Weekly
    """
    ready_collections = [c for c in _get_ready_collections() if str(c.get("group_id")) == str(group.id)]
    min_threshold = MIN_FEEDS_THRESHOLD_DEFAULT

    has_daily = any(_count_items(c, "feed") >= min_threshold for c in ready_collections)
    if has_daily:
        return CADENCE_BUCKETS[0]

    # Assume 3-day may allow bundling; still require same threshold at collection level
    has_three_day = any(_count_items(c, "feed") >= min_threshold for c in ready_collections)
    if has_three_day:
        return CADENCE_BUCKETS[1]

    return CADENCE_BUCKETS[2]


def _should_release_now_for_bucket(last_episode_time: Optional[datetime], bucket_days: int) -> bool:
    if not last_episode_time:
        return True
    next_allowed = last_episode_time + timedelta(days=bucket_days)
    return datetime.utcnow() >= next_allowed


@celery.task(bind=True)
def generate_episode_for_group(self, group_id: str) -> Dict[str, Any]:
    """Generate a complete episode for a podcast group."""
    task_id = self.request.id
    
    try:
        logger.info(f"Starting episode generation for group {group_id} (task: {task_id})")
        
        # Initialize services
        generation_service = EpisodeGenerationService()
        
        # Generate episode (run async function in sync context)
        import asyncio
        # If a preferred collection was attached to the task request, pass it through
        preferred_collection_id = None
        try:
            req_kwargs = getattr(self.request, 'kwargs', {}) or {}
            preferred_collection_id = req_kwargs.get('collection_id')
        except Exception:
            preferred_collection_id = None

        result = asyncio.run(
            generation_service.generate_complete_episode(UUID(group_id), collection_id=preferred_collection_id)
        )
        
        logger.info(f"Episode generation completed for group {group_id}")
        return {
            "status": "success",
            "episode_id": str(result["episode_id"]),
            "message": "Episode generated successfully"
        }
        
    except Exception as e:
        logger.error(f"Error generating episode for group {group_id}: {e}")
        return {
            "status": "error",
            "error": str(e),
            "message": "Episode generation failed"
        }


@celery.task
def check_scheduled_groups():
    """Adaptive cadence scheduler.
    - Evaluates groups per cadence buckets (daily -> 3-day -> weekly)
    - Uses Collections readiness to decide release eligibility
    - Selects highest-ranked ready collection for release per slot
    - Removes artificial one-per-day bottleneck by conditional cadence enforcement
    """
    try:
        logger.info("Checking scheduled podcast groups with adaptive cadence")
        
        db = get_db_session()
        try:
            # Get all active podcast groups
            active_groups = db.query(PodcastGroup).filter(
                PodcastGroup.status == "active"
            ).all()
            
            ready_collections = _get_ready_collections()
            groups_to_process: List[Tuple[PodcastGroup, Dict[str, Any]]] = []
            
            for group in active_groups:
                # Determine current cadence bucket for the group
                bucket_name, bucket_days = _current_bucket_for_group(db, group)

                # Last published episode for cadence gating
                last_episode = db.query(Episode).filter(
                    Episode.group_id == group.id,
                    Episode.status == EpisodeStatus.PUBLISHED
                ).order_by(Episode.created_at.desc()).first()

                if not _should_release_now_for_bucket(
                    last_episode.created_at if last_episode else None,
                    bucket_days
                ):
                    logger.info(
                        f"Cadence gate not reached for group={group.id} bucket={bucket_name}"
                    )
                    continue

                # Find ready collections for this group
                candidate_collections = [
                    c for c in ready_collections if str(c.get("group_id")) == str(group.id)
                ]

                # Enforce threshold (feeds >= N)
                min_threshold = MIN_FEEDS_THRESHOLD_DEFAULT
                candidate_collections = [
                    c for c in candidate_collections if _count_items(c, "feed") >= min_threshold
                ]

                if not candidate_collections:
                    logger.info(
                        f"No ready collections meeting threshold for group={group.id}; "
                        f"bucket={bucket_name}"
                    )
                    continue

                best = _select_best_collection(candidate_collections)
                if best:
                    groups_to_process.append((group, best))
            
            logger.info(
                f"Found {len(groups_to_process)} group/collection pairs ready for episode generation"
            )
            
            # Queue episode generation for each group
            for group, collection in groups_to_process:
                logger.info(
                    {
                        "event": "cadence_selection",
                        "group_id": str(group.id),
                        "collection_id": collection.get("collection_id"),
                        "feed_count": _count_items(collection, "feed"),
                        "review_count": _count_items(collection, "review"),
                        "reason": "selected_top_ranked_ready_collection"
                    }
                )
                # Pass selected collection id through to episode generation task
                generate_episode_for_group.apply_async(args=[str(group.id)], kwargs={
                    "collection_id": collection.get("collection_id")
                })
                
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error checking scheduled groups (adaptive): {e}")


@celery.task
def fetch_all_news_feeds():
    """Fetch articles from all active news feeds."""
    try:
        logger.info("Fetching news from all active feeds")
        
        db = get_db_session()
        try:
            # Get all active news feeds
            active_feeds = db.query(NewsFeed).filter(
                NewsFeed.is_active == True
            ).all()
            
            # Trigger fetch for each feed
            for feed in active_feeds:
                try:
                    # Call news feed service to fetch articles
                    async def fetch_feed():
                        async with httpx.AsyncClient() as client:
                            response = await client.post(
                                f"http://news-feed:8001/feeds/{feed.id}/fetch"
                            )
                            response.raise_for_status()
                    
                    import asyncio
                    asyncio.run(fetch_feed())
                    
                except Exception as e:
                    logger.error(f"Error fetching feed {feed.id}: {e}")
                    
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error in fetch_all_news_feeds task: {e}")


@celery.task
def create_collections_from_articles():
    """Create collections from reviewed articles."""
    try:
        logger.info("Creating collections from reviewed articles")
        
        db = get_db_session()
        try:
            # Get reviewed articles that aren't already in collections
            reviewed_articles = db.query(Article).filter(
                Article.reviewer_type.isnot(None),  # Already reviewed
                Article.collection_id.is_(None),    # Not yet in a collection
                Article.confidence.isnot(None)      # Has confidence score
            ).order_by(Article.processed_at.desc()).limit(50).all()
            
            if len(reviewed_articles) >= 3:  # Minimum threshold
                # Group articles by topic/theme for better collections
                articles_by_topic = {}
                for article in reviewed_articles:
                    # Use reviewer tags to group articles
                    tags = article.review_tags or ["general"]
                    primary_tag = tags[0] if tags else "general"
                    
                    if primary_tag not in articles_by_topic:
                        articles_by_topic[primary_tag] = []
                    articles_by_topic[primary_tag].append(article)
                
                # Check for existing collections and add articles to them, or create new ones
                for topic, articles in articles_by_topic.items():
                    if len(articles) >= 3:  # Minimum articles per collection
                        try:
                            # Check if we already have a collection for this topic
                            existing_collection = db.query(Collection).filter(
                                Collection.name == f"Auto Collection: {topic.title()}"
                            ).first()
                            
                            if existing_collection:
                                # Add articles to existing collection
                                for article in articles:
                                    article.collection_id = existing_collection.id
                                db.commit()
                                logger.info(f"Added {len(articles)} articles to existing collection {existing_collection.id} for topic '{topic}'")
                            else:
                                # Create new collection
                                async def create_collection():
                                    async with httpx.AsyncClient() as client:
                                        collection_data = {
                                            "name": f"Auto Collection: {topic.title()}",
                                            "description": f"Automatically created collection of {topic} articles",
                                            "group_ids": [],  # Independent collection
                                            "status": "building"
                                        }
                                        
                                        response = await client.post(
                                            "http://collections:8011/collections",
                                            json=collection_data
                                        )
                                        response.raise_for_status()
                                        collection = response.json()
                                        
                                        # Add articles to collection by updating their collection_id
                                        for article in articles:
                                            article.collection_id = UUID(collection['collection']['collection_id'])
                                        
                                        db.commit()
                                        
                                        logger.info(f"Created collection {collection['collection']['collection_id']} for topic '{topic}' with {len(articles)} articles")
                                
                                import asyncio
                                asyncio.run(create_collection())
                            
                        except Exception as e:
                            logger.error(f"Error creating/updating collection for topic {topic}: {e}")
            else:
                logger.info(f"Not enough reviewed articles to create collections (need 3+, have {len(reviewed_articles)})")
                    
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error in create_collections_from_articles task: {e}")


@celery.task
def update_collection_status():
    """Update collection status from building to ready when they have enough articles."""
    try:
        logger.info("Updating collection status")
        
        db = get_db_session()
        try:
            # Get collections that are in building status
            building_collections = db.query(Collection).filter(
                Collection.status == "building"
            ).all()
            
            for collection in building_collections:
                # Count articles in this collection
                article_count = db.query(Article).filter(Article.collection_id == collection.id).count()
                
                # If collection has enough articles, mark it as ready
                if article_count >= 3:  # Minimum threshold for ready status
                    collection.status = "ready"
                    db.commit()
                    logger.info(f"Updated collection {collection.id} ({collection.name}) to ready status with {article_count} articles")
                else:
                    logger.info(f"Collection {collection.id} ({collection.name}) still building with {article_count} articles")
                    
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error in update_collection_status task: {e}")


@celery.task
def send_articles_to_reviewer():
    """Send unreviewed articles to the Reviewer service."""
    try:
        logger.info("Sending unreviewed articles to reviewer")
        
        db = get_db_session()
        try:
            # Get unreviewed articles (limit to 50 per run)
            unreviewed_articles = db.query(Article).filter(
                Article.reviewer_type.is_(None)  # Not yet reviewed
            ).limit(50).all()
            
            if not unreviewed_articles:
                logger.info("No unreviewed articles found")
                return
            
            logger.info(f"Found {len(unreviewed_articles)} unreviewed articles")
            
            # Send articles to reviewer service
            async def send_to_reviewer():
                async with httpx.AsyncClient() as client:
                    for article in unreviewed_articles:
                        try:
                            review_data = {
                                "feed_id": str(article.feed_id),
                                "title": article.title,
                                "url": article.link,
                                "content": article.content or article.summary or "",
                                "published": article.publish_date.isoformat() if article.publish_date else None
                            }
                            
                            response = await client.post(
                                "http://reviewer:8008/review",
                                json=review_data,
                                timeout=30.0
                            )
                            response.raise_for_status()
                            
                            logger.info(f"Sent article {article.id} to reviewer")
                            
                        except Exception as e:
                            logger.error(f"Error sending article {article.id} to reviewer: {e}")
            
            import asyncio
            asyncio.run(send_to_reviewer())
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error in send_articles_to_reviewer task: {e}")


def should_generate_episode(group: PodcastGroup) -> bool:
    """Check if a podcast group should generate a new episode based on schedule."""
    try:
        from croniter import croniter
        
        if not group.schedule:
            return False
        
        # Get the last episode for this group
        db = get_db_session()
        try:
            last_episode = db.query(Episode).filter(
                Episode.group_id == group.id,
                Episode.status == EpisodeStatus.PUBLISHED
            ).order_by(Episode.created_at.desc()).first()
            
            if not last_episode:
                # No episodes yet, generate first one
                return True
            
            # Check if schedule indicates time for new episode
            cron = croniter(group.schedule, last_episode.created_at)
            next_run = cron.get_next(datetime)
            
            return datetime.utcnow() >= next_run
            
        except Exception as e:
            logger.error(f"Error checking schedule for group {group.id}: {e}")
            return False
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error in should_generate_episode: {e}")
        return False


@celery.task
def cleanup_old_episodes():
    """Clean up old episode files and database records."""
    try:
        logger.info("Starting cleanup of old episodes")
        
        db = get_db_session()
        try:
            # Delete episodes older than 90 days
            cutoff_date = datetime.utcnow() - timedelta(days=90)
            
            old_episodes = db.query(Episode).filter(
                Episode.created_at < cutoff_date,
                Episode.status == EpisodeStatus.PUBLISHED
            ).all()
            
            for episode in old_episodes:
                # Delete audio files
                audio_file = episode.audio_file
                if audio_file and audio_file.url:
                    try:
                        import os
                        if os.path.exists(audio_file.url):
                            os.unlink(audio_file.url)
                    except Exception as e:
                        logger.warning(f"Could not delete audio file {audio_file.url}: {e}")
                
                # Delete database records
                db.delete(episode)
            
            db.commit()
            logger.info(f"Cleaned up {len(old_episodes)} old episodes")
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error in cleanup_old_episodes task: {e}")


@celery.task
def health_check_services():
    """Check health of all services."""
    try:
        services = {
            "news-feed": "http://news-feed:8001/health",
            "text-generation": "http://text-generation:8002/health",
            "writer": "http://writer:8003/health",
            "presenter": "http://presenter:8004/health",
            "publishing": "http://publishing:8005/health",
        }
        
        health_status = {}
        
        async def check_service(name, url):
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(url)
                    health_status[name] = "healthy" if response.status_code == 200 else "unhealthy"
            except Exception as e:
                health_status[name] = f"error: {str(e)}"
        
        import asyncio
        tasks = [check_service(name, url) for name, url in services.items()]
        asyncio.run(asyncio.gather(*tasks))
        
        logger.info(f"Service health check completed: {health_status}")
        return health_status
        
    except Exception as e:
        logger.error(f"Error in health_check_services task: {e}")
        return {"error": str(e)}
