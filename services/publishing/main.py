"""
Publishing Service - Handles publishing episodes to podcast hosting platforms.
"""
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from uuid import UUID

import httpx
import boto3
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel

from shared.database import get_db, create_tables
from shared.models import Episode, EpisodeMetadata, AudioFile, PublishRecord
from shared.schemas import PublishRecordCreate, PublishRecord as PublishRecordSchema

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Publishing Service", version="1.0.0")

# Configuration
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_S3_BUCKET = os.getenv("AWS_S3_BUCKET", "podcast-ai-storage")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# Platform configurations
PLATFORM_CONFIGS = {
    "anchor": {
        "api_url": "https://api.anchor.fm/api",
        "required_fields": ["title", "description", "audio_url", "category"]
    },
    "libsyn": {
        "api_url": "https://api.libsyn.com",
        "required_fields": ["title", "description", "audio_url", "category"]
    },
    "buzzsprout": {
        "api_url": "https://www.buzzsprout.com/api",
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


class S3Uploader:
    """Handles uploading audio files to S3."""
    
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION
        )
        self.bucket = AWS_S3_BUCKET
    
    async def upload_audio_file(
        self,
        local_file_path: str,
        episode_id: UUID,
        file_extension: str = "wav"
    ) -> str:
        """Upload audio file to S3 and return public URL."""
        try:
            s3_key = f"episodes/{episode_id}/audio.{file_extension}"
            
            # Upload file
            self.s3_client.upload_file(
                local_file_path,
                self.bucket,
                s3_key,
                ExtraArgs={
                    'ContentType': 'audio/wav' if file_extension == 'wav' else 'audio/mpeg',
                    'ACL': 'public-read'
                }
            )
            
            # Generate public URL
            public_url = f"https://{self.bucket}.s3.{AWS_REGION}.amazonaws.com/{s3_key}"
            
            logger.info(f"Uploaded audio file to S3: {public_url}")
            return public_url
            
        except Exception as e:
            logger.error(f"Error uploading to S3: {e}")
            raise HTTPException(status_code=500, detail=f"S3 upload failed: {str(e)}")


class PlatformPublisher:
    """Handles publishing to different podcast platforms."""
    
    def __init__(self):
        self.s3_uploader = S3Uploader()
    
    async def publish_to_anchor(
        self,
        episode_data: Dict[str, Any],
        credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        """Publish episode to Anchor platform."""
        try:
            # This is a placeholder implementation
            # In reality, you would use Anchor's actual API
            
            logger.info("Publishing to Anchor (placeholder implementation)")
            
            # Simulate API call
            await asyncio.sleep(2)  # Simulate network delay
            
            # Return mock response
            return {
                "platform": "anchor",
                "external_id": f"anchor_{episode_data['episode_id']}",
                "public_url": f"https://anchor.fm/episode/{episode_data['episode_id']}",
                "status": "published"
            }
            
        except Exception as e:
            logger.error(f"Error publishing to Anchor: {e}")
            return {
                "platform": "anchor",
                "status": "failed",
                "error": str(e)
            }
    
    async def publish_to_libsyn(
        self,
        episode_data: Dict[str, Any],
        credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        """Publish episode to Libsyn platform."""
        try:
            # This is a placeholder implementation
            # In reality, you would use Libsyn's actual API
            
            logger.info("Publishing to Libsyn (placeholder implementation)")
            
            # Simulate API call
            await asyncio.sleep(2)  # Simulate network delay
            
            # Return mock response
            return {
                "platform": "libsyn",
                "external_id": f"libsyn_{episode_data['episode_id']}",
                "public_url": f"https://libsyn.com/episode/{episode_data['episode_id']}",
                "status": "published"
            }
            
        except Exception as e:
            logger.error(f"Error publishing to Libsyn: {e}")
            return {
                "platform": "libsyn",
                "status": "failed",
                "error": str(e)
            }
    
    async def publish_to_buzzsprout(
        self,
        episode_data: Dict[str, Any],
        credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        """Publish episode to Buzzsprout platform."""
        try:
            # This is a placeholder implementation
            # In reality, you would use Buzzsprout's actual API
            
            logger.info("Publishing to Buzzsprout (placeholder implementation)")
            
            # Simulate API call
            await asyncio.sleep(2)  # Simulate network delay
            
            # Return mock response
            return {
                "platform": "buzzsprout",
                "external_id": f"buzzsprout_{episode_data['episode_id']}",
                "public_url": f"https://buzzsprout.com/episode/{episode_data['episode_id']}",
                "status": "published"
            }
            
        except Exception as e:
            logger.error(f"Error publishing to Buzzsprout: {e}")
            return {
                "platform": "buzzsprout",
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
            "anchor": self.publish_to_anchor,
            "libsyn": self.publish_to_libsyn,
            "buzzsprout": self.publish_to_buzzsprout
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
        
        # Upload audio file to S3 if not already uploaded
        if not audio_file.url.startswith("http"):
            # Local file, need to upload to S3
            public_audio_url = await self.platform_publisher.s3_uploader.upload_audio_file(
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
            platforms=["anchor", "libsyn"],
            platform_credentials={
                "anchor": {"api_key": "test_key"},
                "libsyn": {"api_key": "test_key"}
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
