
"""
Service clients for communicating with other microservices.
"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from uuid import UUID

import httpx
import redis
from sqlalchemy.orm import Session

# Add the shared directory to Python path
import sys
import os
sys.path.append('/app/shared')

from database import get_db_session
from models import PodcastGroup, Article, Episode, EpisodeStatus, EpisodeMetadata, AudioFile

logger = logging.getLogger(__name__)

# Initialize Redis
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")


class CadenceManager:
    """Manages episode generation cadence and prevents overlapping runs."""
    
    def __init__(self):
        self.redis = redis.Redis.from_url(REDIS_URL, decode_responses=True)
    
    def acquire_group_lock(self, group_id: UUID, timeout_hours: int = 1) -> bool:
        """Acquire lock for a podcast group to prevent overlapping generation."""
        lock_key = f"overseer:group:{group_id}:lock"
        lock_value = f"locked_at_{int(datetime.utcnow().timestamp())}"
        
        # Use Redis SETNX with TTL to acquire lock
        return self.redis.set(lock_key, lock_value, nx=True, ex=timeout_hours * 3600)
    
    def release_group_lock(self, group_id: UUID):
        """Release lock for a podcast group."""
        lock_key = f"overseer:group:{group_id}:lock"
        self.redis.delete(lock_key)
    
    def is_group_locked(self, group_id: UUID) -> bool:
        """Check if a group is currently locked."""
        lock_key = f"overseer:group:{group_id}:lock"
        return self.redis.exists(lock_key)
    
    def get_cadence_status(self, group_id: UUID, db: Session) -> Dict[str, Any]:
        """Get cadence status for a podcast group."""
        group = db.query(PodcastGroup).filter(PodcastGroup.id == group_id).first()
        if not group:
            return {"error": "Group not found"}
        
        # Get last published episode
        last_episode = db.query(Episode).filter(
            Episode.group_id == group_id,
            Episode.status == EpisodeStatus.PUBLISHED
        ).order_by(Episode.created_at.desc()).first()
        
        last_published_at = last_episode.created_at if last_episode else None
        
        # Determine cadence bucket based on activity
        bucket, next_eligible_at, reason = self._determine_cadence_bucket(
            group_id, last_published_at, db
        )
        
        return {
            "group_id": str(group_id),
            "bucket": bucket,
            "last_published_at": last_published_at.isoformat() if last_published_at else None,
            "next_eligible_at": next_eligible_at.isoformat() if next_eligible_at else None,
            "reason": reason,
            "locked": self.is_group_locked(group_id)
        }
    
    def _determine_cadence_bucket(self, group_id: UUID, last_published_at: Optional[datetime], db: Session) -> tuple:
        """Determine the appropriate cadence bucket for a group."""
        now = datetime.utcnow()
        
        # Get feed count for this group
        group = db.query(PodcastGroup).filter(PodcastGroup.id == group_id).first()
        feed_count = len(group.news_feeds) if group and group.news_feeds else 0
        
        # Get recent article count
        recent_articles = 0
        if feed_count > 0:
            recent_articles = db.query(Article).filter(
                Article.feed_id.in_([f.id for f in group.news_feeds]),
                Article.created_at >= now - timedelta(hours=24)
            ).count()
        
        # Adaptive cadence logic
        min_feeds_threshold = int(os.getenv("MIN_FEEDS_THRESHOLD", "5"))
        
        if feed_count < min_feeds_threshold or recent_articles < 3:
            # Weekly cadence for low activity
            bucket = "Weekly"
            next_eligible = (last_published_at or now) + timedelta(days=7)
            reason = f"Low activity: {feed_count} feeds, {recent_articles} recent articles"
        elif recent_articles >= 10:
            # Daily cadence for high activity
            bucket = "Daily"
            next_eligible = (last_published_at or now) + timedelta(days=1)
            reason = f"High activity: {recent_articles} recent articles"
        else:
            # 3-day cadence for medium activity
            bucket = "3-Day"
            next_eligible = (last_published_at or now) + timedelta(days=3)
            reason = f"Medium activity: {recent_articles} recent articles"
        
        return bucket, next_eligible, reason
    
    def get_all_cadence_statuses(self, db: Session) -> List[Dict[str, Any]]:
        """Get cadence status for all active podcast groups."""
        groups = db.query(PodcastGroup).filter(PodcastGroup.status == "active").all()
        statuses = []
        
        for group in groups:
            status = self.get_cadence_status(group.id, db)
            status["group_name"] = group.name
            statuses.append(status)
        
        return statuses


class ServiceClient:
    """Base client for service communication."""
    
    def __init__(self, base_url: str, timeout: float = 60.0):
        self.base_url = base_url
        self.timeout = timeout
    
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request to service."""
        url = f"{self.base_url}{endpoint}"
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()


