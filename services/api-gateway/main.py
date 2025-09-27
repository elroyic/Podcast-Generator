"""
API Gateway - Central entry point for the Podcast AI application.
"""
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from uuid import UUID

import httpx
import os
import jwt
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Depends, Request, BackgroundTasks, Header
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import text, func

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
from fastapi import Body

import os
import subprocess

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Podcast AI API Gateway", version="1.0.0")

# Templates for admin interface
templates = Jinja2Templates(directory="templates")
PUBLIC_MEDIA_BASE_URL = os.getenv("PUBLIC_MEDIA_BASE_URL", "http://localhost:8095")

# JWT Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-super-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24

# Authentication
security = HTTPBearer(auto_error=False)

# Service URLs
SERVICE_URLS = {
    "news-feed": "http://news-feed:8001",
    "text-generation": "http://text-generation:8002",
    "writer": "http://writer:8003",
    "presenter": "http://presenter:8004",
    # Internal-only services (no host port mapping needed)
    "publishing": "http://publishing:8005",
    # Correct port for enhanced overseer service
    "ai-overseer": "http://ai-overseer:8012",
    "reviewer": "http://reviewer:8008",
}

# JWT Helper Functions
def create_jwt_token(username: str) -> str:
    """Create a JWT token for a user."""
    expiry = datetime.utcnow() + timedelta(hours=JWT_EXPIRE_HOURS)
    payload = {
        "sub": username,
        "exp": expiry,
        "iat": datetime.utcnow(),
        "role": "admin"  # Simple role-based auth
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def verify_jwt_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify a JWT token and return payload."""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Get current authenticated user from JWT token."""
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    payload = verify_jwt_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return payload


def admin_required(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Require admin role for endpoint access."""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


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


# Authentication Endpoints
@app.post("/api/auth/login")
async def login(credentials: Dict[str, str] = Body(...)):
    """Simple login endpoint - in production, validate against a user database."""
    username = credentials.get("username")
    password = credentials.get("password")
    
    # Simple hardcoded admin credentials (in production, use proper user management)
    if username == "admin" and password == os.getenv("ADMIN_PASSWORD", "admin123"):
        token = create_jwt_token(username)
        return {
            "access_token": token,
            "token_type": "bearer",
            "username": username,
            "role": "admin"
        }
    else:
        raise HTTPException(status_code=401, detail="Invalid credentials")


@app.post("/api/auth/verify")
async def verify_token(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Verify if current token is valid."""
    return {
        "valid": True,
        "username": current_user.get("sub"),
        "role": current_user.get("role"),
        "expires": current_user.get("exp")
    }


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
        # SQLAlchemy 2.x requires using text() for textual SQL
        db.execute(text("SELECT 1"))
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


# Reviewer Dashboard Page
@app.get("/reviewer", response_class=HTMLResponse)
async def reviewer_dashboard(request: Request):
    """Render the Reviewer Dashboard UI."""
    return templates.TemplateResponse("reviewer-dashboard.html", {"request": request})


# Presenter Management Page
@app.get("/presenters", response_class=HTMLResponse)
async def presenter_management(request: Request):
    """Render the Presenter Management UI."""
    return templates.TemplateResponse("presenter-management.html", {"request": request})


# Episodes Page
@app.get("/episodes", response_class=HTMLResponse)
async def episodes_page(request: Request):
    """Render the Episodes UI."""
    return templates.TemplateResponse("episodes.html", {"request": request})


# News Feed Dashboard Page
@app.get("/news-feed", response_class=HTMLResponse)
async def news_feed_dashboard(request: Request):
    """Render the News Feed Dashboard UI."""
    return templates.TemplateResponse("news-feed-dashboard.html", {"request": request})


# Collections Dashboard Page
@app.get("/collections", response_class=HTMLResponse)
async def collections_dashboard(request: Request):
    """Render the Collections Dashboard UI."""
    return templates.TemplateResponse("collections-dashboard.html", {"request": request})


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
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(admin_required)
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
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(admin_required)
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
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(admin_required)
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


@app.get("/api/episodes-simple")
async def list_episodes_simple(
    group_id: Optional[UUID] = None,
    status: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """List episodes with simple data (no complex relationships)."""
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
    
    episodes = query.order_by(Episode.created_at.desc()).limit(limit).all()
    
    # Convert to simple format
    simple_episodes = []
    for episode in episodes:
        # Get group name
        group_name = "Unknown"
        if episode.group_id:
            group = db.query(PodcastGroup).filter(PodcastGroup.id == episode.group_id).first()
            if group:
                group_name = group.name
        
        simple_episodes.append({
            "id": str(episode.id),
            "group_id": str(episode.group_id) if episode.group_id else None,
            "group_name": group_name,
            "status": episode.status.value if episode.status else "unknown",
            "created_at": episode.created_at.isoformat() if episode.created_at else None
        })
    
    return simple_episodes


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


@app.get("/api/episodes/{episode_id}/download")
async def download_episode(
    episode_id: UUID,
    db: Session = Depends(get_db)
):
    """Download episode audio file."""
    from shared.models import AudioFile
    from fastapi.responses import RedirectResponse
    
    # Get episode
    episode = db.query(Episode).filter(Episode.id == episode_id).first()
    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")
    
    # Get audio file
    audio_file = db.query(AudioFile).filter(AudioFile.episode_id == episode_id).first()
    if not audio_file:
        raise HTTPException(status_code=404, detail="Audio file not found for this episode")
    
    # Check if this is a local file path or external URL
    if audio_file.url.startswith("http"):
        # External URL - redirect directly
        return RedirectResponse(url=audio_file.url)
    else:
        # Local path - serve via nginx
        nginx_url = f"http://localhost:8080{audio_file.url}"
        return RedirectResponse(url=nginx_url)


# Presenters API
@app.get("/api/presenters", response_model=List[PresenterSchema])
async def list_presenters(db: Session = Depends(get_db)):
    """List all presenters."""
    return db.query(Presenter).all()


@app.get("/api/presenters/{presenter_id}", response_model=PresenterSchema)
async def get_presenter(
    presenter_id: UUID,
    db: Session = Depends(get_db)
):
    """Get a specific presenter."""
    presenter = db.query(Presenter).filter(Presenter.id == presenter_id).first()
    if not presenter:
        raise HTTPException(status_code=404, detail="Presenter not found")
    return presenter


@app.put("/api/presenters/{presenter_id}", response_model=PresenterSchema)
async def update_presenter(
    presenter_id: UUID,
    presenter_data: PresenterCreate,
    db: Session = Depends(get_db)
):
    """Update a presenter."""
    presenter = db.query(Presenter).filter(Presenter.id == presenter_id).first()
    if not presenter:
        raise HTTPException(status_code=404, detail="Presenter not found")
    
    update_data = presenter_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(presenter, field, value)
    
    db.commit()
    db.refresh(presenter)
    return presenter


@app.delete("/api/presenters/{presenter_id}")
async def delete_presenter(
    presenter_id: UUID,
    db: Session = Depends(get_db)
):
    """Delete a presenter."""
    presenter = db.query(Presenter).filter(Presenter.id == presenter_id).first()
    if not presenter:
        raise HTTPException(status_code=404, detail="Presenter not found")
    
    db.delete(presenter)
    db.commit()
    return {"message": "Presenter deleted successfully"}


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


# Reviewer proxy endpoints
@app.get("/api/reviewer/config")
async def get_reviewer_config():
    return await call_service("reviewer", "GET", "/config")


@app.put("/api/reviewer/config")
async def put_reviewer_config(payload: Dict[str, Any] = Body(...)):
    return await call_service("reviewer", "PUT", "/config", json=payload)


@app.get("/api/reviewer/metrics")
async def get_reviewer_metrics():
    return await call_service("reviewer", "GET", "/metrics")


@app.post("/api/reviewer/scale/light")
async def scale_light_reviewer(workers: int = Body(embed=True, default=1)):
    # Store desired count in reviewer config; external process handles applying scale
    await call_service("reviewer", "PUT", "/config", json={"light_workers": workers})
    return {"status": "ok", "workers": workers}


@app.get("/api/cadence/status")
async def get_cadence_status(group_id: Optional[str] = None):
    """Get cadence status for podcast groups."""
    if group_id:
        return await call_service("ai-overseer", "GET", f"/cadence/status?group_id={group_id}")
    else:
        return await call_service("ai-overseer", "GET", "/cadence/status")


@app.get("/api/overseer/duplicates")
async def get_overseer_duplicates(since: str):
    return await call_service("ai-overseer", "GET", f"/api/overseer/duplicates?since={since}")


# News Feed API endpoints
@app.get("/api/news-feed/stats")
async def get_news_feed_stats(db: Session = Depends(get_db)):
    """Get news feed statistics."""
    from shared.models import NewsFeed, Article
    from datetime import datetime, timedelta
    
    # Get total feeds
    total_feeds = db.query(NewsFeed).count()
    
    # Get active feeds
    active_feeds = db.query(NewsFeed).filter(NewsFeed.is_active == True).count()
    
    # Get articles from today
    today = datetime.now().date()
    articles_today = db.query(Article).filter(
        Article.created_at >= today
    ).count()
    
    # Get last fetch time
    last_feed = db.query(NewsFeed).filter(
        NewsFeed.last_fetched.isnot(None)
    ).order_by(NewsFeed.last_fetched.desc()).first()
    
    last_fetch = last_feed.last_fetched.isoformat() if last_feed and last_feed.last_fetched else None
    
    return {
        "total_feeds": total_feeds,
        "active_feeds": active_feeds,
        "articles_today": articles_today,
        "last_fetch": last_fetch
    }


@app.get("/api/news-feed/recent-articles")
async def get_recent_articles(limit: int = 10, db: Session = Depends(get_db)):
    """Get recent articles from all feeds."""
    from shared.models import Article, NewsFeed
    
    articles = db.query(Article).join(NewsFeed).order_by(
        Article.created_at.desc()
    ).limit(limit).all()
    
    result = []
    for article in articles:
        feed = db.query(NewsFeed).filter(NewsFeed.id == article.feed_id).first()
        result.append({
            "id": str(article.id),
            "title": article.title,
            "link": article.link,
            "summary": article.summary,
            "publish_date": article.publish_date.isoformat() if article.publish_date else None,
            "feed_name": feed.name if feed else "Unknown Feed",
            "reviewer_type": article.reviewer_type,
            "confidence": article.confidence
        })
    
    return result


@app.get("/api/news-feed/performance")
async def get_news_feed_performance(hours: int = 24, db: Session = Depends(get_db)):
    """Return time-series of article counts per hour for the last N hours.
    Uses Article.created_at for ingestion-based performance.
    """
    from shared.models import Article
    from datetime import datetime, timedelta

    # Normalize to the top of the current hour (UTC)
    now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
    start = now - timedelta(hours=hours - 1)

    # Query counts grouped per hour using Postgres date_trunc
    rows = (
        db.query(
            func.date_trunc('hour', Article.created_at).label('bucket'),
            func.count(Article.id)
        )
        .filter(Article.created_at >= start)
        .group_by('bucket')
        .order_by('bucket')
        .all()
    )

    # Map results for quick lookup
    bucket_to_count = {}
    for bucket_dt, count in rows:
        try:
            # bucket_dt may be timezone-aware depending on DB config
            key = bucket_dt.replace(minute=0, second=0, microsecond=0, tzinfo=None)
        except Exception:
            key = bucket_dt
        bucket_to_count[key] = int(count)

    labels: list[str] = []
    counts: list[int] = []
    # Build a contiguous series covering the full window
    for i in range(hours):
        ts = start + timedelta(hours=i)
        labels.append(ts.strftime("%H:00"))
        counts.append(int(bucket_to_count.get(ts, 0)))

    return {
        "start": start.isoformat() + "Z",
        "end": now.isoformat() + "Z",
        "labels": labels,
        "counts": counts,
    }


@app.post("/api/news-feed/refresh/{feed_id}")
async def refresh_feed(feed_id: UUID, db: Session = Depends(get_db)):
    """Trigger a manual refresh of a specific news feed."""
    from shared.models import NewsFeed, Article
    import httpx
    import feedparser
    from datetime import datetime
    
    # Get the feed
    feed = db.query(NewsFeed).filter(NewsFeed.id == feed_id).first()
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")
    
    try:
        # Fetch the RSS feed
        async with httpx.AsyncClient() as client:
            response = await client.get(feed.source_url, timeout=30.0)
            response.raise_for_status()
            
        # Parse the feed
        parsed_feed = feedparser.parse(response.text)
        
        if parsed_feed.bozo:
            return {"success": False, "error": "Invalid RSS feed format", "entries_processed": 0}
        
        # Process new entries
        entries_processed = 0
        for entry in parsed_feed.entries[:10]:  # Limit to 10 most recent entries
            # Check if article already exists
            existing = db.query(Article).filter(
                Article.feed_id == feed.id,
                Article.link == entry.link
            ).first()
            
            if not existing:
                # Create new article
                article = Article(
                    feed_id=feed.id,
                    title=entry.title,
                    link=entry.link,
                    summary=entry.summary if hasattr(entry, 'summary') else None,
                    content=entry.content[0].value if hasattr(entry, 'content') and entry.content else None,
                    publish_date=datetime(*entry.published_parsed[:6]) if hasattr(entry, 'published_parsed') else None
                )
                db.add(article)
                entries_processed += 1
        
        # Update feed last_fetched
        feed.last_fetched = datetime.utcnow()
        db.commit()
        
        return {
            "success": True, 
            "message": f"Feed refreshed successfully. {entries_processed} new articles processed.",
            "entries_processed": entries_processed
        }
        
    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e), "entries_processed": 0}


@app.post("/api/news-feed/refresh-all")
async def refresh_all_feeds(db: Session = Depends(get_db)):
    """Trigger refresh for all active news feeds via the news-feed service."""
    try:
        # Get all active feeds
        feeds = db.query(NewsFeed).filter(NewsFeed.is_active == True).all()

        triggered = 0
        errors: list[str] = []

        for feed in feeds:
            try:
                await call_service("news-feed", "POST", f"/feeds/{feed.id}/fetch")
                triggered += 1
            except Exception as e:
                errors.append(f"{feed.id}: {str(e)}")

        return {
            "success": len(errors) == 0,
            "triggered": triggered,
            "errors": errors,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to trigger feed refresh: {str(e)}")


# Collections API endpoints
@app.get("/api/collections/stats")
async def get_collections_stats(db: Session = Depends(get_db)):
    """Get collections statistics."""
    from shared.models import Collection, Article
    
    # Get total collections
    total_collections = db.query(Collection).count()
    
    # Get ready collections
    ready_collections = db.query(Collection).filter(Collection.status == "ready").count()
    
    # Get processing collections
    processing_collections = db.query(Collection).filter(Collection.status == "processing").count()
    
    # Get total articles in collections
    total_articles = db.query(Article).join(Collection).count()
    
    return {
        "total_collections": total_collections,
        "ready_collections": ready_collections,
        "processing_collections": processing_collections,
        "total_articles": total_articles
    }


@app.get("/api/collections")
async def list_collections(db: Session = Depends(get_db)):
    """List all collections."""
    from shared.models import Collection, PodcastGroup
    
    collections = db.query(Collection).all()
    
    result = []
    for collection in collections:
        # Get group name
        group_name = "Unknown Group"
        if collection.group_id:
            group = db.query(PodcastGroup).filter(PodcastGroup.id == collection.group_id).first()
            if group:
                group_name = group.name
        
        # Get article count
        article_count = db.query(Article).filter(Article.collection_id == collection.id).count()
        
        result.append({
            "id": str(collection.id),
            "group_id": str(collection.group_id) if collection.group_id else None,
            "group_name": group_name,
            "status": collection.status,
            "article_count": article_count,
            "created_at": collection.created_at.isoformat() if collection.created_at else None,
            "updated_at": collection.updated_at.isoformat() if collection.updated_at else None
        })
    
    return result


@app.get("/api/collections/{collection_id}")
async def get_collection(collection_id: UUID, db: Session = Depends(get_db)):
    """Get a specific collection with its articles."""
    from shared.models import Collection, Article, NewsFeed, PodcastGroup
    
    collection = db.query(Collection).filter(Collection.id == collection_id).first()
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    # Get group name
    group_name = "Unknown Group"
    if collection.group_id:
        group = db.query(PodcastGroup).filter(PodcastGroup.id == collection.group_id).first()
        if group:
            group_name = group.name
    
    # Get articles
    articles = db.query(Article).filter(Article.collection_id == collection.id).all()
    
    article_list = []
    for article in articles:
        feed = db.query(NewsFeed).filter(NewsFeed.id == article.feed_id).first()
        article_list.append({
            "id": str(article.id),
            "title": article.title,
            "link": article.link,
            "summary": article.summary,
            "publish_date": article.publish_date.isoformat() if article.publish_date else None,
            "feed_name": feed.name if feed else "Unknown Feed",
            "reviewer_type": article.reviewer_type,
            "confidence": article.confidence
        })
    
    return {
        "id": str(collection.id),
        "group_id": str(collection.group_id) if collection.group_id else None,
        "group_name": group_name,
        "status": collection.status,
        "created_at": collection.created_at.isoformat() if collection.created_at else None,
        "updated_at": collection.updated_at.isoformat() if collection.updated_at else None,
        "articles": article_list
    }


@app.post("/api/collections")
async def create_collection(
    collection_data: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db)
):
    """Create a new collection."""
    from shared.models import Collection, PodcastGroup
    
    # Validate group exists
    group_id = collection_data.get("group_id")
    if group_id:
        group = db.query(PodcastGroup).filter(PodcastGroup.id == group_id).first()
        if not group:
            raise HTTPException(status_code=404, detail="Podcast group not found")
    
    # Create collection
    collection = Collection(
        group_id=group_id,
        status=collection_data.get("status", "processing")
    )
    db.add(collection)
    db.commit()
    db.refresh(collection)
    
    return {
        "id": str(collection.id),
        "group_id": str(collection.group_id) if collection.group_id else None,
        "status": collection.status,
        "created_at": collection.created_at.isoformat(),
        "updated_at": collection.updated_at.isoformat()
    }


@app.put("/api/collections/{collection_id}")
async def update_collection(
    collection_id: UUID,
    collection_data: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db)
):
    """Update a collection."""
    from shared.models import Collection
    
    collection = db.query(Collection).filter(Collection.id == collection_id).first()
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    # Update fields
    if "status" in collection_data:
        collection.status = collection_data["status"]
    
    db.commit()
    db.refresh(collection)
    
    return {
        "id": str(collection.id),
        "group_id": str(collection.group_id) if collection.group_id else None,
        "status": collection.status,
        "created_at": collection.created_at.isoformat(),
        "updated_at": collection.updated_at.isoformat()
    }


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
