"""
API Gateway - Central entry point for the Podcast AI application.
"""
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from uuid import UUID

import httpx
import os
from fastapi import FastAPI, HTTPException, Depends, Request, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session

from shared.database import get_db, create_tables
from shared.models import PodcastGroup, Episode, Presenter, Writer, NewsFeed
from shared.schemas import (
    PodcastGroup as PodcastGroupSchema,
    PodcastGroupCreate,
    PodcastGroupUpdate,
    Episode as EpisodeSchema,
    Presenter as PresenterSchema,
    PresenterCreate,
    Writer as WriterSchema,
    WriterCreate,
    NewsFeed as NewsFeedSchema,
    NewsFeedCreate,
    GenerationRequest,
    GenerationResponse,
    HealthCheck
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Podcast AI API Gateway", version="1.0.0")

# Templates for admin interface
templates = Jinja2Templates(directory="templates")
PUBLIC_MEDIA_BASE_URL = os.getenv("PUBLIC_MEDIA_BASE_URL", "http://localhost:8090")

# Service URLs
SERVICE_URLS = {
    "news-feed": "http://news-feed:8001",
    "text-generation": "http://text-generation:8002", 
    "writer": "http://writer:8003",
    "presenter": "http://presenter:8004",
    "publishing": "http://publishing:8005",
    "ai-overseer": "http://ai-overseer:8006"
}

# Create tables on startup
@app.on_event("startup")
async def startup_event():
    create_tables()
    logger.info("API Gateway started")


async def call_service(service_name: str, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
    """Make HTTP request to a microservice."""
    if service_name not in SERVICE_URLS:
        raise HTTPException(status_code=400, detail=f"Unknown service: {service_name}")
    
    url = f"{SERVICE_URLS[service_name]}{endpoint}"
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.request(method, url, **kwargs)
            response.raise_for_status()
            try:
                return response.json()
            except Exception:
                # Fallback to raw text if JSON parsing fails
                return {"status_code": response.status_code, "raw": response.text}
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Service communication error: {str(e)}")


# Health Check
@app.get("/health", response_model=HealthCheck)
async def health_check():
    """Health check endpoint."""
    services_status = {}
    
    # Check each service
    for service_name in SERVICE_URLS:
        try:
            await call_service(service_name, "GET", "/health")
            services_status[service_name] = "healthy"
        except Exception as e:
            services_status[service_name] = f"error: {str(e)}"
    
    # Check database
    try:
        db = next(get_db())
        db.execute("SELECT 1")
        services_status["database"] = "healthy"
    except Exception as e:
        services_status["database"] = f"error: {str(e)}"
    
    overall_status = "healthy" if all("error" not in status for status in services_status.values()) else "degraded"
    
    return HealthCheck(
        status=overall_status,
        timestamp=datetime.utcnow(),
        services=services_status
    )


# Admin Interface
@app.get("/", response_class=HTMLResponse)
async def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    """Admin dashboard home page."""
    
    # Get system stats
    total_groups = db.query(PodcastGroup).count()
    active_groups = db.query(PodcastGroup).filter(PodcastGroup.status == "active").count()
    total_episodes = db.query(Episode).count()
    
    # Get recent episodes and enrich with MP3 availability
    recent = db.query(Episode).order_by(Episode.created_at.desc()).limit(5).all()

    async def has_mp3(episode_id: str) -> bool:
        try:
            # Check via nginx internal network
            url = f"http://nginx:8080/storage/episodes/{episode_id}/audio.mp3"
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.head(url)
                return resp.status_code == 200
        except Exception:
            return False

    recent_episodes = []
    for ep in recent:
        ep_id = str(ep.id)
        status_value = getattr(ep.status, 'value', str(ep.status))
        mp3_ok = await has_mp3(ep_id)
        recent_episodes.append({
            'id': ep_id,
            'status': status_value,
            'created_at': ep.created_at,
            'has_mp3': mp3_ok,
            'mp3_url': f"{PUBLIC_MEDIA_BASE_URL}/storage/episodes/{ep_id}/audio.mp3",
            'listen_url': f"{PUBLIC_MEDIA_BASE_URL}/podcast/episodes/{ep_id}",
        })

    # Draft episodes queue (outstanding to be voiced)
    from shared.models import EpisodeStatus
    drafts = db.query(Episode).filter(Episode.status == EpisodeStatus.DRAFT).order_by(Episode.created_at.desc()).limit(20).all()
    draft_episodes = []
    for ep in drafts:
        ep_id = str(ep.id)
        group = db.query(PodcastGroup).filter(PodcastGroup.id == ep.group_id).first()
        draft_episodes.append({
            'id': ep_id,
            'group_name': group.name if group else 'Unknown',
            'created_at': ep.created_at,
            'voice_action': f"/api/management/voice/{ep_id}",
        })

    # Podcast groups and assignments
    groups = db.query(PodcastGroup).filter(PodcastGroup.status == "active").all()
    groups_info = []
    for g in groups:
        presenter_names = [p.name for p in getattr(g, 'presenters', [])]
        writer = db.query(Writer).filter(Writer.id == g.writer_id).first()
        groups_info.append({
            'id': str(g.id),
            'name': g.name,
            'presenters': presenter_names,
            'writer': writer.name if writer else 'Unassigned',
            'feeds': len(getattr(g, 'news_feeds', [])),
        })
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "total_groups": total_groups,
        "active_groups": active_groups,
        "total_episodes": total_episodes,
        "recent_episodes": recent_episodes,
        "draft_episodes": draft_episodes,
        "groups_info": groups_info,
    })


