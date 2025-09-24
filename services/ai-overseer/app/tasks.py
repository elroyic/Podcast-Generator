"""
Celery tasks for the AI Overseer service.
"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
from uuid import UUID

import httpx
from celery import current_task
from sqlalchemy.orm import Session

from shared.database import get_db_session
from shared.models import PodcastGroup, NewsFeed, Article, Episode, EpisodeStatus
from shared.schemas import GenerationRequest, GenerationResponse
from .celery import celery
from .services import EpisodeGenerationService, NewsFeedService, TextGenerationService, WriterService, PresenterService, PublishingService

logger = logging.getLogger(__name__)


@celery.task(bind=True)
def generate_episode_for_group(self, group_id: str) -> Dict[str, Any]:
    """Generate a complete episode for a podcast group."""
    task_id = self.request.id
    
    try:
        logger.info(f"Starting episode generation for group {group_id} (task: {task_id})")
        
        # Initialize services
        generation_service = EpisodeGenerationService()
        
        # Generate episode
        result = generation_service.generate_complete_episode(UUID(group_id))
        
        logger.info(f"Episode generation completed for group {group_id}")
        return {
            "status": "success",
            "episode_id": str(result.get("episode_id")),
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
    """Check for podcast groups that need new episodes based on their schedule."""
    try:
        logger.info("Checking scheduled podcast groups")
        
        db = get_db_session()
        try:
            # Get all active podcast groups
            active_groups = db.query(PodcastGroup).filter(
                PodcastGroup.status == "active"
            ).all()
            
            groups_to_process = []
            
            for group in active_groups:
                if group.schedule:
                    # Check if it's time to generate a new episode
                    if should_generate_episode(group):
                        groups_to_process.append(group)
            
            logger.info(f"Found {len(groups_to_process)} groups ready for episode generation")
            
            # Queue episode generation for each group
            for group in groups_to_process:
                generate_episode_for_group.delay(str(group.id))
                
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error checking scheduled groups: {e}")


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


def should_generate_episode(group: PodcastGroup) -> bool:
    """Check if a podcast group should generate a new episode based on schedule."""
    try:
        from croniter import croniter
        
        if not group.schedule:
            return False
        
        # Get the last episode for this group
        db = get_db_session()
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
        try:
            db.close()
        except Exception:
            pass


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
