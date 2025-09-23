"""
AI Overseer Service - Central orchestrator for podcast generation.
"""
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from uuid import UUID

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session

from shared.database import get_db, create_tables
from shared.models import PodcastGroup, Episode, EpisodeStatus
from shared.schemas import (
    PodcastGroup as PodcastGroupSchema,
    Episode as EpisodeSchema,
    GenerationRequest,
    GenerationResponse,
    HealthCheck
)
from app.celery import celery
from app.services import EpisodeGenerationService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Overseer Service", version="1.0.0")

# Initialize services
episode_generation_service = EpisodeGenerationService()

# Create tables on startup
@app.on_event("startup")
async def startup_event():
    create_tables()
    logger.info("AI Overseer Service started")


@app.get("/health", response_model=HealthCheck)
async def health_check():
    """Health check endpoint."""
    # Check health of other services
    services_status = {}
    
    try:
        # Check Celery workers
        inspect = celery.control.inspect()
        active_workers = inspect.active()
        services_status["celery_workers"] = f"{len(active_workers)} active" if active_workers else "no workers"
        
        # Check database
        db = next(get_db())
        db.execute("SELECT 1")
        services_status["database"] = "healthy"
        
    except Exception as e:
        services_status["database"] = f"error: {str(e)}"
    
    return HealthCheck(
        status="healthy",
        timestamp=datetime.utcnow(),
        services=services_status
    )


@app.post("/generate-episode", response_model=GenerationResponse)
async def generate_episode(
    request: GenerationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Generate a complete episode for a podcast group."""
    
    # Check if group exists and is active
    group = db.query(PodcastGroup).filter(
        PodcastGroup.id == request.group_id,
        PodcastGroup.status == "active"
    ).first()
    
    if not group:
        raise HTTPException(status_code=404, detail="Podcast group not found or inactive")
    
    try:
        # Queue the episode generation task
        task = generate_episode_for_group.delay(str(request.group_id))
        
        logger.info(f"Queued episode generation for group {request.group_id} (task: {task.id})")
        
        return GenerationResponse(
            episode_id=UUID("00000000-0000-0000-0000-000000000000"),  # Will be updated when task completes
            status="queued",
            message=f"Episode generation queued with task ID: {task.id}"
        )
        
    except Exception as e:
        logger.error(f"Error queuing episode generation: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to queue episode generation: {str(e)}")


@app.get("/episodes", response_model=List[EpisodeSchema])
async def list_episodes(
    group_id: Optional[UUID] = None,
    status: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """List episodes, optionally filtered by group and status."""
    query = db.query(Episode)
    
    if group_id:
        query = query.filter(Episode.group_id == group_id)
    
    if status:
        try:
            episode_status = EpisodeStatus(status)
            query = query.filter(Episode.status == episode_status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    
    episodes = query.order_by(Episode.created_at.desc()).limit(limit).all()
    return episodes


@app.get("/episodes/{episode_id}", response_model=EpisodeSchema)
async def get_episode(
    episode_id: UUID,
    db: Session = Depends(get_db)
):
    """Get a specific episode."""
    episode = db.query(Episode).filter(Episode.id == episode_id).first()
    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")
    return episode


@app.get("/podcast-groups", response_model=List[PodcastGroupSchema])
async def list_podcast_groups(
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    """List all podcast groups."""
    query = db.query(PodcastGroup)
    if active_only:
        query = query.filter(PodcastGroup.status == "active")
    
    return query.all()


@app.get("/podcast-groups/{group_id}", response_model=PodcastGroupSchema)
async def get_podcast_group(
    group_id: UUID,
    db: Session = Depends(get_db)
):
    """Get a specific podcast group."""
    group = db.query(PodcastGroup).filter(PodcastGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Podcast group not found")
    return group


@app.post("/podcast-groups/{group_id}/trigger")
async def trigger_group_generation(
    group_id: UUID,
    db: Session = Depends(get_db)
):
    """Manually trigger episode generation for a specific group."""
    
    # Check if group exists and is active
    group = db.query(PodcastGroup).filter(
        PodcastGroup.id == group_id,
        PodcastGroup.status == "active"
    ).first()
    
    if not group:
        raise HTTPException(status_code=404, detail="Podcast group not found or inactive")
    
    try:
        # Queue the episode generation task
        task = generate_episode_for_group.delay(str(group_id))
        
        logger.info(f"Manually triggered episode generation for group {group_id} (task: {task.id})")
        
        return {
            "status": "success",
            "message": f"Episode generation triggered for group {group_id}",
            "task_id": task.id
        }
        
    except Exception as e:
        logger.error(f"Error triggering episode generation: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to trigger episode generation: {str(e)}")


@app.get("/tasks/{task_id}/status")
async def get_task_status(task_id: str):
    """Get the status of a Celery task."""
    try:
        task = celery.AsyncResult(task_id)
        
        return {
            "task_id": task_id,
            "status": task.status,
            "result": task.result if task.ready() else None,
            "info": task.info if not task.ready() else None
        }
        
    except Exception as e:
        logger.error(f"Error getting task status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get task status: {str(e)}")


@app.get("/stats")
async def get_system_stats(db: Session = Depends(get_db)):
    """Get system statistics."""
    try:
        # Count episodes by status
        episode_counts = {}
        for status in EpisodeStatus:
            count = db.query(Episode).filter(Episode.status == status).count()
            episode_counts[status.value] = count
        
        # Count active podcast groups
        active_groups = db.query(PodcastGroup).filter(
            PodcastGroup.status == "active"
        ).count()
        
        # Get recent episode activity
        recent_episodes = db.query(Episode).order_by(
            Episode.created_at.desc()
        ).limit(10).all()
        
        return {
            "episode_counts_by_status": episode_counts,
            "active_podcast_groups": active_groups,
            "recent_episodes": [
                {
                    "id": str(ep.id),
                    "group_id": str(ep.group_id),
                    "status": ep.status.value,
                    "created_at": ep.created_at.isoformat()
                }
                for ep in recent_episodes
            ],
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting system stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get system stats: {str(e)}")


@app.post("/admin/cleanup")
async def cleanup_old_data(background_tasks: BackgroundTasks):
    """Trigger cleanup of old episodes and data."""
    try:
        # Queue cleanup task
        task = cleanup_old_episodes.delay()
        
        return {
            "status": "success",
            "message": "Cleanup task queued",
            "task_id": task.id
        }
        
    except Exception as e:
        logger.error(f"Error queuing cleanup task: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to queue cleanup task: {str(e)}")


# Import Celery tasks
from app.tasks import generate_episode_for_group, cleanup_old_episodes

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8006)
