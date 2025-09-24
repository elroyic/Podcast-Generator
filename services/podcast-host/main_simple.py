"""
Simplified Podcast Host Service for local testing.
This version serves mock podcast content without external storage.
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Local Podcast Host (Simple)", version="1.0.0")

# Configuration
LOCAL_STORAGE_PATH = os.getenv("LOCAL_STORAGE_PATH", "/tmp/podcast_storage")
LOCAL_SERVER_URL = os.getenv("LOCAL_SERVER_URL", "http://localhost:8080")

# Mock episode data
mock_episodes = []


class EpisodeResponse(BaseModel):
    id: str
    title: str
    description: str
    audio_url: str
    published_at: datetime
    duration_seconds: int
    file_size_bytes: int


def create_mock_episode(episode_id: str = None) -> EpisodeResponse:
    """Create a mock episode."""
    
    episode_id = episode_id or str(uuid4())
    
    return EpisodeResponse(
        id=episode_id,
        title="Mock Podcast Episode",
        description="This is a mock podcast episode generated for testing purposes.",
        audio_url=f"{LOCAL_SERVER_URL}/episodes/{episode_id}/audio",
        published_at=datetime.utcnow(),
        duration_seconds=1800,  # 30 minutes
        file_size_bytes=1024000  # 1MB
    )


@app.on_event("startup")
async def startup_event():
    """Initialize the service."""
    # Ensure storage directories exist
    storage_path = Path(LOCAL_STORAGE_PATH)
    storage_path.mkdir(parents=True, exist_ok=True)
    (storage_path / "episodes").mkdir(exist_ok=True)
    (storage_path / "rss").mkdir(exist_ok=True)
    (storage_path / "podcast").mkdir(exist_ok=True)
    
    # Create some mock episodes
    for i in range(3):
        episode = create_mock_episode()
        mock_episodes.append(episode)
    
    logger.info("Local Podcast Host (Simple) started")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "podcast-host-simple", "timestamp": datetime.utcnow()}


@app.get("/episodes", response_model=List[EpisodeResponse])
async def list_episodes():
    """List all episodes."""
    return mock_episodes


@app.get("/episodes/{episode_id}", response_model=EpisodeResponse)
async def get_episode(episode_id: str):
    """Get a specific episode."""
    
    for episode in mock_episodes:
        if episode.id == episode_id:
            return episode
    
    # Create a new mock episode if not found
    episode = create_mock_episode(episode_id)
    mock_episodes.append(episode)
    return episode


@app.get("/episodes/{episode_id}/audio")
async def get_episode_audio(episode_id: str):
    """Get episode audio file."""
    
    # Return mock audio content
    mock_audio_content = f"""
Mock Audio Content for Episode {episode_id}
Generated at: {datetime.utcnow()}

This is a placeholder for the actual audio content.
In a real implementation, this would be an MP3 or WAV file.
The audio would contain the podcast episode content.
"""
    
    return PlainTextResponse(
        content=mock_audio_content,
        media_type="text/plain",
        headers={"Content-Disposition": f"attachment; filename=episode_{episode_id}_audio.txt"}
    )


@app.get("/rss")
async def get_rss_feed():
    """Get RSS feed."""
    
    rss_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
    <channel>
        <title>Mock Podcast RSS Feed</title>
        <description>Mock podcast RSS feed for testing</description>
        <link>{LOCAL_SERVER_URL}</link>
        <language>en-us</language>
        <lastBuildDate>{datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')}</lastBuildDate>
        
        {''.join([f'''
        <item>
            <title>{episode.title}</title>
            <description>{episode.description}</description>
            <link>{LOCAL_SERVER_URL}/episodes/{episode.id}</link>
            <enclosure url="{episode.audio_url}" length="{episode.file_size_bytes}" type="audio/mpeg"/>
            <pubDate>{episode.published_at.strftime('%a, %d %b %Y %H:%M:%S GMT')}</pubDate>
            <guid>{episode.id}</guid>
        </item>
        ''' for episode in mock_episodes])}
    </channel>
</rss>"""
    
    return PlainTextResponse(content=rss_content, media_type="application/rss+xml")


@app.get("/podcast")
async def get_podcast_directory():
    """Get podcast directory page."""
    
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Mock Podcast Directory</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        .episode {{ border: 1px solid #ccc; padding: 20px; margin: 20px 0; }}
        .episode h3 {{ margin-top: 0; }}
    </style>
</head>
<body>
    <h1>Mock Podcast Directory</h1>
    <p>Welcome to the mock podcast directory. This is for testing purposes.</p>
    
    <h2>Episodes</h2>
    {''.join([f'''
    <div class="episode">
        <h3>{episode.title}</h3>
        <p>{episode.description}</p>
        <p><strong>Duration:</strong> {episode.duration_seconds // 60} minutes</p>
        <p><strong>Published:</strong> {episode.published_at.strftime('%Y-%m-%d %H:%M')}</p>
        <p><a href="{episode.audio_url}" download>Download Audio</a></p>
    </div>
    ''' for episode in mock_episodes])}
    
    <h2>RSS Feed</h2>
    <p><a href="/rss">Subscribe to RSS Feed</a></p>
</body>
</html>"""
    
    return PlainTextResponse(content=html_content, media_type="text/html")


@app.post("/api/podcast/episodes")
async def create_episode(episode_data: Dict[str, Any]):
    """Create a new episode (mock implementation)."""
    
    episode_id = str(uuid4())
    episode = create_mock_episode(episode_id)
    mock_episodes.append(episode)
    
    return JSONResponse(content={
        "message": "Episode created successfully",
        "episode_id": episode_id,
        "episode": episode.dict()
    })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8006)
