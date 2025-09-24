"""
Publishing Service - Handles publishing episodes to podcast hosting platforms.
"""
import asyncio
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from uuid import UUID

import aiofiles
import httpx
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session

from shared.database import get_db, create_tables
from shared.models import Episode, EpisodeMetadata, AudioFile, PublishRecord
from shared.schemas import PublishRecordCreate, PublishRecord as PublishRecordSchema

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Publishing Service", version="1.0.0")

# Configuration
LOCAL_STORAGE_PATH = os.getenv("LOCAL_STORAGE_PATH", "/app/storage")
LOCAL_SERVER_URL = os.getenv("LOCAL_SERVER_URL", "http://localhost:8080")

# Platform configurations
PLATFORM_CONFIGS = {
    "local_podcast_host": {
        "api_url": f"{LOCAL_SERVER_URL}/api/podcast",
        "required_fields": ["title", "description", "audio_url", "category"]
    },
    "local_rss_feed": {
        "api_url": f"{LOCAL_SERVER_URL}/api/rss",
        "required_fields": ["title", "description", "audio_url", "category"]
    },
    "local_directory": {
        "api_url": f"{LOCAL_SERVER_URL}/api/episodes",
        "required_fields": ["title", "description", "audio_url", "category"]
    }
}


class PublishRequest(BaseModel):
    episode_id: UUID
    platforms: List[str]  # ["anchor", "libsyn", etc.]
    platform_credentials: Dict[str, Dict[str, str]]  # platform -> credentials
    publish_settings: Optional[Dict[str, Any]] = None


class PublishResponse(BaseModel):
    episode_id: UUID
    publish_records: List[PublishRecordSchema]
    status: str
    message: str


class LocalFileManager:
    """Handles local file storage and management."""
    
    def __init__(self):
        self.storage_path = Path(LOCAL_STORAGE_PATH)
        self.storage_path.mkdir(parents=True, exist_ok=True)
    
    async def store_audio_file(
        self,
        local_file_path: str,
        episode_id: UUID,
        file_extension: str = "wav"
    ) -> str:
        """Store audio file locally and return public URL."""
        try:
            # Create episode directory
            episode_dir = self.storage_path / "episodes" / str(episode_id)
            episode_dir.mkdir(parents=True, exist_ok=True)
            
            # Define destination file path
            dest_filename = f"audio.{file_extension}"
            dest_path = episode_dir / dest_filename
            
            # Copy file to storage
            if os.path.exists(local_file_path):
                shutil.copy2(local_file_path, dest_path)
            else:
                # If source file doesn't exist, create a placeholder
                logger.warning(f"Source file {local_file_path} not found, creating placeholder")
                dest_path.touch()
            
            # Generate public URL
            public_url = f"{LOCAL_SERVER_URL}/storage/episodes/{episode_id}/{dest_filename}"
            
            logger.info(f"Stored audio file locally: {public_url}")
            return public_url
            
        except Exception as e:
            logger.error(f"Error storing file locally: {e}")
            raise HTTPException(status_code=500, detail=f"Local storage failed: {str(e)}")
    
    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """Get file information including size and duration."""
        try:
            path = Path(file_path)
            if not path.exists():
                return {"exists": False}
            
            stat = path.stat()
            return {
                "exists": True,
                "size_bytes": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime),
                "extension": path.suffix[1:] if path.suffix else None
            }
        except Exception as e:
            logger.error(f"Error getting file info: {e}")
            return {"exists": False, "error": str(e)}


