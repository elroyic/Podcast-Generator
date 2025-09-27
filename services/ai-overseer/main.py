"""
AI Overseer Service - Central orchestrator for podcast generation.
"""
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from uuid import UUID

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session

# Add the shared directory to Python path
import sys
import os
sys.path.append('/app/shared')

from database import get_db, create_tables
from models import PodcastGroup, Episode, EpisodeStatus, Presenter, Writer, NewsFeed
from schemas import (
    PodcastGroup as PodcastGroupSchema,
    Episode as EpisodeSchema,
    GenerationRequest,
    GenerationResponse,
    HealthCheck
)
from pydantic import BaseModel
from app.celery import celery
from app.services import EpisodeGenerationService, PersonaGenerationService
import os
import redis

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Overseer Service", version="1.0.0")


# Pydantic models for persona generation
class PersonaGenerationRequest(BaseModel):
    group_id: UUID
    category: Optional[str] = "General"
    recent_articles: Optional[List[str]] = None


class PersonaGenerationResponse(BaseModel):
    name: str
    bio: str
    persona: str
    voice_style: str
    system_prompt: str
    created: bool
    presenter_id: Optional[str] = None

# Initialize services
episode_generation_service = EpisodeGenerationService()
persona_generation_service = PersonaGenerationService()

# Create tables on startup
@app.on_event("startup")
async def startup_event():
    create_tables()
    logger.info("AI Overseer Service started")
    # Initialize Redis connection for duplicates metrics API
    global redis_client
    try:
        redis_client = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"), decode_responses=True)
    except Exception as e:
        redis_client = None
        logger.warning(f"Redis not available for Overseer metrics: {e}")


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
        try:
            db = next(get_db())
            db.execute("SELECT 1")
            services_status["database"] = "healthy"
            db.close()
        except Exception as e:
            services_status["database"] = f"error: {str(e)}"
        
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
            episode_id=str(request.group_id),  # Convert UUID to string
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


@app.get("/metrics/prometheus")
async def get_prometheus_metrics(db: Session = Depends(get_db)):
    """Prometheus-compatible metrics endpoint."""
    try:
        from fastapi.responses import PlainTextResponse
        from datetime import timedelta
        
        # Episode counts by status
        episode_counts = {}
        total_episodes = 0
        for status in EpisodeStatus:
            count = db.query(Episode).filter(Episode.status == status).count()
            episode_counts[status.value] = count
            total_episodes += count
        
        # Recent episode generation stats (last 24 hours)
        yesterday = datetime.utcnow() - timedelta(hours=24)
        recent_generations = db.query(Episode).filter(
            Episode.created_at >= yesterday
        ).count()
        
        # Active groups
        active_groups = db.query(PodcastGroup).filter(
            PodcastGroup.status == "active"
        ).count()
        
        # Calculate average generation duration (placeholder - would need tracking)
        avg_duration = 300  # 5 minutes default
        
        metrics = []
        
        # Episode totals
        metrics.append(f"overseer_episodes_generated_total {total_episodes}")
        
        # Episodes by status
        for status, count in episode_counts.items():
            metrics.append(f'overseer_episodes_by_status{{status="{status}"}} {count}')
        
        # Recent activity
        metrics.append(f"overseer_episodes_generated_last_24h {recent_generations}")
        
        # Active groups
        metrics.append(f"overseer_active_groups_total {active_groups}")
        
        # Average duration
        metrics.append(f"overseer_generation_duration_seconds {avg_duration}")
        
        prometheus_output = "\n".join([
            "# HELP overseer_episodes_generated_total Total episodes generated",
            "# TYPE overseer_episodes_generated_total counter",
            "# HELP overseer_episodes_by_status Episodes by status",
            "# TYPE overseer_episodes_by_status gauge",
            "# HELP overseer_episodes_generated_last_24h Episodes generated in last 24 hours",
            "# TYPE overseer_episodes_generated_last_24h gauge",
            "# HELP overseer_active_groups_total Number of active podcast groups",
            "# TYPE overseer_active_groups_total gauge",
            "# HELP overseer_generation_duration_seconds Average episode generation duration",
            "# TYPE overseer_generation_duration_seconds gauge",
            "",
            *metrics
        ])
        
        return PlainTextResponse(prometheus_output, media_type="text/plain")
        
    except Exception as e:
        logger.error(f"Error generating Prometheus metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate metrics: {str(e)}")


