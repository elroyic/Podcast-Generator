
"""
Service clients for communicating with other microservices.
"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from uuid import UUID
import json
import hashlib

import httpx
import redis
from sqlalchemy.orm import Session

# Add the shared directory to Python path
import sys
import os
sys.path.append('/app/shared')

from database import get_db_session
from models import PodcastGroup, Article, Episode, EpisodeStatus, EpisodeMetadata, AudioFile, Presenter, NewsFeed

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
    
    def __init__(self, base_url: str, timeout: float = 180.0):
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
    
    async def get_active_collection_for_group(self, group_id: UUID) -> Optional[Dict[str, Any]]:
        """Get the active building collection for a group."""
        try:
            return await self._make_request("GET", f"/collections/group/{str(group_id)}/active")
        except Exception as e:
            logger.error(f"Error fetching active collection for group {group_id}: {e}")
            return None
    
    async def create_snapshot(self, collection_id: str, episode_id: str) -> Optional[str]:
        """Create a snapshot of a collection for an episode."""
        try:
            result = await self._make_request(
                "POST", 
                f"/collections/{collection_id}/snapshot",
                params={"episode_id": episode_id}
            )
            return result.get("snapshot_id")
        except Exception as e:
            logger.error(f"Error creating collection snapshot: {e}")
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
        super().__init__("http://editor:8009")
    
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
    
    async def generate_brief(
        self,
        presenter_id: UUID,
        collection_id: str,
        articles: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate a 1000-word brief from a presenter on a collection."""
        try:
            request_data = {
                "presenter_id": str(presenter_id),
                "collection_id": collection_id,
                "articles": articles
            }
            
            return await self._make_request("POST", "/generate-brief", json=request_data)
            
        except Exception as e:
            logger.error(f"Error generating presenter brief: {e}")
            raise
    
    async def generate_feedback(
        self,
        presenter_id: UUID,
        script_id: str,
        script: str,
        collection_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate 500-word feedback from a presenter on a script."""
        try:
            request_data = {
                "presenter_id": str(presenter_id),
                "script_id": script_id,
                "script": script,
                "collection_context": collection_context
            }
            
            return await self._make_request("POST", "/generate-feedback", json=request_data)
            
        except Exception as e:
            logger.error(f"Error generating presenter feedback: {e}")
            raise
    
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
    


class TTSService(ServiceClient):
    """Client for TTS Service (VibeVoice audio generation only)."""
    
    def __init__(self):
        super().__init__("http://tts:8015")
    
    async def generate_audio(
        self,
        episode_id: UUID,
        script: str,
        duration_seconds: Optional[int] = None
    ) -> Dict[str, Any]:
        """Generate audio from script using VibeVoice."""
        try:
            request_data = {
                "episode_id": str(episode_id),
                "script": script,
                "duration_seconds": duration_seconds
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


class PersonaGenerationService:
    """Service for generating presenter personas using LLM."""
    
    def __init__(self):
        self.text_generation_service = TextGenerationService()
    
    def _create_persona_system_prompt(self) -> str:
        """Create system prompt for persona generation."""
        return """
You are an expert at creating engaging podcast presenter personas. Generate unique, memorable, and authentic presenter characters that would be perfect for podcast hosting.

For each persona, create:
1. A distinctive name that fits the character
2. A compelling bio that shows personality and expertise
3. A detailed persona description with speaking style, interests, and quirks
4. Voice characteristics and speaking patterns
5. A system prompt that defines how this presenter should behave

Make each persona:
- Unique and memorable
- Authentic and relatable
- Professional yet personable
- Suited for podcast hosting
- Distinctive in voice and style
- Engaging and entertaining

Return your response as valid JSON with the following structure:
{
    "name": "Presenter Name",
    "bio": "Brief bio describing the presenter",
    "persona": "Detailed persona description including speaking style, interests, personality traits",
    "voice_style": "Description of voice characteristics and speaking patterns",
    "system_prompt": "System prompt that defines how this presenter should behave when reviewing content and providing feedback"
}
"""
    
    def _create_persona_content_prompt(self, group_category: str, recent_articles: List[str]) -> str:
        """Create content prompt for persona generation based on group context."""
        articles_context = ""
        if recent_articles:
            articles_context = f"""
Recent article topics to consider for expertise areas:
{chr(10).join([f"- {article[:100]}..." for article in recent_articles[:5]])}
"""
        
        return f"""
Create a unique podcast presenter persona for a {group_category} podcast.

{articles_context}

Requirements:
- The persona should be well-suited for {group_category} content
- Make them knowledgeable but approachable
- Give them a distinctive personality and speaking style
- Include specific expertise areas relevant to {group_category}
- Make them engaging and entertaining
- Ensure they would be good at reviewing and discussing content

Generate a complete persona that would be perfect for hosting a {group_category} podcast.
"""
    
    async def generate_presenter_persona(
        self,
        group_id: UUID,
        group_category: str = "General",
        recent_articles: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Generate a presenter persona using LLM."""
        try:
            logger.info(f"Generating presenter persona for {group_category} group {group_id}")
            
            # Get recent article titles for context
            if not recent_articles:
                db = get_db_session()
                try:
                    group = db.query(PodcastGroup).filter(PodcastGroup.id == group_id).first()
                    if group and group.news_feeds:
                        feed_ids = [feed.id for feed in group.news_feeds]
                        articles = db.query(Article).filter(
                            Article.feed_id.in_(feed_ids)
                        ).order_by(Article.created_at.desc()).limit(10).all()
                        recent_articles = [article.title for article in articles]
                finally:
                    db.close()
            
            # Create prompts
            system_prompt = self._create_persona_system_prompt()
            content_prompt = self._create_persona_content_prompt(group_category, recent_articles or [])
            
            # Use text generation service to create persona
            request_data = {
                "group_id": str(group_id),
                "article_summaries": [{"title": title, "summary": "", "link": ""} for title in (recent_articles or [])],
                "target_duration_minutes": 1,  # Not used for persona generation
                "style_preferences": {
                    "task": "persona_generation",
                    "system_prompt": system_prompt,
                    "content_prompt": content_prompt
                }
            }
            
            # Make a custom request to text generation service
            async with httpx.AsyncClient(timeout=180.0) as client:
                response = await client.post(
                    "http://text-generation:8002/generate-script",
                    json=request_data
                )
                response.raise_for_status()
                result = response.json()
            
            # Extract persona from the generated script
            script = result.get("script", "")
            
            # Try to parse JSON from the script
            try:
                # Look for JSON in the script
                import re
                json_match = re.search(r'\{.*\}', script, re.DOTALL)
                if json_match:
                    persona_data = json.loads(json_match.group())
                else:
                    # Fallback: create persona from script content
                    persona_data = self._create_fallback_persona(script, group_category)
            except json.JSONDecodeError:
                # Fallback: create persona from script content
                persona_data = self._create_fallback_persona(script, group_category)
            
            # Validate and enhance persona data
            persona_data = self._validate_persona_data(persona_data, group_category)
            
            # Check for duplicate names and make unique if needed
            persona_data = self._ensure_unique_name(persona_data, group_category)
            
            logger.info(f"Successfully generated persona: {persona_data.get('name', 'Unknown')}")
            return persona_data
            
        except Exception as e:
            logger.error(f"Error generating presenter persona: {e}")
            # Return a fallback persona
            return self._create_fallback_persona("", group_category)
    
    async def generate_writer_persona(
        self,
        group_id: UUID,
        group_category: str = "General",
        recent_articles: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Generate a writer persona using LLM."""
        try:
            logger.info(f"Generating writer persona for {group_category} group {group_id}")
            
            # Get recent article titles for context
            if not recent_articles:
                db = get_db_session()
                try:
                    group = db.query(PodcastGroup).filter(PodcastGroup.id == group_id).first()
                    if group and group.news_feeds:
                        feed_ids = [feed.id for feed in group.news_feeds]
                        articles = db.query(Article).filter(
                            Article.feed_id.in_(feed_ids)
                        ).order_by(Article.created_at.desc()).limit(10).all()
                        recent_articles = [article.title for article in articles]
                finally:
                    db.close()
            
            # Create prompts
            system_prompt = self._create_writer_system_prompt()
            content_prompt = self._create_writer_content_prompt(group_category, recent_articles or [])
            
            # Use text generation service to create writer persona
            request_data = {
                "group_id": str(group_id),
                "article_summaries": [{"title": title, "summary": "", "link": ""} for title in (recent_articles or [])],
                "target_duration_minutes": 1,  # Not used for writer generation
                "style_preferences": {
                    "task": "writer_generation",
                    "system_prompt": system_prompt,
                    "content_prompt": content_prompt
                }
            }
            
            # Make a custom request to text generation service
            async with httpx.AsyncClient(timeout=180.0) as client:
                response = await client.post(
                    "http://text-generation:8002/generate-script",
                    json=request_data
                )
                response.raise_for_status()
                result = response.json()
            
            # Extract writer persona from the generated script
            script = result.get("script", "")
            
            # Try to parse JSON from the script
            try:
                # Look for JSON in the script
                import re
                json_match = re.search(r'\{.*\}', script, re.DOTALL)
                if json_match:
                    writer_data = json.loads(json_match.group())
                else:
                    # Fallback: create writer from script content
                    writer_data = self._create_fallback_writer(script, group_category)
            except json.JSONDecodeError:
                # Fallback: create writer from script content
                writer_data = self._create_fallback_writer(script, group_category)
            
            # Validate and enhance writer data
            writer_data = self._validate_writer_data(writer_data, group_category)
            
            logger.info(f"Successfully generated writer: {writer_data.get('name', 'Unknown')}")
            return writer_data
            
        except Exception as e:
            logger.error(f"Error generating writer persona: {e}")
            # Return a fallback writer
            return self._create_fallback_writer("", group_category)
    
    def _create_writer_system_prompt(self) -> str:
        """Create system prompt for writer generation."""
        return """
You are an expert at creating engaging podcast writer personas. Generate unique, professional, and skilled writer characters that would be perfect for creating podcast content.

For each writer, create:
1. A distinctive name that fits the character
2. A compelling bio that shows writing expertise and background
3. A detailed writing style description with tone, approach, and specialties
4. Writing characteristics and content creation patterns
5. A system prompt that defines how this writer should behave

Make each writer:
- Unique and professional
- Skilled in content creation
- Knowledgeable in their field
- Suited for podcast script writing
- Distinctive in writing style
- Engaging and informative

Return your response as valid JSON with the following structure:
{
    "name": "Writer Name",
    "bio": "Brief bio describing the writer's background and expertise",
    "style": "Writing style description including tone, approach, and specialties",
    "specialties": ["expertise area 1", "expertise area 2"],
    "system_prompt": "System prompt that defines how this writer should behave when creating content"
}
"""
    
    def _create_writer_content_prompt(self, group_category: str, recent_articles: List[str]) -> str:
        """Create content prompt for writer generation based on group context."""
        articles_context = ""
        if recent_articles:
            articles_context = f"""
Recent article topics to consider for expertise areas:
{chr(10).join([f"- {article[:100]}..." for article in recent_articles[:5]])}
"""
        
        return f"""
Create a unique podcast writer persona for a {group_category} podcast.

{articles_context}

Requirements:
- The writer should be well-suited for {group_category} content
- Make them knowledgeable and skilled in content creation
- Give them a distinctive writing style and approach
- Include specific expertise areas relevant to {group_category}
- Make them professional and engaging
- Ensure they would be good at creating compelling podcast scripts

Generate a complete writer persona that would be perfect for writing {group_category} podcast content.
"""
    
    def _create_fallback_writer(self, script_content: str, category: str) -> Dict[str, Any]:
        """Create a fallback writer when LLM generation fails."""
        category_lower = category.lower()
        
        # Generate unique writer based on category and timestamp
        import time
        timestamp = str(int(time.time()))
        seed = hashlib.md5(f"{category}_{timestamp}".encode()).hexdigest()
        writer_index = int(seed[:2], 16) % 4
        
        writers = [
            {
                "name": f"Jordan {category} Writer",
                "bio": f"Experienced content writer specializing in {category} topics with a passion for creating engaging podcast scripts.",
                "style": f"Professional, informative, and engaging writing style perfect for {category} content.",
                "specialties": [category.lower(), "content creation", "script writing"],
                "system_prompt": f"You are a skilled writer creating {category} podcast content. Focus on clarity, engagement, and accuracy."
            },
            {
                "name": f"Casey {category} Content Creator",
                "bio": f"Creative writer with expertise in {category} and a talent for making complex topics accessible.",
                "style": f"Clear, conversational, and educational writing approach for {category} audiences.",
                "specialties": [category.lower(), "educational content", "podcast scripts"],
                "system_prompt": f"You are a content creator specializing in {category} podcast scripts. Make information accessible and engaging."
            },
            {
                "name": f"Morgan {category} Scriptwriter",
                "bio": f"Professional scriptwriter with deep knowledge of {category} and experience in audio content creation.",
                "style": f"Structured, compelling, and audience-focused writing for {category} podcast content.",
                "specialties": [category.lower(), "script writing", "audio content"],
                "system_prompt": f"You are a professional scriptwriter creating {category} podcast content. Focus on structure and audience engagement."
            },
            {
                "name": f"Taylor {category} Storyteller",
                "bio": f"Storytelling expert who specializes in bringing {category} topics to life through compelling narratives.",
                "style": f"Narrative-driven, engaging, and memorable writing style for {category} content.",
                "specialties": [category.lower(), "storytelling", "narrative content"],
                "system_prompt": f"You are a storyteller creating {category} podcast content. Use narrative techniques to make content memorable."
            }
        ]
        
        return writers[writer_index]
    
    def _validate_writer_data(self, writer_data: Dict[str, Any], category: str) -> Dict[str, Any]:
        """Validate and enhance writer data."""
        # Ensure required fields exist
        if "name" not in writer_data:
            writer_data["name"] = f"{category} Writer"
        
        if "bio" not in writer_data:
            writer_data["bio"] = f"Professional writer specializing in {category} content."
        
        if "style" not in writer_data:
            writer_data["style"] = f"Professional writing style for {category} content."
        
        if "specialties" not in writer_data:
            writer_data["specialties"] = [category.lower(), "content creation"]
        
        if "system_prompt" not in writer_data:
            writer_data["system_prompt"] = f"You are a professional writer creating {category} podcast content."
        
        return writer_data

    def _ensure_unique_name(self, persona_data: Dict[str, Any], category: str) -> Dict[str, Any]:
        """Ensure the persona name is unique by checking existing presenters."""
        try:
            db = get_db_session()
            try:
                base_name = persona_data.get("name", f"AI {category} Presenter")
                existing_names = set()
                
                # Get all existing presenter names
                presenters = db.query(Presenter).all()
                for presenter in presenters:
                    if presenter.name:
                        existing_names.add(presenter.name.lower())
                
                # If name is unique, return as-is
                if base_name.lower() not in existing_names:
                    return persona_data
                
                # Generate unique name by appending numbers
                counter = 1
                while f"{base_name} {counter}".lower() in existing_names:
                    counter += 1
                
                unique_name = f"{base_name} {counter}"
                persona_data["name"] = unique_name
                logger.info(f"Generated unique name: {unique_name}")
                
                return persona_data
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error ensuring unique name: {e}")
            # Fallback: add timestamp to make unique
            import time
            timestamp = int(time.time()) % 10000
            persona_data["name"] = f"{persona_data.get('name', 'AI Presenter')} {timestamp}"
            return persona_data

    def _create_fallback_persona(self, script_content: str, category: str) -> Dict[str, Any]:
        """Create a fallback persona when LLM generation fails."""
        category_lower = category.lower()
        
        # Generate deterministic persona based on category
        seed = hashlib.md5(category.encode()).hexdigest()
        persona_index = int(seed[:2], 16) % 4
        
        personas = [
            {
                "name": f"Alex {category} Expert",
                "bio": f"Experienced {category_lower} analyst with a passion for breaking down complex topics into digestible insights.",
                "persona": f"Professional yet approachable, Alex brings years of {category_lower} expertise to every discussion. Known for clear explanations and thoughtful analysis.",
                "voice_style": "Clear, confident, and engaging with a professional tone that's accessible to all audiences.",
                "system_prompt": f"You are Alex, a knowledgeable {category_lower} expert. Provide clear, insightful analysis while maintaining an engaging and approachable tone."
            },
            {
                "name": f"Sam {category} Insider",
                "bio": f"Industry insider with deep connections in {category_lower}, offering unique perspectives on current events.",
                "persona": f"Sam has insider knowledge and isn't afraid to share candid insights about {category_lower} developments. Direct and honest in approach.",
                "voice_style": "Direct, conversational, and slightly informal with occasional industry jargon explained for clarity.",
                "system_prompt": f"You are Sam, a {category_lower} insider with deep industry knowledge. Share insights candidly while explaining complex concepts clearly."
            },
            {
                "name": f"Jordan {category} Explorer",
                "bio": f"Curious explorer of {category_lower} trends, always asking the right questions to uncover deeper stories.",
                "persona": f"Jordan approaches {category_lower} with curiosity and skepticism, always digging deeper to understand the full picture.",
                "voice_style": "Inquisitive, thoughtful, and analytical with a tendency to ask probing questions and explore multiple angles.",
                "system_prompt": f"You are Jordan, a curious {category_lower} explorer. Ask thoughtful questions and explore multiple perspectives on each topic."
            },
            {
                "name": f"Casey {category} Storyteller",
                "bio": f"Master storyteller who brings {category_lower} news to life through compelling narratives and real-world connections.",
                "persona": f"Casey excels at connecting {category_lower} developments to broader themes and human stories, making complex topics relatable.",
                "voice_style": "Narrative-driven, engaging, and emotionally intelligent with a talent for making abstract concepts concrete.",
                "system_prompt": f"You are Casey, a {category_lower} storyteller. Connect news to broader themes and human stories to make content engaging and relatable."
            }
        ]
        
        return personas[persona_index]
    
    def _validate_persona_data(self, persona_data: Dict[str, Any], category: str) -> Dict[str, Any]:
        """Validate and enhance persona data."""
        required_fields = ["name", "bio", "persona", "voice_style", "system_prompt"]
        
        for field in required_fields:
            if field not in persona_data or not persona_data[field]:
                if field == "name":
                    persona_data[field] = f"AI {category} Presenter"
                elif field == "bio":
                    persona_data[field] = f"AI-generated presenter specializing in {category.lower()} content"
                elif field == "persona":
                    persona_data[field] = f"Professional {category.lower()} presenter with engaging personality"
                elif field == "voice_style":
                    persona_data[field] = "Clear, professional, and engaging voice suitable for podcast hosting"
                elif field == "system_prompt":
                    persona_data[field] = f"You are a knowledgeable {category.lower()} presenter. Provide clear, engaging commentary on the topics discussed."
        
        return persona_data


class EpisodeGenerationService:
    """Orchestrates the complete episode generation process."""
    
    def __init__(self):
        self.news_feed_service = NewsFeedService()
        self.collections_service = CollectionsService()
        self.text_generation_service = TextGenerationService()
        self.writer_service = WriterService()
        self.editor_service = EditorService()
        self.presenter_service = PresenterService()
        self.tts_service = TTSService()
        self.publishing_service = PublishingService()
        self.persona_generation_service = PersonaGenerationService()
        self.cadence_manager = CadenceManager()
        # Feature flag: allow switching script generation source
        self.use_writer_for_script = str(os.getenv("USE_WRITER_FOR_SCRIPT", "true")).lower() in ("1", "true", "yes")
        # Redis for production lock
        self.redis = redis.Redis.from_url(REDIS_URL, decode_responses=True)
    
    def _set_production_active(self, group_id: UUID, episode_id: UUID):
        """Set production lock to pause reviewer service during podcast production."""
        lock_key = "podcast:production:active"
        lock_value = json.dumps({
            "group_id": str(group_id),
            "episode_id": str(episode_id),
            "started_at": datetime.utcnow().isoformat()
        })
        # Set lock with 2 hour TTL as safety measure
        self.redis.set(lock_key, lock_value, ex=2 * 3600)
        logger.info(f"🔒 Production lock activated - Reviewer Service paused for group {group_id}")
    
    def _clear_production_lock(self):
        """Clear production lock to resume reviewer service."""
        lock_key = "podcast:production:active"
        self.redis.delete(lock_key)
        logger.info("🔓 Production lock cleared - Reviewer Service resumed")
    
    async def generate_complete_episode(self, group_id: UUID, collection_id: Optional[str] = None) -> Dict[str, Any]:
        """Generate a complete episode from start to finish."""
        db = get_db_session()
        episode_id_for_lock = None
        
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
            
            # Step 2: Get active collection and create snapshot
            snapshot_collection_id = None
            articles: List[Dict[str, Any]] = []
            
            if collection_id:
                logger.info(f"Using manually selected collection {collection_id}")
                # User provided a specific collection
                active_collection_id = collection_id
            else:
                logger.info(f"Getting active collection for group {group_id}")
                # Get the active building collection for this group
                active_collection = await self.collections_service.get_active_collection_for_group(group_id)
                if not active_collection:
                    self.cadence_manager.release_group_lock(group_id)
                    raise ValueError(f"No active collection found for group {group_id}")
                active_collection_id = active_collection.get("collection_id")
                logger.info(f"Found active collection: {active_collection_id}")
            
            # Step 3: Create a temporary episode to get an ID for the snapshot
            logger.info("Creating episode record for snapshot")
            episode = Episode(
                group_id=group_id,
                script="",  # Will be filled later
                status=EpisodeStatus.DRAFT
            )
            db.add(episode)
            db.commit()
            db.refresh(episode)
            
            # PAUSE REVIEWER SERVICE during podcast production
            episode_id_for_lock = episode.id
            self._set_production_active(group_id, episode.id)
            
            # Step 4: Create snapshot of the collection
            logger.info(f"Creating snapshot of collection {active_collection_id} for episode {episode.id}")
            snapshot_collection_id = await self.collections_service.create_snapshot(
                active_collection_id,
                str(episode.id)
            )
            
            if not snapshot_collection_id:
                logger.warning("Failed to create snapshot, using original collection")
                snapshot_collection_id = active_collection_id
            else:
                logger.info(f"✅ Created snapshot collection: {snapshot_collection_id}")
                logger.info(f"✅ New building collection automatically created for future articles")
            
            # Step 5: Gather articles from the snapshot collection
            logger.info(f"Using snapshot collection {snapshot_collection_id} for content")
            collection = await self.collections_service.get_collection(snapshot_collection_id)
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
            
            # If snapshot had no articles, fall back to database articles for this episode
            if not articles:
                logger.info("Snapshot has no items in memory, fetching from database")
                # Get articles directly from database for this collection
                from uuid import UUID as UUIDType
                db_articles = db.query(Article).filter(
                    Article.collection_id == UUIDType(snapshot_collection_id)
                ).all()
                
                for article in db_articles:
                    articles.append({
                        "title": article.title,
                        "summary": article.summary,
                        "link": article.link,
                        "publish_date": article.publish_date.isoformat() if article.publish_date else None
                    })
            
            # Final fallback to recent articles
            if not articles:
                logger.warning("No articles in snapshot, falling back to recent articles")
                articles = await self.news_feed_service.get_recent_articles(group_id)
            
            # Validate minimum article count
            MIN_FEEDS_REQUIRED = int(os.getenv("MIN_FEEDS_PER_COLLECTION", "3"))
            if not articles:
                raise ValueError("No article content available to generate episode")
            
            if len(articles) < MIN_FEEDS_REQUIRED:
                error_msg = f"Insufficient articles: {len(articles)}/{MIN_FEEDS_REQUIRED} required"
                logger.warning(f"Collection validation failed for group {group_id}: {error_msg}")
                raise ValueError(error_msg)
            
            # Step 3: Generate presenter briefs for the collection
            logger.info("Generating presenter briefs for collection")
            presenter_briefs = []
            try:
                for presenter in group.presenters:
                    logger.info(f"Requesting brief from presenter {presenter.name}")
                    brief_result = await self.presenter_service.generate_brief(
                        presenter_id=presenter.id,
                        collection_id=collection_id or str(group_id),
                        articles=articles
                    )
                    presenter_briefs.append({
                        "presenter_id": str(presenter.id),
                        "presenter_name": presenter.name,
                        "brief": brief_result.get("brief", ""),
                        "metadata": brief_result.get("brief_metadata", {})
                    })
                    logger.info(f"✅ Received brief from {presenter.name}")
            except Exception as e:
                logger.warning(f"Failed to generate presenter briefs: {e}")
                # Continue without briefs if generation fails
            
            # Step 4: Generate script (Writer by default; can toggle to TextGeneration)
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
            
            # Episode record already created earlier for snapshot
            # Update it with the generated script
            logger.info("Updating episode with generated script")
            episode.script = script
            db.commit()
            
            # Step 5: Generate presenter feedback on the script
            logger.info("Generating presenter feedback on script")
            presenter_feedback = []
            try:
                collection_context = {
                    "group_name": group.name,
                    "category": group.category or "General",
                    "article_count": len(articles),
                    "target_audience": "general",
                    "presenter_briefs": presenter_briefs
                }
                
                for presenter in group.presenters:
                    logger.info(f"Requesting feedback from presenter {presenter.name}")
                    feedback_result = await self.presenter_service.generate_feedback(
                        presenter_id=presenter.id,
                        script_id=str(episode.id),
                        script=script,
                        collection_context=collection_context
                    )
                    presenter_feedback.append({
                        "presenter_id": str(presenter.id),
                        "presenter_name": presenter.name,
                        "feedback": feedback_result.get("feedback", ""),
                        "metadata": feedback_result.get("feedback_metadata", {})
                    })
                    logger.info(f"✅ Received feedback from {presenter.name}")
            except Exception as e:
                logger.warning(f"Failed to generate presenter feedback: {e}")
                # Continue without feedback if generation fails
            
            # Step 6: Edit script using Editor service
            logger.info("Editing and polishing script")
            try:
                collection_context["presenter_feedback"] = presenter_feedback
                
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
            
            # Step 7: Generate metadata
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
            
            # Step 8: Generate audio (TEMPORARY: using Presenter until new hardware arrives)
            logger.info("Generating audio")
            presenter_ids = [p.id for p in group.presenters]
            audio_result = await self.presenter_service.generate_audio(
                episode.id, script, presenter_ids
            )
            
            # Step 8.1: Create AudioFile record
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
            
            # Step 9: Publish episode to local platforms
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
            
            # Release locks after successful completion
            self._clear_production_lock()
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
            # Release locks on error
            self._clear_production_lock()
            self.cadence_manager.release_group_lock(group_id)
            raise
        finally:
            db.close()