class NewsFeedService(ServiceClient):
    """Client for News Feed Service."""
    
    def __init__(self):
        super().__init__("http://news-feed:8001")
    
    async def get_recent_articles(
        self,
        group_id: UUID,
        hours: int = 24,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get recent articles for a podcast group."""
        try:
            # Get articles from assigned feeds
            db = get_db_session()
            try:
                group = db.query(PodcastGroup).filter(PodcastGroup.id == group_id).first()
                if not group:
                    return []
                
                # Get articles from assigned feeds
                feed_ids = [feed.id for feed in group.news_feeds]
                if not feed_ids:
                    return []
                
                articles = db.query(Article).filter(
                    Article.feed_id.in_(feed_ids)
                ).order_by(Article.publish_date.desc()).limit(limit).all()
                
                return [
                    {
                        "id": str(article.id),
                        "title": article.title,
                        "link": article.link,
                        "summary": article.summary,
                        "content": article.content,
                        "publish_date": article.publish_date.isoformat() if article.publish_date else None
                    }
                    for article in articles
                ]
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error getting recent articles: {e}")
            return []


class CollectionsService(ServiceClient):
    """Client for Collections Service."""

    def __init__(self):
        super().__init__("http://collections:8011")

    async def get_collection(self, collection_id: str) -> Optional[Dict[str, Any]]:
        try:
            return await self._make_request("GET", f"/collections/{collection_id}")
        except Exception as e:
            logger.error(f"Error fetching collection {collection_id}: {e}")
            return None


class TextGenerationService(ServiceClient):
    """Client for Text Generation Service."""
    
    def __init__(self):
        super().__init__("http://text-generation:8002")
    
    async def generate_script(
        self,
        group_id: UUID,
        article_summaries: List[Dict[str, Any]],
        target_duration: int = 75
    ) -> Dict[str, Any]:
        """Generate podcast script from articles."""
        try:
            request_data = {
                "group_id": str(group_id),
                "article_summaries": article_summaries,
                "target_duration_minutes": target_duration
            }
            
            return await self._make_request("POST", "/generate-script", json=request_data)
            
        except Exception as e:
            logger.error(f"Error generating script: {e}")
            raise


class WriterService(ServiceClient):
    """Client for Writer Service."""
    
    def __init__(self):
        super().__init__("http://writer:8003")
    
    async def generate_script(
        self,
        group_id: UUID,
        articles: List[str]
    ) -> Dict[str, Any]:
        """Generate episode script from articles."""
        try:
            request_data = {
                "group_id": str(group_id),
                "articles": articles
            }
            
            return await self._make_request("POST", "/generate-script", json=request_data)
            
        except Exception as e:
            logger.error(f"Error generating script: {e}")
            raise
    
    async def generate_metadata(
        self,
        episode_id: UUID,
        script: str,
        group_id: UUID
    ) -> Dict[str, Any]:
        """Generate episode metadata from script."""
        try:
            request_data = {
                "episode_id": str(episode_id),
                "script": script,
                "group_id": str(group_id)
            }
            
            return await self._make_request("POST", "/generate-metadata", json=request_data)
            
        except Exception as e:
            logger.error(f"Error generating metadata: {e}")
            raise


class EditorService(ServiceClient):
    """Client for Editor Service."""
    
    def __init__(self):
        super().__init__("http://editor:8010")
    
    async def edit_script(
        self,
        script_id: str,
        script: str,
        collection_context: Dict[str, Any],
        target_length_minutes: int = 10
    ) -> Dict[str, Any]:
        """Edit and polish a script."""
        try:
            request_data = {
                "script_id": script_id,
                "script": script,
                "collection_context": collection_context,
                "target_length_minutes": target_length_minutes,
                "target_audience": "general"
            }
            
            return await self._make_request("POST", "/edit-script", json=request_data)
            
        except Exception as e:
            logger.error(f"Error editing script: {e}")
            raise


class PresenterService(ServiceClient):
    """Client for Presenter Service."""
    
    def __init__(self):
        super().__init__("http://presenter:8004")
    
    async def generate_audio(
        self,
        episode_id: UUID,
        script: str,
        presenter_ids: List[UUID]
    ) -> Dict[str, Any]:
        """Generate audio from script."""
        try:
            request_data = {
                "episode_id": str(episode_id),
                "script": script,
                "presenter_ids": [str(pid) for pid in presenter_ids]
            }
            
            return await self._make_request("POST", "/generate-audio", json=request_data)
            
        except Exception as e:
            logger.error(f"Error generating audio: {e}")
            raise


class PublishingService(ServiceClient):
    """Client for Publishing Service."""
    
    def __init__(self):
        super().__init__("http://publishing:8005")
    
    async def publish_episode(
        self,
        episode_id: UUID,
        platforms: List[str],
        credentials: Dict[str, Dict[str, str]]
    ) -> Dict[str, Any]:
        """Publish episode to platforms."""
        try:
            request_data = {
                "episode_id": str(episode_id),
                "platforms": platforms,
                "platform_credentials": credentials
            }
            
            return await self._make_request("POST", "/publish", json=request_data)
            
        except Exception as e:
            logger.error(f"Error publishing episode: {e}")
            raise


class EpisodeGenerationService:
    """Orchestrates the complete episode generation process."""
    
    def __init__(self):
        self.news_feed_service = NewsFeedService()
        self.collections_service = CollectionsService()
        self.text_generation_service = TextGenerationService()
        self.writer_service = WriterService()
        self.editor_service = EditorService()
        self.presenter_service = PresenterService()
        self.publishing_service = PublishingService()
        self.cadence_manager = CadenceManager()
        # Feature flag: allow switching script generation source
        self.use_writer_for_script = str(os.getenv("USE_WRITER_FOR_SCRIPT", "true")).lower() in ("1", "true", "yes")
    
    async def generate_complete_episode(self, group_id: UUID, collection_id: Optional[str] = None) -> Dict[str, Any]:
        """Generate a complete episode from start to finish."""
        db = get_db_session()
        
        try:
            logger.info(f"Starting complete episode generation for group {group_id}")
            
            # Step 0: Acquire lock to prevent overlapping runs
            if not self.cadence_manager.acquire_group_lock(group_id):
                raise ValueError(f"Another episode generation is already in progress for group {group_id}")
            
            # Step 1: Get podcast group details
            group = db.query(PodcastGroup).filter(PodcastGroup.id == group_id).first()
            if not group:
                self.cadence_manager.release_group_lock(group_id)
                raise ValueError(f"Podcast group {group_id} not found")
            
            # Step 2: Gather article summaries (prefer selected collection if provided)
            articles: List[Dict[str, Any]] = []
            if collection_id:
                logger.info(f"Using selected collection {collection_id} for content")
                collection = await self.collections_service.get_collection(collection_id)
                if collection:
                    # Extract feeds as article summaries
                    for item in collection.get("items", []):
                        if item.get("item_type") == "feed":
                            content = item.get("content", {})
                            articles.append({
                                "title": content.get("title"),
                                "summary": content.get("summary"),
                                "link": content.get("link"),
                                "publish_date": content.get("publish_date")
                            })
            if not articles:
                logger.info("Falling back to recent articles from NewsFeedService")
                articles = await self.news_feed_service.get_recent_articles(group_id)
            if not articles:
                raise ValueError("No article content available to generate episode")
            
            # Step 3: Generate script (Writer by default; can toggle to TextGeneration)
            if self.use_writer_for_script:
                logger.info("Generating podcast script with Writer service")
                article_contents = [f"{a.get('title', '')} - {a.get('summary', '')[:500]}" for a in articles]
                script_result = await self.writer_service.generate_script(group_id, article_contents)
                script = script_result["script"]
            else:
                logger.info("Generating podcast script with Text-Generation service")
                # Use summaries as input for text-generation service
                tg_result = await self.text_generation_service.generate_script(
                    group_id=group_id,
                    article_summaries=articles,
                    target_duration=75
                )
                script = tg_result.get("script") or tg_result.get("raw_script") or ""
                if not script:
                    raise ValueError("Text-Generation did not return a script")
            
            # Step 4: Create episode record
            logger.info("Creating episode record")
            episode = Episode(
                group_id=group_id,
                script=script,
                status=EpisodeStatus.DRAFT
            )
            db.add(episode)
            db.commit()
            db.refresh(episode)
            
            # Step 5: Edit script using Editor service
            logger.info("Editing and polishing script")
            try:
                collection_context = {
                    "group_name": group.name,
                    "category": group.category or "General",
                    "article_count": len(articles),
                    "target_audience": "general"
                }
                
                edit_result = await self.editor_service.edit_script(
                    script_id=str(episode.id),
                    script=script,
                    collection_context=collection_context,
                    target_length_minutes=10
                )
                
                # Update script with edited version
                if "review" in edit_result and "edited_script" in edit_result["review"]:
                    original_script = script
                    script = edit_result["review"]["edited_script"]
                    episode.script = script
                    db.commit()
                    logger.info("Script updated with edited version")
                
            except Exception as e:
                logger.warning(f"Script editing failed, using original script: {e}")
                # Continue with original script if editing fails
            
            # Step 6: Generate metadata
            logger.info("Generating episode metadata")
            metadata_result = await self.writer_service.generate_metadata(
                episode.id, script, group_id
            )
            metadata_data = metadata_result["metadata"]
            
            # Create metadata record
            metadata = EpisodeMetadata(
                episode_id=episode.id,
                **metadata_data
            )
            db.add(metadata)
            db.commit()
            
            # Step 7: Generate audio
            logger.info("Generating audio")
            presenter_ids = [p.id for p in group.presenters]
            audio_result = await self.presenter_service.generate_audio(
                episode.id, script, presenter_ids
            )
            
            # Step 7.1: Create AudioFile record
            if "audio_url" in audio_result:
                logger.info("Creating AudioFile record")
                audio_file = AudioFile(
                    episode_id=episode.id,
                    url=audio_result["audio_url"],
                    duration_seconds=audio_result.get("duration_seconds"),
                    file_size_bytes=audio_result.get("file_size_bytes"),
                    format=audio_result.get("format", "mp3")
                )
                db.add(audio_file)
            
            # Update episode status
            episode.status = EpisodeStatus.VOICED
            db.commit()
            
            # Step 8: Publish episode to local platforms
            logger.info("Publishing episode to local platforms")
            try:
                publish_result = await self.publishing_service.publish_episode(
                    episode.id,
                    platforms=["local_podcast_host", "local_rss_feed", "local_directory"],
                    credentials={}  # No credentials needed for local platforms
                )
                episode.status = EpisodeStatus.PUBLISHED
                db.commit()
            except Exception as e:
                logger.warning(f"Publishing failed, episode saved as voiced: {e}")
            
            logger.info(f"Episode generation completed: {episode.id}")
            
            # Release lock after successful completion
            self.cadence_manager.release_group_lock(group_id)
            
            return {
                "episode_id": episode.id,
                "status": episode.status,
                "script_length": len(script.split()),
                "audio_url": audio_result.get("audio_url"),
                "duration_seconds": audio_result.get("duration_seconds")
            }
            
        except Exception as e:
            logger.error(f"Error in episode generation: {e}")
            db.rollback()
            # Release lock on error
            self.cadence_manager.release_group_lock(group_id)
            raise
        finally:
            db.close()