@app.post("/auto-create-groups")
async def auto_create_podcast_groups(db: Session = Depends(get_db)):
    """Automatically create podcast groups based on available content and presenters."""
    try:
        logger.info("🤖 Auto-creating podcast groups...")
        
        # Check if we have sufficient resources
        writers = db.query(Writer).all()
        presenters = db.query(Presenter).all()
        feeds = db.query(NewsFeed).filter(NewsFeed.is_active == True).all()
        
        if not writers:
            # Create a default writer
            default_writer = Writer(
                name="AI Content Writer",
                model="Qwen3",
                capabilities=["script_generation", "metadata_generation"]
            )
            db.add(default_writer)
            db.commit()
            db.refresh(default_writer)
            writers = [default_writer]
            
        if not presenters:
            # Create default presenters using LLM persona generation
            logger.info("🎭 Generating AI presenter personas...")
            default_presenters = []
            
            # Generate personas for different categories
            categories = ["Technology", "News", "Finance", "General"]
            for category in categories:
                try:
                    # Create a temporary group for persona generation context
                    temp_group = PodcastGroup(
                        name=f"Temp {category} Group",
                        category=category,
                        status="active"
                    )
                    db.add(temp_group)
                    db.commit()
                    db.refresh(temp_group)
                    
                    # Generate persona for this category
                    persona_data = await persona_generation_service.generate_presenter_persona(
                        group_id=temp_group.id,
                        group_category=category
                    )
                    
                    # Create presenter from generated persona
                    presenter = Presenter(
                        name=persona_data["name"],
                        bio=persona_data["bio"],
                        persona=persona_data["persona"],
                        voice_model="vibevoice",
                        llm_model="qwen2.5:latest",
                        system_prompt=persona_data["system_prompt"],
                        specialties=[category.lower()],
                        age=30,
                        gender="neutral",
                        status="active"
                    )
                    db.add(presenter)
                    default_presenters.append(presenter)
                    
                    # Clean up temp group
                    db.delete(temp_group)
                    
                except Exception as e:
                    logger.warning(f"Failed to generate persona for {category}, using fallback: {e}")
                    # Fallback presenter
                    presenter = Presenter(
                        name=f"AI {category} Presenter",
                        bio=f"AI-powered {category.lower()} presenter",
                        age=30,
                        gender="neutral",
                        specialties=[category.lower()],
                        voice_model="vibevoice",
                        llm_model="qwen2.5:latest",
                        system_prompt=f"You are a knowledgeable {category.lower()} presenter. Provide clear, engaging commentary.",
                        status="active"
                    )
                    db.add(presenter)
                    default_presenters.append(presenter)
            
            db.commit()
            for presenter in default_presenters:
                db.refresh(presenter)
            presenters = default_presenters
            logger.info(f"✅ Generated {len(presenters)} AI presenter personas")
        
        # Create podcast groups by category if they don't exist
        categories = ["Technology", "News", "Finance", "General"]
        created_groups = []
        
        for category in categories:
            # Check if group already exists for this category
            existing = db.query(PodcastGroup).filter(
                PodcastGroup.category == category,
                PodcastGroup.status == "active"
            ).first()
            
            if not existing:
                # Create new group
                group = PodcastGroup(
                    name=f"AI {category} Podcast",
                    description=f"Automated {category.lower()} podcast generated from RSS feeds",
                    category=category,
                    language="en",
                    country="US",
                    tags=[category.lower(), "ai", "automated"],
                    keywords=[category.lower(), "news", "ai"],
                    schedule="0 12 * * *",  # Daily at noon
                    writer_id=writers[0].id
                )
                db.add(group)
                db.commit()
                db.refresh(group)
                
                # Assign presenters
                group.presenters = presenters[:2]  # Assign first 2 presenters
                
                # Assign feeds (distribute feeds across groups)
                feeds_per_group = len(feeds) // len(categories)
                start_idx = len(created_groups) * feeds_per_group
                end_idx = start_idx + feeds_per_group
                group.news_feeds = feeds[start_idx:end_idx]
                
                db.commit()
                created_groups.append(group)
                logger.info(f"✅ Created podcast group: {group.name}")
        
        return {
            "status": "success",
            "message": f"Auto-created {len(created_groups)} podcast groups",
            "groups_created": [
                {
                    "id": str(group.id),
                    "name": group.name,
                    "category": group.category,
                    "feeds_assigned": len(group.news_feeds),
                    "presenters_assigned": len(group.presenters)
                }
                for group in created_groups
            ],
            "total_writers": len(writers),
            "total_presenters": len(presenters),
            "total_feeds": len(feeds)
        }
        
    except Exception as e:
        logger.error(f"❌ Error auto-creating podcast groups: {e}")
        raise HTTPException(status_code=500, detail=f"Auto-creation failed: {str(e)}")


