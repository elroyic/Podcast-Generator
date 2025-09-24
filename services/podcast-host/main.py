"""
Local Podcast Hosting Service - Serves podcast content locally.
"""
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
from uuid import UUID

from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel

from shared.database import get_db, create_tables
from shared.models import Episode, EpisodeMetadata, AudioFile, PublishRecord
from sqlalchemy.orm import Session

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Local Podcast Host", version="1.0.0")

# Configuration
LOCAL_STORAGE_PATH = os.getenv("LOCAL_STORAGE_PATH", "/app/storage")
LOCAL_SERVER_URL = os.getenv("LOCAL_SERVER_URL", "http://localhost:8080")


class EpisodeResponse(BaseModel):
    id: str
    title: str
    description: str
    audio_url: str
    published_at: datetime
    duration_seconds: int
    file_size_bytes: int


@app.on_event("startup")
async def startup_event():
    create_tables()
    # Ensure storage directories exist
    storage_path = Path(LOCAL_STORAGE_PATH)
    storage_path.mkdir(parents=True, exist_ok=True)
    (storage_path / "episodes").mkdir(exist_ok=True)
    (storage_path / "rss").mkdir(exist_ok=True)
    (storage_path / "podcast").mkdir(exist_ok=True)
    logger.info("Local Podcast Host started")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "podcast-host", "timestamp": datetime.utcnow()}


@app.get("/episodes/{episode_id}")
async def get_episode_info(episode_id: UUID, db: Session = Depends(get_db)):
    """Get episode information."""
    try:
        # Get episode from database
        episode = db.query(Episode).filter(Episode.id == episode_id).first()
        if not episode:
            raise HTTPException(status_code=404, detail="Episode not found")
        
        # Get metadata
        metadata = db.query(EpisodeMetadata).filter(
            EpisodeMetadata.episode_id == episode_id
        ).first()
        
        # Get audio file
        audio_file = db.query(AudioFile).filter(
            AudioFile.episode_id == episode_id
        ).first()
        
        if not audio_file:
            raise HTTPException(status_code=404, detail="Audio file not found")
        
        return EpisodeResponse(
            id=str(episode.id),
            title=metadata.title if metadata else "Untitled Episode",
            description=metadata.description if metadata else "No description",
            audio_url=f"{LOCAL_SERVER_URL}/storage/episodes/{episode_id}/audio.wav",
            published_at=episode.created_at,
            duration_seconds=audio_file.duration_seconds or 0,
            file_size_bytes=audio_file.file_size_bytes or 0
        )
        
    except Exception as e:
        logger.error(f"Error getting episode info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/rss/episodes/{episode_id}")
async def get_episode_rss(episode_id: UUID, db: Session = Depends(get_db)):
    """Generate RSS feed for a specific episode."""
    try:
        # Get episode data
        episode = db.query(Episode).filter(Episode.id == episode_id).first()
        if not episode:
            raise HTTPException(status_code=404, detail="Episode not found")
        
        metadata = db.query(EpisodeMetadata).filter(
            EpisodeMetadata.episode_id == episode_id
        ).first()
        
        audio_file = db.query(AudioFile).filter(
            AudioFile.episode_id == episode_id
        ).first()
        
        if not audio_file:
            raise HTTPException(status_code=404, detail="Audio file not found")
        
        # Generate RSS XML
        title = metadata.title if metadata else "Untitled Episode"
        description = metadata.description if metadata else "No description"
        audio_url = f"{LOCAL_SERVER_URL}/storage/episodes/{episode_id}/audio.wav"
        pub_date = episode.created_at.strftime("%a, %d %b %Y %H:%M:%S GMT")
        
        rss_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
  <channel>
    <title>Local Podcast - {title}</title>
    <description>{description}</description>
    <link>{LOCAL_SERVER_URL}</link>
    <language>en</language>
    <pubDate>{pub_date}</pubDate>
    <lastBuildDate>{pub_date}</lastBuildDate>
    
    <item>
      <title>{title}</title>
      <description><![CDATA[{description}]]></description>
      <link>{LOCAL_SERVER_URL}/episodes/{episode_id}</link>
      <guid>{LOCAL_SERVER_URL}/episodes/{episode_id}</guid>
      <pubDate>{pub_date}</pubDate>
      <enclosure url="{audio_url}" type="audio/wav" length="{audio_file.file_size_bytes or 0}"/>
      <itunes:duration>{audio_file.duration_seconds or 0}</itunes:duration>
    </item>
  </channel>
</rss>"""
        
        return PlainTextResponse(
            content=rss_content,
            media_type="application/rss+xml"
        )
        
    except Exception as e:
        logger.error(f"Error generating RSS: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/podcast/episodes/{episode_id}")
async def get_podcast_episode(episode_id: UUID, db: Session = Depends(get_db)):
    """Get podcast episode page."""
    try:
        # Get episode data
        episode = db.query(Episode).filter(Episode.id == episode_id).first()
        if not episode:
            raise HTTPException(status_code=404, detail="Episode not found")
        
        metadata = db.query(EpisodeMetadata).filter(
            EpisodeMetadata.episode_id == episode_id
        ).first()
        
        audio_file = db.query(AudioFile).filter(
            AudioFile.episode_id == episode_id
        ).first()
        
        if not audio_file:
            raise HTTPException(status_code=404, detail="Audio file not found")
        
        title = metadata.title if metadata else "Untitled Episode"
        description = metadata.description if metadata else "No description"
        audio_url = f"{LOCAL_SERVER_URL}/storage/episodes/{episode_id}/audio.wav"
        
        # Generate simple HTML page
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
        .episode {{ background: #f5f5f5; padding: 20px; border-radius: 8px; margin: 20px 0; }}
        audio {{ width: 100%; margin: 10px 0; }}
        .metadata {{ color: #666; font-size: 0.9em; }}
    </style>
</head>
<body>
    <h1>Local Podcast</h1>
    <div class="episode">
        <h2>{title}</h2>
        <div class="metadata">
            <p><strong>Published:</strong> {episode.created_at.strftime("%B %d, %Y at %I:%M %p")}</p>
            <p><strong>Duration:</strong> {audio_file.duration_seconds or 0} seconds</p>
            <p><strong>File Size:</strong> {audio_file.file_size_bytes or 0} bytes</p>
        </div>
        <p>{description}</p>
        <audio controls>
            <source src="{audio_url}" type="audio/wav">
            Your browser does not support the audio element.
        </audio>
        <p><a href="{audio_url}" download>Download Audio File</a></p>
    </div>
    <p><a href="{LOCAL_SERVER_URL}/rss/episodes/{episode_id}">RSS Feed</a></p>
</body>
</html>"""
        
        return PlainTextResponse(
            content=html_content,
            media_type="text/html"
        )
        
    except Exception as e:
        logger.error(f"Error generating podcast page: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/episodes")
async def list_episodes(db: Session = Depends(get_db)):
    """List all episodes."""
    try:
        episodes = db.query(Episode).all()
        episode_list = []
        
        for episode in episodes:
            metadata = db.query(EpisodeMetadata).filter(
                EpisodeMetadata.episode_id == episode.id
            ).first()
            
            episode_list.append({
                "id": str(episode.id),
                "title": metadata.title if metadata else "Untitled Episode",
                "created_at": episode.created_at.isoformat(),
                "url": f"{LOCAL_SERVER_URL}/episodes/{episode.id}"
            })
        
        return {"episodes": episode_list}
        
    except Exception as e:
        logger.error(f"Error listing episodes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8006)
