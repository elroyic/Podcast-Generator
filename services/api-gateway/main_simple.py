"""
Simplified API Gateway for local testing.
This version works with the simplified services and uses SQLite.
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from uuid import UUID, uuid4

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Podcast AI API Gateway (Simple)", version="1.0.0")

# In-memory storage for testing
podcast_groups = []
presenters = []
writers = []
news_feeds = []
episodes = []

# Simple models for testing
class PodcastGroup:
    def __init__(self, id: str, name: str, description: str = None, category: str = None, status: str = "active"):
        self.id = id
        self.name = name
        self.description = description
        self.category = category
        self.status = status
        self.created_at = datetime.utcnow()
    
    def dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "status": self.status,
            "created_at": self.created_at
        }

class Presenter:
    def __init__(self, id: str, name: str, bio: str = None, gender: str = None, country: str = None, city: str = None):
        self.id = id
        self.name = name
        self.bio = bio
        self.gender = gender
        self.country = country
        self.city = city
        self.created_at = datetime.utcnow()
    
    def dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "bio": self.bio,
            "gender": self.gender,
            "country": self.country,
            "city": self.city,
            "created_at": self.created_at
        }

class Writer:
    def __init__(self, id: str, name: str, model: str = "Mock", capabilities: str = ""):
        self.id = id
        self.name = name
        self.model = model
        self.capabilities = capabilities
        self.created_at = datetime.utcnow()
    
    def dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "model": self.model,
            "capabilities": self.capabilities,
            "created_at": self.created_at
        }

class NewsFeed:
    def __init__(self, id: str, source_url: str, name: str = None, type: str = "RSS", is_active: bool = True):
        self.id = id
        self.source_url = source_url
        self.name = name
        self.type = type
        self.is_active = is_active
        self.created_at = datetime.utcnow()
    
    def dict(self):
        return {
            "id": self.id,
            "source_url": self.source_url,
            "name": self.name,
            "type": self.type,
            "is_active": self.is_active,
            "created_at": self.created_at
        }

class Episode:
    def __init__(self, id: str, group_id: str, script: str = None, status: str = "draft"):
        self.id = id
        self.group_id = group_id
        self.script = script
        self.status = status
        self.created_at = datetime.utcnow()
    
    def dict(self):
        return {
            "id": self.id,
            "group_id": self.group_id,
            "script": self.script,
            "status": self.status,
            "created_at": self.created_at
        }

# Pydantic schemas
class PresenterCreate(BaseModel):
    name: str
    bio: Optional[str] = None
    gender: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None

class WriterCreate(BaseModel):
    name: str
    capabilities: Optional[List[str]] = None

class NewsFeedCreate(BaseModel):
    source_url: str
    name: Optional[str] = None
    type: str = "RSS"
    is_active: bool = True

class PodcastGroupCreate(BaseModel):
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    presenter_ids: List[str] = []
    writer_id: str
    news_feed_ids: List[str] = []

class GenerationRequest(BaseModel):
    group_id: str
    force_regenerate: bool = False

class GenerationResponse(BaseModel):
    episode_id: str
    status: str
    message: str

# Service URLs for simplified services
SERVICE_URLS = {
    "news-feed": "http://localhost:8001",
    "text-generation": "http://localhost:8002", 
    "writer": "http://localhost:8003",
    "presenter": "http://localhost:8004",
    "publishing": "http://localhost:8005",
    "podcast-host": "http://localhost:8006"
}

# No database needed for simplified version

async def call_service(service_name: str, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
    """Make HTTP request to a microservice."""
    if service_name not in SERVICE_URLS:
        raise HTTPException(status_code=400, detail=f"Unknown service: {service_name}")
    
    url = f"{SERVICE_URLS[service_name]}{endpoint}"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Service communication error: {str(e)}")

@app.on_event("startup")
async def startup_event():
    """Initialize the service."""
    logger.info("API Gateway (Simple) started")

@app.get("/health")
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
    
    # Mock database status
    services_status["database"] = "healthy (in-memory)"
    
    overall_status = "healthy" if all("error" not in status for status in services_status.values()) else "degraded"
    
    return {
        "status": overall_status,
        "timestamp": datetime.utcnow(),
        "services": services_status
    }

@app.get("/", response_class=HTMLResponse)
async def admin_dashboard():
    """Admin dashboard home page."""
    
    total_groups = len(podcast_groups)
    active_groups = len([g for g in podcast_groups if g.status == "active"])
    total_episodes = len(episodes)
    
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Podcast AI - Admin Dashboard</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        .stats {{ display: flex; gap: 20px; margin: 20px 0; }}
        .stat {{ background: #f0f0f0; padding: 20px; border-radius: 5px; }}
        .stat h3 {{ margin-top: 0; }}
    </style>
</head>
<body>
    <h1>Podcast AI - Admin Dashboard</h1>
    
    <div class="stats">
        <div class="stat">
            <h3>Total Groups</h3>
            <p>{total_groups}</p>
        </div>
        <div class="stat">
            <h3>Active Groups</h3>
            <p>{active_groups}</p>
        </div>
        <div class="stat">
            <h3>Total Episodes</h3>
            <p>{total_episodes}</p>
        </div>
    </div>
    
    <h2>System Status</h2>
    <p><a href="/health">Check System Health</a></p>
    
    <h2>API Endpoints</h2>
    <ul>
        <li><a href="/api/presenters">List Presenters</a></li>
        <li><a href="/api/writers">List Writers</a></li>
        <li><a href="/api/news-feeds">List News Feeds</a></li>
        <li><a href="/api/podcast-groups">List Podcast Groups</a></li>
        <li><a href="/api/episodes">List Episodes</a></li>
    </ul>
</body>
</html>"""
    
    return html_content