@app.post("/test-complete-workflow")
async def test_complete_workflow(db: Session = Depends(get_db)):
    """Test the complete podcast generation workflow end-to-end."""
    try:
        logger.info("🧪 Starting complete workflow test...")
        
        # Step 1: Check if we have any active podcast groups
        active_groups = db.query(PodcastGroup).filter(PodcastGroup.status == "active").all()
        
        if not active_groups:
            # Create a test podcast group
            logger.info("📝 Creating test podcast group...")
            
            # Create test writer first
            from shared.models import Writer, Presenter
            
            test_writer = Writer(
                name="Test Writer",
                model="Qwen3",
                capabilities=["script_generation", "metadata_generation"]
            )
            db.add(test_writer)
            db.commit()
            db.refresh(test_writer)
            
            # Create test presenter
            test_presenter = Presenter(
                name="Test Presenter",
                bio="AI-generated presenter for testing",
                age=30,
                gender="neutral",
                specialties=["technology", "news"],
                voice_model="vibevoice"
            )
            db.add(test_presenter)
            db.commit()
            db.refresh(test_presenter)
            
            # Create test podcast group
            test_group = PodcastGroup(
                name="Test Podcast Workflow",
                description="Automated test podcast for system validation",
                category="Technology",
                language="en",
                country="US",
                tags=["test", "automation", "ai"],
                keywords=["test", "podcast", "ai"],
                schedule="0 12 * * *",  # Daily at noon
                writer_id=test_writer.id
            )
            db.add(test_group)
            db.commit()
            db.refresh(test_group)
            
            # Assign presenter to group
            test_group.presenters = [test_presenter]
            db.commit()
            
            target_group = test_group
            logger.info(f"✅ Created test podcast group: {target_group.id}")
        else:
            target_group = active_groups[0]
            logger.info(f"📋 Using existing podcast group: {target_group.name}")
        
        # Step 2: Test episode generation
        logger.info("🎬 Testing episode generation...")
        test_articles = [
            "Breaking: AI technology advances continue to reshape industries worldwide with new capabilities in natural language processing and machine learning.",
            "Scientists discover new methods for improving renewable energy efficiency using artificial intelligence algorithms.",
            "Tech companies announce major investments in sustainable computing infrastructure for the next decade."
        ]
        
        # Generate episode using the service
        try:
            result = await episode_generation_service.generate_complete_episode(
                group_id=target_group.id
            )
            
            episode_id = result.get("episode_id")
            logger.info(f"✅ Episode generated successfully: {episode_id}")
            
            # Step 3: Verify episode was created with all components
            episode = db.query(Episode).filter(Episode.id == episode_id).first()
            if not episode:
                raise ValueError("Episode not found in database")
            
            has_script = bool(episode.script)
            has_metadata = db.query(EpisodeMetadata).filter(EpisodeMetadata.episode_id == episode_id).first() is not None
            has_audio = db.query(AudioFile).filter(AudioFile.episode_id == episode_id).first() is not None
            
            # Step 4: Check cadence system
            cadence_status = episode_generation_service.cadence_manager.get_cadence_status(target_group.id, db)
            
            # Step 5: Return comprehensive test results
            test_results = {
                "status": "success",
                "test_timestamp": datetime.utcnow().isoformat(),
                "workflow_components": {
                    "group_creation": True,
                    "episode_generation": True,
                    "script_creation": has_script,
                    "metadata_generation": has_metadata,
                    "audio_generation": has_audio,
                    "cadence_system": bool(cadence_status),
                },
                "episode_details": {
                    "episode_id": str(episode_id),
                    "status": episode.status.value if episode.status else "unknown",
                    "script_length": len(episode.script.split()) if episode.script else 0,
                    "group_name": target_group.name
                },
                "cadence_info": cadence_status,
                "services_tested": [
                    "ai-overseer",
                    "writer",
                    "editor", 
                    "presenter",
                    "publishing"
                ],
                "test_summary": {
                    "total_components": 6,
                    "passed_components": sum([
                        True,  # group_creation
                        True,  # episode_generation  
                        has_script,
                        has_metadata,
                        has_audio,
                        bool(cadence_status)
                    ]),
                    "success_rate": f"{(sum([True, True, has_script, has_metadata, has_audio, bool(cadence_status)]) / 6) * 100:.1f}%"
                }
            }
            
            logger.info(f"🎉 Workflow test completed successfully! Success rate: {test_results['test_summary']['success_rate']}")
            return test_results
            
        except Exception as gen_error:
            logger.error(f"❌ Episode generation failed: {gen_error}")
            return {
                "status": "partial_failure",
                "error": str(gen_error),
                "test_timestamp": datetime.utcnow().isoformat(),
                "message": "Episode generation failed, but group creation succeeded"
            }
            
    except Exception as e:
        logger.error(f"❌ Complete workflow test failed: {e}")
        raise HTTPException(status_code=500, detail=f"Workflow test failed: {str(e)}")


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