# Groups Management Page
@app.get("/groups", response_class=HTMLResponse)
async def groups_page(request: Request):
    """Render the Podcast Groups management UI (data fetched client-side)."""
    return templates.TemplateResponse("groups.html", {"request": request})


# Management endpoints
@app.get("/api/management/voicing-queue")
async def get_voicing_queue(db: Session = Depends(get_db)):
    from shared.models import EpisodeStatus
    drafts = db.query(Episode).filter(Episode.status == EpisodeStatus.DRAFT).order_by(Episode.created_at.desc()).all()
    out = []
    for ep in drafts:
        group = db.query(PodcastGroup).filter(PodcastGroup.id == ep.group_id).first()
        out.append({
            'id': str(ep.id),
            'created_at': ep.created_at.isoformat() if ep.created_at else None,
            'group_id': str(ep.group_id),
            'group_name': group.name if group else 'Unknown'
        })
    return { 'count': len(out), 'draft_episodes': out }


@app.api_route("/api/management/voice/{episode_id}", methods=["POST", "GET"])
async def voice_episode(episode_id: UUID, db: Session = Depends(get_db)):
    """Trigger voicing for an existing draft episode using Presenter service."""
    ep = db.query(Episode).filter(Episode.id == episode_id).first()
    if not ep:
        raise HTTPException(status_code=404, detail="Episode not found")
    group = db.query(PodcastGroup).filter(PodcastGroup.id == ep.group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Podcast group not found")
    presenter_ids = [str(p.id) for p in getattr(group, 'presenters', [])]
    if not presenter_ids:
        raise HTTPException(status_code=400, detail="No presenters assigned to this group")

    # Call Presenter
    payload = {
        'episode_id': str(episode_id),
        'script': ep.script or '',
        'presenter_ids': presenter_ids,
    }
    try:
        result = await call_service('presenter', 'POST', '/generate-audio', json=payload)
        # Mark episode voiced
        from shared.models import EpisodeStatus
        ep.status = EpisodeStatus.VOICED
        db.commit()
        return { 'status': 'voiced', 'episode_id': str(episode_id), 'presenter_result': result }
    except HTTPException as he:
        # Bubble up underlying detail for visibility
        try:
            d = he.detail
            if isinstance(d, dict):
                detail = d.get('detail') or d.get('raw') or str(d)
            else:
                detail = str(d)
        except Exception:
            detail = str(he)
        raise HTTPException(status_code=he.status_code, detail=f"Voicing failed: {detail}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Voicing failed: {str(e)}")


@app.post("/api/management/voice-all")
async def voice_all_drafts(limit: int = 10, db: Session = Depends(get_db)):
    from shared.models import EpisodeStatus
    drafts = db.query(Episode).filter(Episode.status == EpisodeStatus.DRAFT).order_by(Episode.created_at.desc()).limit(limit).all()
    voiced = []
    failed = []
    for ep in drafts:
        try:
            await voice_episode(ep.id, db)
            voiced.append(str(ep.id))
        except Exception as e:
            failed.append({ 'episode_id': str(ep.id), 'error': str(e) })
    return { 'voiced': voiced, 'failed': failed }


# Podcast Groups API
@app.get("/api/podcast-groups", response_model=List[PodcastGroupSchema])
async def list_podcast_groups(
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    """List all podcast groups."""
    query = db.query(PodcastGroup)
    if active_only:
        query = query.filter(PodcastGroup.status == "active")
    
    return query.all()


@app.post("/api/podcast-groups", response_model=PodcastGroupSchema)
async def create_podcast_group(
    group_data: PodcastGroupCreate,
    db: Session = Depends(get_db)
):
    """Create a new podcast group."""
    # Validate presenters exist
    presenters = db.query(Presenter).filter(
        Presenter.id.in_(group_data.presenter_ids)
    ).all()
    
    if len(presenters) != len(group_data.presenter_ids):
        raise HTTPException(status_code=400, detail="One or more presenters not found")
    
    # Validate writer exists
    writer = db.query(Writer).filter(Writer.id == group_data.writer_id).first()
    if not writer:
        raise HTTPException(status_code=400, detail="Writer not found")
    
    # Validate news feeds exist
    feeds = db.query(NewsFeed).filter(
        NewsFeed.id.in_(group_data.news_feed_ids)
    ).all()
    
    if len(feeds) != len(group_data.news_feed_ids):
        raise HTTPException(status_code=400, detail="One or more news feeds not found")
    
    # Create podcast group
    group = PodcastGroup(
        name=group_data.name,
        description=group_data.description,
        category=group_data.category,
        subcategory=group_data.subcategory,
        language=group_data.language,
        country=group_data.country,
        tags=group_data.tags,
        keywords=group_data.keywords,
        schedule=group_data.schedule,
        status=group_data.status,
        writer_id=group_data.writer_id
    )
    
    db.add(group)
    db.commit()
    db.refresh(group)
    
    # Add presenters and feeds
    group.presenters = presenters
    group.news_feeds = feeds
    db.commit()
    
    return group


@app.get("/api/podcast-groups/{group_id}", response_model=PodcastGroupSchema)
async def get_podcast_group(
    group_id: UUID,
    db: Session = Depends(get_db)
):
    """Get a specific podcast group."""
    group = db.query(PodcastGroup).filter(PodcastGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Podcast group not found")
    return group


@app.put("/api/podcast-groups/{group_id}", response_model=PodcastGroupSchema)
async def update_podcast_group(
    group_id: UUID,
    group_data: PodcastGroupUpdate,
    db: Session = Depends(get_db)
):
    """Update a podcast group."""
    group = db.query(PodcastGroup).filter(PodcastGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Podcast group not found")
    
    update_data = group_data.dict(exclude_unset=True)
    
    # Handle presenter updates
    if "presenter_ids" in update_data:
        presenters = db.query(Presenter).filter(
            Presenter.id.in_(update_data["presenter_ids"])
        ).all()
        group.presenters = presenters
        del update_data["presenter_ids"]
    
    # Handle writer updates
    if "writer_id" in update_data:
        writer = db.query(Writer).filter(Writer.id == update_data["writer_id"]).first()
        if not writer:
            raise HTTPException(status_code=400, detail="Writer not found")
        group.writer_id = update_data["writer_id"]
        del update_data["writer_id"]
    
    # Handle news feed updates
    if "news_feed_ids" in update_data:
        feeds = db.query(NewsFeed).filter(
            NewsFeed.id.in_(update_data["news_feed_ids"])
        ).all()
        group.news_feeds = feeds
        del update_data["news_feed_ids"]
    
    # Update other fields
    for field, value in update_data.items():
        setattr(group, field, value)
    
    db.commit()
    db.refresh(group)
    return group


@app.delete("/api/podcast-groups/{group_id}")
async def delete_podcast_group(
    group_id: UUID,
    db: Session = Depends(get_db)
):
    """Delete a podcast group."""
    group = db.query(PodcastGroup).filter(PodcastGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Podcast group not found")
    
    db.delete(group)
    db.commit()
    return {"message": "Podcast group deleted successfully"}


# Episode Generation
@app.post("/api/generate-episode", response_model=GenerationResponse)
async def generate_episode(
    request: GenerationRequest,
    db: Session = Depends(get_db)
):
    """Generate a complete episode for a podcast group."""
    
    # Forward request to AI Overseer service
    # Convert UUID to string for JSON serialization
    request_dict = request.dict()
    logger.info(f"Original request_dict: {request_dict}")
    
    # Convert all UUID fields to strings
    for key, value in request_dict.items():
        if hasattr(value, '__class__') and 'UUID' in str(value.__class__):
            request_dict[key] = str(value)
            logger.info(f"Converted {key} from UUID to string: {request_dict[key]}")
    
    logger.info(f"Final request_dict: {request_dict}")
    
    return await call_service("ai-overseer", "POST", "/generate-episode", json=request_dict)


@app.get("/api/episodes", response_model=List[EpisodeSchema])
async def list_episodes(
    group_id: Optional[UUID] = None,
    status: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """List episodes."""
    query = db.query(Episode)
    
    if group_id:
        query = query.filter(Episode.group_id == group_id)
    
    if status:
        try:
            from shared.models import EpisodeStatus
            episode_status = EpisodeStatus(status)
            query = query.filter(Episode.status == episode_status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    
    return query.order_by(Episode.created_at.desc()).limit(limit).all()


@app.get("/api/episodes/{episode_id}", response_model=EpisodeSchema)
async def get_episode(
    episode_id: UUID,
    db: Session = Depends(get_db)
):
    """Get a specific episode."""
    episode = db.query(Episode).filter(Episode.id == episode_id).first()
    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")
    return episode


# Presenters API
@app.get("/api/presenters", response_model=List[PresenterSchema])
async def list_presenters(db: Session = Depends(get_db)):
    """List all presenters."""
    return db.query(Presenter).all()


@app.post("/api/presenters", response_model=PresenterSchema)
async def create_presenter(
    presenter_data: PresenterCreate,
    db: Session = Depends(get_db)
):
    """Create a new presenter."""
    presenter = Presenter(**presenter_data.dict())
    db.add(presenter)
    db.commit()
    db.refresh(presenter)
    return presenter


# Writers API
@app.get("/api/writers", response_model=List[WriterSchema])
async def list_writers(db: Session = Depends(get_db)):
    """List all writers."""
    return db.query(Writer).all()


@app.post("/api/writers", response_model=WriterSchema)
async def create_writer(
    writer_data: WriterCreate,
    db: Session = Depends(get_db)
):
    """Create a new writer."""
    writer = Writer(**writer_data.dict())
    db.add(writer)
    db.commit()
    db.refresh(writer)
    return writer


# News Feeds API
@app.get("/api/news-feeds", response_model=List[NewsFeedSchema])
async def list_news_feeds(db: Session = Depends(get_db)):
    """List all news feeds."""
    return db.query(NewsFeed).all()


@app.post("/api/news-feeds", response_model=NewsFeedSchema)
async def create_news_feed(
    feed_data: NewsFeedCreate,
    db: Session = Depends(get_db)
):
    """Create a new news feed."""
    # Forward to news-feed service
    return await call_service("news-feed", "POST", "/feeds", json=feed_data.dict())


# System Management
@app.get("/api/stats")
async def get_system_stats(db: Session = Depends(get_db)):
    """Get system statistics."""
    # Get stats from AI Overseer
    return await call_service("ai-overseer", "GET", "/stats")


@app.post("/api/admin/cleanup")
async def cleanup_old_data():
    """Trigger cleanup of old data."""
    return await call_service("ai-overseer", "POST", "/admin/cleanup")


# Service-specific endpoints (proxied)
@app.get("/api/services/{service_name}/health")
async def get_service_health(service_name: str):
    """Get health status of a specific service."""
    if service_name not in SERVICE_URLS:
        raise HTTPException(status_code=404, detail="Service not found")
    
    return await call_service(service_name, "GET", "/health")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