@app.get("/api/presenters")
async def list_presenters():
    """List all presenters."""
    return [p.dict() for p in presenters]

@app.post("/api/presenters")
async def create_presenter(presenter_data: PresenterCreate):
    """Create a new presenter."""
    presenter = Presenter(
        id=str(uuid4()),
        name=presenter_data.name,
        bio=presenter_data.bio,
        gender=presenter_data.gender,
        country=presenter_data.country,
        city=presenter_data.city
    )
    presenters.append(presenter)
    return presenter.dict()

@app.get("/api/writers")
async def list_writers():
    """List all writers."""
    return [w.dict() for w in writers]

@app.post("/api/writers")
async def create_writer(writer_data: WriterCreate):
    """Create a new writer."""
    writer = Writer(
        id=str(uuid4()),
        name=writer_data.name,
        capabilities=",".join(writer_data.capabilities) if writer_data.capabilities else ""
    )
    writers.append(writer)
    return writer.dict()

@app.get("/api/news-feeds")
async def list_news_feeds():
    """List all news feeds."""
    return [f.dict() for f in news_feeds]

@app.post("/api/news-feeds")
async def create_news_feed(feed_data: NewsFeedCreate):
    """Create a new news feed."""
    # Forward to news-feed service
    return await call_service("news-feed", "POST", "/feeds", json=feed_data.dict())

@app.get("/api/podcast-groups")
async def list_podcast_groups():
    """List all podcast groups."""
    return [g.dict() for g in podcast_groups]

@app.post("/api/podcast-groups")
async def create_podcast_group(group_data: PodcastGroupCreate):
    """Create a new podcast group."""
    group = PodcastGroup(
        id=str(uuid4()),
        name=group_data.name,
        description=group_data.description,
        category=group_data.category
    )
    podcast_groups.append(group)
    return group.dict()

@app.post("/api/generate-episode", response_model=GenerationResponse)
async def generate_episode(request: GenerationRequest):
    """Generate a complete episode for a podcast group."""
    
    # Check if group exists
    group = None
    for g in podcast_groups:
        if g.id == request.group_id:
            group = g
            break
    
    if not group:
        raise HTTPException(status_code=404, detail="Podcast group not found")
    
    try:
        # Create episode record
        episode = Episode(
            id=str(uuid4()),
            group_id=request.group_id,
            script="Mock script content",
            status="draft"
        )
        episodes.append(episode)
        
        # Update status to indicate generation started
        episode.status = "generating"
        
        # Simulate the generation process
        # In a real implementation, this would call the AI overseer service
        
        return GenerationResponse(
            episode_id=episode.id,
            status="queued",
            message=f"Episode generation started for group {request.group_id}"
        )
        
    except Exception as e:
        logger.error(f"Error generating episode: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate episode: {str(e)}")

@app.get("/api/episodes")
async def list_episodes():
    """List episodes."""
    return [e.dict() for e in episodes[-50:]]  # Return last 50 episodes

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