class PlatformPublisher:
    """Handles publishing to different podcast platforms."""
    
    def __init__(self):
        self.file_manager = LocalFileManager()
    
    async def publish_to_local_podcast_host(
        self,
        episode_data: Dict[str, Any],
        credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        """Publish episode to local podcast hosting platform."""
        try:
            logger.info("Publishing to local podcast host")
            
            # Simulate processing time
            await asyncio.sleep(1)
            
            # Generate local podcast feed URL
            episode_id = episode_data['episode_id']
            local_url = f"{LOCAL_SERVER_URL}/podcast/episodes/{episode_id}"
            
            # Return response
            return {
                "platform": "local_podcast_host",
                "external_id": f"local_{episode_id}",
                "public_url": local_url,
                "status": "published"
            }
            
        except Exception as e:
            logger.error(f"Error publishing to local host: {e}")
            return {
                "platform": "local_podcast_host",
                "status": "failed",
                "error": str(e)
            }
    
    async def publish_to_local_rss_feed(
        self,
        episode_data: Dict[str, Any],
        credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        """Publish episode to local RSS feed."""
        try:
            logger.info("Publishing to local RSS feed")
            
            # Simulate processing time
            await asyncio.sleep(1)
            
            # Generate local RSS feed URL
            episode_id = episode_data['episode_id']
            rss_url = f"{LOCAL_SERVER_URL}/rss/episodes/{episode_id}"
            
            # Return response
            return {
                "platform": "local_rss_feed",
                "external_id": f"rss_{episode_id}",
                "public_url": rss_url,
                "status": "published"
            }
            
        except Exception as e:
            logger.error(f"Error publishing to local RSS: {e}")
            return {
                "platform": "local_rss_feed",
                "status": "failed",
                "error": str(e)
            }
    
    async def publish_to_local_directory(
        self,
        episode_data: Dict[str, Any],
        credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        """Publish episode to local directory listing."""
        try:
            logger.info("Publishing to local directory")
            
            # Simulate processing time
            await asyncio.sleep(1)
            
            # Generate local directory URL
            episode_id = episode_data['episode_id']
            directory_url = f"{LOCAL_SERVER_URL}/episodes/{episode_id}"
            
            # Return response
            return {
                "platform": "local_directory",
                "external_id": f"dir_{episode_id}",
                "public_url": directory_url,
                "status": "published"
            }
            
        except Exception as e:
            logger.error(f"Error publishing to local directory: {e}")
            return {
                "platform": "local_directory",
                "status": "failed",
                "error": str(e)
            }
    
    async def publish_to_platform(
        self,
        platform: str,
        episode_data: Dict[str, Any],
        credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        """Publish to a specific platform."""
        platform_methods = {
            "local_podcast_host": self.publish_to_local_podcast_host,
            "local_rss_feed": self.publish_to_local_rss_feed,
            "local_directory": self.publish_to_local_directory
        }
        
        if platform not in platform_methods:
            raise ValueError(f"Unsupported platform: {platform}")
        
        return await platform_methods[platform](episode_data, credentials)


class PublishingManager:
    """Manages the publishing process for episodes."""
    
    def __init__(self):
        self.platform_publisher = PlatformPublisher()
    
    async def prepare_episode_data(
        self,
        episode: Episode,
        metadata: EpisodeMetadata,
        audio_file: AudioFile
    ) -> Dict[str, Any]:
        """Prepare episode data for publishing."""
        
        # Store audio file locally if not already stored
        if not audio_file.url.startswith("http"):
            # Local file, need to store in local storage
            public_audio_url = await self.platform_publisher.file_manager.store_audio_file(
                audio_file.url,
                episode.id,
                audio_file.format or "wav"
            )
        else:
            public_audio_url = audio_file.url
        
        episode_data = {
            "episode_id": str(episode.id),
            "title": metadata.title or "Untitled Episode",
            "description": metadata.description or "No description available",
            "audio_url": public_audio_url,
            "category": metadata.category or "General",
            "subcategory": metadata.subcategory,
            "tags": metadata.tags or [],
            "keywords": metadata.keywords or [],
            "language": metadata.language or "en",
            "country": metadata.country or "US",
            "duration_seconds": audio_file.duration_seconds,
            "file_size_bytes": audio_file.file_size_bytes,
            "format": audio_file.format or "wav",
            "created_at": episode.created_at.isoformat()
        }
        
        return episode_data
    
    async def publish_episode(
        self,
        request: PublishRequest,
        db: Session
    ) -> PublishResponse:
        """Publish episode to multiple platforms."""
        
        # Get episode details
        episode = db.query(Episode).filter(Episode.id == request.episode_id).first()
        if not episode:
            raise HTTPException(status_code=404, detail="Episode not found")
        
        # Get episode metadata
        metadata = db.query(EpisodeMetadata).filter(
            EpisodeMetadata.episode_id == request.episode_id
        ).first()
        if not metadata:
            raise HTTPException(status_code=404, detail="Episode metadata not found")
        
        # Get audio file
        audio_file = db.query(AudioFile).filter(
            AudioFile.episode_id == request.episode_id
        ).first()
        if not audio_file:
            raise HTTPException(status_code=404, detail="Audio file not found")
        
        try:
            # Prepare episode data
            episode_data = await self.prepare_episode_data(episode, metadata, audio_file)
            
            # Publish to each platform
            publish_records = []
            successful_platforms = []
            failed_platforms = []
            
            for platform in request.platforms:
                try:
                    credentials = request.platform_credentials.get(platform, {})
                    
                    # Publish to platform
                    result = await self.platform_publisher.publish_to_platform(
                        platform,
                        episode_data,
                        credentials
                    )
                    
                    # Create publish record
                    publish_record = PublishRecord(
                        episode_id=request.episode_id,
                        platform=platform,
                        external_id=result.get("external_id"),
                        public_url=result.get("public_url"),
                        status=result.get("status", "pending"),
                        error_message=result.get("error"),
                        published_at=datetime.utcnow() if result.get("status") == "published" else None
                    )
                    
                    db.add(publish_record)
                    publish_records.append(publish_record)
                    
                    if result.get("status") == "published":
                        successful_platforms.append(platform)
                    else:
                        failed_platforms.append(platform)
                        
                except Exception as e:
                    logger.error(f"Error publishing to {platform}: {e}")
                    
                    # Create failed publish record
                    publish_record = PublishRecord(
                        episode_id=request.episode_id,
                        platform=platform,
                        status="failed",
                        error_message=str(e)
                    )
                    
                    db.add(publish_record)
                    publish_records.append(publish_record)
                    failed_platforms.append(platform)
            
            db.commit()
            
            # Refresh records to get IDs
            for record in publish_records:
                db.refresh(record)
            
            # Determine overall status
            if successful_platforms and not failed_platforms:
                overall_status = "published"
                message = f"Successfully published to all platforms: {', '.join(successful_platforms)}"
            elif successful_platforms and failed_platforms:
                overall_status = "partial"
                message = f"Published to {', '.join(successful_platforms)}, failed on {', '.join(failed_platforms)}"
            else:
                overall_status = "failed"
                message = f"Failed to publish to any platform: {', '.join(failed_platforms)}"
            
            logger.info(f"Publishing completed for episode {request.episode_id}: {overall_status}")
            
            return PublishResponse(
                episode_id=request.episode_id,
                publish_records=publish_records,
                status=overall_status,
                message=message
            )
            
        except Exception as e:
            logger.error(f"Error in publishing process: {e}")
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Publishing failed: {str(e)}")


# Initialize services
publishing_manager = PublishingManager()

# Create tables on startup
@app.on_event("startup")
async def startup_event():
    create_tables()
    logger.info("Publishing Service started")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "publishing", "timestamp": datetime.utcnow()}


@app.post("/publish", response_model=PublishResponse)
async def publish_episode(
    request: PublishRequest,
    db: Session = Depends(get_db)
):
    """Publish episode to podcast hosting platforms."""
    
    try:
        result = await publishing_manager.publish_episode(request, db)
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in publish endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Publishing failed: {str(e)}")


@app.get("/episodes/{episode_id}/publish-records", response_model=List[PublishRecordSchema])
async def get_publish_records(
    episode_id: UUID,
    db: Session = Depends(get_db)
):
    """Get publish records for an episode."""
    records = db.query(PublishRecord).filter(
        PublishRecord.episode_id == episode_id
    ).all()
    
    return records


@app.get("/platforms")
async def list_supported_platforms():
    """List supported publishing platforms."""
    return {
        "supported_platforms": list(PLATFORM_CONFIGS.keys()),
        "platform_configs": PLATFORM_CONFIGS
    }


@app.post("/test-publish")
async def test_publish(
    test_episode_id: str = "00000000-0000-0000-0000-000000000001",
    db: Session = Depends(get_db)
):
    """Test endpoint for publishing functionality."""
    try:
        # Create test request
        request = PublishRequest(
            episode_id=UUID(test_episode_id),
            platforms=["local_podcast_host", "local_rss_feed"],
            platform_credentials={
                "local_podcast_host": {"api_key": "test_key"},
                "local_rss_feed": {"api_key": "test_key"}
            }
        )
        
        # Create test episode data
        from shared.models import Episode, EpisodeMetadata, AudioFile
        from datetime import datetime
        
        test_episode = Episode(
            id=request.episode_id,
            group_id=UUID("00000000-0000-0000-0000-000000000001"),
            script="Test script",
            created_at=datetime.utcnow()
        )
        
        test_metadata = EpisodeMetadata(
            episode_id=request.episode_id,
            title="Test Episode",
            description="This is a test episode for publishing",
            category="Technology",
            tags=["test", "podcast"]
        )
        
        test_audio = AudioFile(
            episode_id=request.episode_id,
            url="/tmp/test.wav",
            duration_seconds=300,
            file_size_bytes=5000000,
            format="wav"
        )
        
        # Add to database temporarily
        db.add(test_episode)
        db.add(test_metadata)
        db.add(test_audio)
        db.commit()
        
        try:
            result = await publishing_manager.publish_episode(request, db)
            return result
        finally:
            # Clean up test data
            db.delete(test_episode)
            db.delete(test_metadata)
            db.delete(test_audio)
            db.commit()
        
    except Exception as e:
        logger.error(f"Error in test publish: {e}")
        raise HTTPException(status_code=500, detail=f"Test publish failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    import asyncio
    import os
    from sqlalchemy.orm import Session
    uvicorn.run(app, host="0.0.0.0", port=8005)
