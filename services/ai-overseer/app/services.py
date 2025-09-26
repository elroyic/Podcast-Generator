
"""
Service clients for communicating with other microservices.
"""
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from uuid import UUID

import httpx
from sqlalchemy.orm import Session

# Add the shared directory to Python path
import sys
import os
sys.path.append('/app/shared')

from database import get_db_session
from models import PodcastGroup, Article, Episode, EpisodeStatus, EpisodeMetadata, AudioFile

logger = logging.getLogger(__name__)


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
        self.presenter_service = PresenterService()
        self.publishing_service = PublishingService()
    
    async def generate_complete_episode(self, group_id: UUID, collection_id: Optional[str] = None) -> Dict[str, Any]:
        """Generate a complete episode from start to finish."""
        db = get_db_session()
        
        try:
            logger.info(f"Starting complete episode generation for group {group_id}")
            
            # Step 1: Get podcast group details
            group = db.query(PodcastGroup).filter(PodcastGroup.id == group_id).first()
            if not group:
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
            
            # Step 3: Generate script
            logger.info("Generating podcast script")
            script_result = await self.text_generation_service.generate_script(
                group_id, articles, target_duration=75
            )
            script = script_result["script"]
            
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
            
            # Step 5: Generate metadata
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
            
            # Step 6: Generate audio
            logger.info("Generating audio")
            presenter_ids = [p.id for p in group.presenters]
            audio_result = await self.presenter_service.generate_audio(
                episode.id, script, presenter_ids
            )
            
            # Update episode status
            episode.status = EpisodeStatus.VOICED
            db.commit()
            
            # Step 7: Publish episode (optional - can be done later)
            logger.info("Publishing episode")
            try:
                publish_result = await self.publishing_service.publish_episode(
                    episode.id,
                    platforms=["anchor"],  # Default platform
                    credentials={}  # Would need actual credentials
                )
                episode.status = EpisodeStatus.PUBLISHED
                db.commit()
            except Exception as e:
                logger.warning(f"Publishing failed, episode saved as voiced: {e}")
            
            logger.info(f"Episode generation completed: {episode.id}")
            
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
            raise
        finally:
            db.close()
