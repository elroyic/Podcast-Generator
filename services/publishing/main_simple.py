"""
Simplified Publishing Service for local testing.
This version creates mock publishing records without external platforms.
"""

import logging
import os
from datetime import datetime
from typing import Dict, Any, Optional, List
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Publishing Service (Simple)", version="1.0.0")

# Configuration
LOCAL_STORAGE_PATH = os.getenv("LOCAL_STORAGE_PATH", "/tmp/podcast_storage")
LOCAL_SERVER_URL = os.getenv("LOCAL_SERVER_URL", "http://localhost:8080")


class PublishRequest(BaseModel):
    episode_id: UUID
    platforms: List[str]
    platform_credentials: Dict[str, Dict[str, str]]


class PublishResponse(BaseModel):
    episode_id: UUID
    publish_records: List[Dict[str, Any]]
    status: str
    message: str


def create_mock_publish_record(episode_id: UUID, platform: str) -> Dict[str, Any]:
    """Create a mock publishing record."""
    
    return {
        "id": str(uuid4()),
        "episode_id": str(episode_id),
        "platform": platform,
        "external_id": f"mock_{platform}_{episode_id}",
        "public_url": f"{LOCAL_SERVER_URL}/episodes/{episode_id}",
        "status": "published",
        "error_message": None,
        "published_at": datetime.utcnow().isoformat(),
        "created_at": datetime.utcnow().isoformat()
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "publishing-simple", "timestamp": datetime.utcnow()}


@app.post("/publish", response_model=PublishResponse)
async def publish_episode(request: PublishRequest):
    """Publish episode to platforms."""
    
    logger.info(f"Publishing episode {request.episode_id} to platforms: {request.platforms}")
    
    try:
        publish_records = []
        
        for platform in request.platforms:
            # Create mock publish record for each platform
            record = create_mock_publish_record(request.episode_id, platform)
            publish_records.append(record)
            
            logger.info(f"Mock published to {platform}: {record['public_url']}")
        
        return PublishResponse(
            episode_id=request.episode_id,
            publish_records=publish_records,
            status="published",
            message=f"Successfully published to {len(request.platforms)} platforms"
        )
        
    except Exception as e:
        logger.error(f"Error publishing episode: {e}")
        raise HTTPException(status_code=500, detail=f"Publishing failed: {str(e)}")


@app.post("/test-publish")
async def test_publish():
    """Test endpoint for publishing."""
    
    mock_episode_id = UUID("12345678-1234-1234-1234-123456789012")
    mock_platforms = ["local_podcast_host", "local_rss_feed"]
    
    publish_records = []
    for platform in mock_platforms:
        record = create_mock_publish_record(mock_episode_id, platform)
        publish_records.append(record)
    
    return {
        "episode_id": str(mock_episode_id),
        "publish_records": publish_records,
        "status": "published",
        "message": "Test publishing successful",
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)