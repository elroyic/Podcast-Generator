#!/usr/bin/env python3
"""
Hybrid API Gateway - Uses main application database with working simple services.
"""

import asyncio
import logging
import os
import tempfile
from datetime import datetime
from typing import Dict, Any, Optional, List
from uuid import UUID, uuid4

import httpx
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session

# Add the shared directory to Python path
import sys
sys.path.append('/app/shared')

from database import get_db, create_tables
from models import PodcastGroup, Episode, EpisodeStatus, Presenter, Writer, NewsFeed
from schemas import (
    PodcastGroup as PodcastGroupSchema,
    Episode as EpisodeSchema,
    Presenter as PresenterSchema,
    Writer as WriterSchema,
    NewsFeed as NewsFeedSchema,
    GenerationRequest,
    GenerationResponse,
    HealthCheck
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Podcast AI Hybrid API Gateway", version="1.0.0")

# Simple service URLs (working services)
SIMPLE_SERVICE_URLS = {
    "news-feed": "http://localhost:8001",
    "text-generation": "http://localhost:8002", 
    "writer": "http://localhost:8003",
    "presenter": "http://localhost:8004",
    "publishing": "http://localhost:8005",
    "podcast-host": "http://localhost:8006"
}

@app.on_event("startup")
async def startup_event():
    """Initialize the application."""
    logger.info("Hybrid API Gateway started")
    # Create database tables
    create_tables()

async def call_simple_service(service_name: str, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
    """Make HTTP request to a simple service."""
    if service_name not in SIMPLE_SERVICE_URLS:
        raise HTTPException(status_code=400, detail=f"Unknown service: {service_name}")
    
    url = f"{SIMPLE_SERVICE_URLS[service_name]}{endpoint}"
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Service communication error: {str(e)}")

# Health Check
@app.get("/health", response_model=HealthCheck)
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "hybrid-api-gateway", "timestamp": datetime.utcnow()}

# Presenter endpoints
@app.post("/api/presenters", response_model=PresenterSchema)
async def create_presenter(presenter: PresenterSchema, db: Session = Depends(get_db)):
    """Create a new presenter."""
    db_presenter = Presenter(
        id=uuid4(),
        name=presenter.name,
        bio=presenter.bio,
        gender=presenter.gender,
        country=presenter.country,
        city=presenter.city,
        created_at=datetime.utcnow()
    )
    db.add(db_presenter)
    db.commit()
    db.refresh(db_presenter)
    return db_presenter

@app.get("/api/presenters", response_model=List[PresenterSchema])
async def list_presenters(db: Session = Depends(get_db)):
    """List all presenters."""
    return db.query(Presenter).all()

# Writer endpoints
@app.post("/api/writers", response_model=WriterSchema)
async def create_writer(writer: WriterSchema, db: Session = Depends(get_db)):
    """Create a new writer."""
    db_writer = Writer(
        id=uuid4(),
        name=writer.name,
        capabilities=writer.capabilities,
        created_at=datetime.utcnow()
    )
    db.add(db_writer)
    db.commit()
    db.refresh(db_writer)
    return db_writer

@app.get("/api/writers", response_model=List[WriterSchema])
async def list_writers(db: Session = Depends(get_db)):
    """List all writers."""
    return db.query(Writer).all()

# News Feed endpoints
@app.post("/api/news-feeds", response_model=NewsFeedSchema)
async def create_news_feed(feed: NewsFeedSchema, db: Session = Depends(get_db)):
    """Create a new news feed."""
    db_feed = NewsFeed(
        id=uuid4(),
        source_url=feed.source_url,
        name=feed.name,
        type=feed.type,
        is_active=feed.is_active,
        created_at=datetime.utcnow()
    )
    db.add(db_feed)
    db.commit()
    db.refresh(db_feed)
    return db_feed

@app.get("/api/news-feeds", response_model=List[NewsFeedSchema])
async def list_news_feeds(db: Session = Depends(get_db)):
    """List all news feeds."""
    return db.query(NewsFeed).all()

# Podcast Group endpoints
@app.post("/api/podcast-groups", response_model=PodcastGroupSchema)
async def create_podcast_group(group: PodcastGroupSchema, db: Session = Depends(get_db)):
    """Create a new podcast group."""
    db_group = PodcastGroup(
        id=uuid4(),
        name=group.name,
        description=group.description,
        category=group.category,
        presenter_ids=group.presenter_ids,
        writer_id=group.writer_id,
        news_feed_ids=group.news_feed_ids,
        is_active=True,
        created_at=datetime.utcnow()
    )
    db.add(db_group)
    db.commit()
    db.refresh(db_group)
    return db_group

@app.get("/api/podcast-groups", response_model=List[PodcastGroupSchema])
async def list_podcast_groups(db: Session = Depends(get_db)):
    """List all podcast groups."""
    return db.query(PodcastGroup).all()

# Episode Generation endpoint
@app.post("/api/generate-episode", response_model=GenerationResponse)
async def generate_episode(request: GenerationRequest, db: Session = Depends(get_db)):
    """Generate a complete episode using hybrid approach."""
    
    # Find the podcast group
    group = db.query(PodcastGroup).filter(PodcastGroup.id == request.group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Podcast group not found")
    
    # Create episode record
    episode = Episode(
        id=uuid4(),
        group_id=group.id,
        title="",
        description="",
        status=EpisodeStatus.GENERATING,
        script="",
        duration_seconds=0,
        file_path="",
        created_at=datetime.utcnow()
    )
    db.add(episode)
    db.commit()
    db.refresh(episode)
    
    try:
        # Step 1: Get news articles
        logger.info("📰 Fetching news articles...")
        news_response = await call_simple_service("news-feed", "GET", f"/feeds/{group.news_feed_ids[0]}/articles")
        articles = news_response.get("articles", [])
        logger.info(f"✅ Fetched {len(articles)} articles")
        
        # Step 2: Generate script using Ollama
        logger.info("✍️ Generating script...")
        script_request = {
            "group_id": str(group.id),
            "articles": articles,
            "target_duration": 75  # 1 minute 15 seconds
        }
        script_response = await call_simple_service("text-generation", "POST", "/generate-script", json=script_request)
        script = script_response.get("script", "")
        logger.info(f"✅ Generated script ({len(script)} characters)")
        
        # Step 3: Generate metadata
        logger.info("📝 Generating metadata...")
        metadata_request = {
            "episode_id": str(episode.id),
            "script": script,
            "group_id": str(group.id)
        }
        metadata_response = await call_simple_service("writer", "POST", "/generate-metadata", json=metadata_request)
        title = metadata_response.get("title", "Spring Weather Podcast Episode")
        description = metadata_response.get("description", "A podcast about spring weather patterns")
        logger.info(f"✅ Generated metadata: {title}")
        
        # Step 4: Generate MP3 audio
        logger.info("🎵 Generating MP3 audio...")
        audio_request = {
            "episode_id": str(episode.id),
            "script": script,
            "presenter_ids": group.presenter_ids,
            "voice_settings": {
                "speed": 1.0,
                "pitch": 1.0,
                "volume": 1.0
            }
        }
        audio_response = await call_simple_service("presenter", "POST", "/generate-audio", json=audio_request)
        audio_url = audio_response.get("audio_url", "")
        duration = audio_response.get("duration_seconds", 0)
        file_size = audio_response.get("file_size_bytes", 0)
        logger.info(f"✅ Generated MP3 audio: {audio_url}")
        
        # Step 5: Update episode with results
        episode.title = title
        episode.description = description
        episode.script = script
        episode.duration_seconds = duration
        episode.file_path = audio_url
        episode.status = EpisodeStatus.COMPLETED
        db.commit()
        
        logger.info("🎉 Episode generation completed successfully!")
        
        return GenerationResponse(
            episode_id=str(episode.id),
            status="completed",
            message=f"Episode '{title}' generated successfully! Duration: {duration}s, Size: {file_size} bytes"
        )
        
    except Exception as e:
        logger.error(f"❌ Episode generation failed: {e}")
        episode.status = EpisodeStatus.FAILED
        db.commit()
        
        return GenerationResponse(
            episode_id=str(episode.id),
            status="failed",
            message=f"Episode generation failed: {str(e)}"
        )

# Episode endpoints
@app.get("/api/episodes", response_model=List[EpisodeSchema])
async def list_episodes(group_id: Optional[UUID] = None, db: Session = Depends(get_db)):
    """List episodes, optionally filtered by group."""
    query = db.query(Episode)
    if group_id:
        query = query.filter(Episode.group_id == group_id)
    return query.order_by(Episode.created_at.desc()).all()

@app.get("/api/episodes/{episode_id}", response_model=EpisodeSchema)
async def get_episode(episode_id: UUID, db: Session = Depends(get_db)):
    """Get a specific episode."""
    episode = db.query(Episode).filter(Episode.id == episode_id).first()
    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")
    return episode

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