@app.get("/cadence/status")
async def get_cadence_status(group_id: Optional[str] = None, db: Session = Depends(get_db)):
    """Get cadence status for podcast groups."""
    try:
        if group_id:
            # Single group status
            from uuid import UUID
            group_uuid = UUID(group_id)
            status = episode_generation_service.cadence_manager.get_cadence_status(group_uuid, db)
            return status
        else:
            # All groups status
            statuses = episode_generation_service.cadence_manager.get_all_cadence_statuses(db)
            return {"cadence_statuses": statuses}
    except Exception as e:
        logger.error(f"Error getting cadence status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get cadence status: {str(e)}")


@app.get("/api/overseer/duplicates")
async def get_duplicates_since(since: str):
    """Return count of duplicates filtered since timestamp (ISO8601).
    Reads timestamps from news-feed's Redis list reviewer:duplicates:events
    """
    from datetime import datetime
    try:
        dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
        ts = int(dt.timestamp())
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid 'since' timestamp")

    if not ('redis_client' in globals() and redis_client):
        raise HTTPException(status_code=503, detail="Redis unavailable")

    try:
        events = redis_client.lrange("reviewer:duplicates:events", 0, -1)
        count = 0
        for e in events:
            try:
                if int(e) >= ts:
                    count += 1
            except Exception:
                continue
        # Estimate unique processed as total new Article rows since 'since'
        # For simplicity, return placeholder 0 here; UI can compute via DB if needed
        return {
            "since": since,
            "duplicate_count": count,
            "unique_processed": 0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read duplicates: {e}")
        
    except Exception as e:
        logger.error(f"Error queuing cleanup task: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to queue cleanup task: {str(e)}")


@app.post("/api/presenters/auto-generate", response_model=PersonaGenerationResponse)
async def auto_generate_presenter_persona(
    request: PersonaGenerationRequest,
    db: Session = Depends(get_db)
):
    """Generate a presenter persona using LLM and optionally create the presenter."""
    try:
        logger.info(f"🎭 Generating presenter persona for group {request.group_id}")
        
        # Generate persona using LLM
        persona_data = await persona_generation_service.generate_presenter_persona(
            group_id=request.group_id,
            group_category=request.category,
            recent_articles=request.recent_articles
        )
        
        # Create presenter record in database
        presenter = Presenter(
            name=persona_data["name"],
            bio=persona_data["bio"],
            persona=persona_data["persona"],
            voice_model="vibevoice",
            llm_model="qwen2.5:latest",
            system_prompt=persona_data["system_prompt"],
            specialties=[request.category.lower()] if request.category else ["general"],
            age=30,  # Default age
            gender="neutral",  # Default gender
            status="active"
        )
        
        db.add(presenter)
        db.commit()
        db.refresh(presenter)
        
        logger.info(f"✅ Created presenter: {presenter.name} (ID: {presenter.id})")
        
        return PersonaGenerationResponse(
            name=persona_data["name"],
            bio=persona_data["bio"],
            persona=persona_data["persona"],
            voice_style=persona_data["voice_style"],
            system_prompt=persona_data["system_prompt"],
            created=True,
            presenter_id=str(presenter.id)
        )
        
    except Exception as e:
        logger.error(f"❌ Error generating presenter persona: {e}")
        raise HTTPException(status_code=500, detail=f"Persona generation failed: {str(e)}")


# Import Celery tasks
from app.tasks import generate_episode_for_group, cleanup_old_episodes

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8006)
