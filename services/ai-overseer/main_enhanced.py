"""
Enhanced AI Overseer Service - Central orchestrator for podcast generation.
Handles increased news volume by classifying, categorizing, and ranking news articles by importance.
Manages the complete workflow from feed processing to final MP3 generation.
"""
import logging
import asyncio
import httpx
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session

from shared.database import get_db, create_tables
from shared.models import PodcastGroup, Episode, EpisodeStatus, Article, NewsFeed, Presenter

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Overseer Service (Enhanced)", version="1.0.0")

# Service URLs
REVIEWER_SERVICE_URL = "http://reviewer:8007"
PRESENTER_SERVICE_URL = "http://presenter:8008"
WRITER_SERVICE_URL = "http://writer:8010"
EDITOR_SERVICE_URL = "http://editor:8009"
COLLECTIONS_SERVICE_URL = "http://collections:8011"
NEWS_FEED_SERVICE_URL = "http://news-feed:8001"
PRESENTER_AUDIO_SERVICE_URL = "http://presenter:8004"


class FeedProcessingRequest(BaseModel):
    """Request to process feeds for a podcast group."""
    group_id: UUID
    max_articles_per_feed: int = 5


class CollectionProcessingRequest(BaseModel):
    """Request to process a collection."""
    collection_id: str
    group_id: UUID


class EpisodeGenerationRequest(BaseModel):
    """Request to generate a complete episode."""
    group_id: UUID
    target_length_minutes: int = 10
    force_generation: bool = False


class EpisodeGenerationResponse(BaseModel):
    """Response from episode generation."""
    episode_id: UUID
    status: str
    message: str
    processing_steps: List[Dict[str, Any]]


class WorkflowOrchestrator:
    """Handles the complete podcast generation workflow."""
    
    def __init__(self):
        self.http_client = httpx.AsyncClient(timeout=300.0)
    
    async def process_feeds_for_group(self, group_id: UUID, max_articles: int = 5) -> Dict[str, Any]:
        """Process feeds for a podcast group."""
        logger.info(f"Processing feeds for group {group_id}")
        
        try:
            # Get recent articles from news feeds
            response = await self.http_client.get(
                f"{NEWS_FEED_SERVICE_URL}/articles/recent",
                params={"hours": 24, "limit": max_articles * 10}
            )
            response.raise_for_status()
            articles = response.json()
            
            # Send articles to reviewer for classification
            review_results = []
            for article in articles[:max_articles * 5]:  # Limit processing
                try:
                    review_response = await self.http_client.post(
                        f"{REVIEWER_SERVICE_URL}/review-article",
                        json={"article_id": article["id"], "force_review": False}
                    )
                    if review_response.status_code == 200:
                        review_results.append(review_response.json())
                except Exception as e:
                    logger.warning(f"Failed to review article {article['id']}: {e}")
            
            logger.info(f"Processed {len(review_results)} articles for group {group_id}")
            return {
                "group_id": str(group_id),
                "articles_processed": len(articles),
                "reviews_completed": len(review_results),
                "review_results": review_results
            }
            
        except Exception as e:
            logger.error(f"Error processing feeds for group {group_id}: {e}")
            raise
    
    async def create_collection_from_reviews(
        self, 
        group_id: UUID, 
        review_results: List[Dict[str, Any]]
    ) -> str:
        """Create a collection from review results."""
        logger.info(f"Creating collection for group {group_id}")
        
        try:
            # Create collection
            collection_response = await self.http_client.post(
                f"{COLLECTIONS_SERVICE_URL}/collections",
                json={
                    "group_id": str(group_id),
                    "name": f"Collection {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
                    "description": f"Auto-generated collection for group {group_id}"
                }
            )
            collection_response.raise_for_status()
            collection = collection_response.json()
            
            # Add feed items to collection
            for review in review_results:
                await self.http_client.post(
                    f"{COLLECTIONS_SERVICE_URL}/collections/{collection['collection_id']}/items",
                    json={
                        "item_type": "feed",
                        "content": review["review"],
                        "metadata": {"source": "ai_overseer"}
                    }
                )
            
            # Add review items to collection
            for review in review_results:
                await self.http_client.post(
                    f"{COLLECTIONS_SERVICE_URL}/collections/{collection['collection_id']}/items",
                    json={
                        "item_type": "review",
                        "content": review["review"],
                        "metadata": {"source": "reviewer_service"}
                    }
                )
            
            logger.info(f"Created collection {collection['collection_id']} with {len(review_results)} items")
            return collection["collection_id"]
            
        except Exception as e:
            logger.error(f"Error creating collection for group {group_id}: {e}")
            raise
    
    async def generate_presenter_briefs(self, collection_id: str, group_id: UUID) -> List[Dict[str, Any]]:
        """Generate presenter briefs for a collection."""
        logger.info(f"Generating presenter briefs for collection {collection_id}")
        
        try:
            # Get collection details
            collection_response = await self.http_client.get(
                f"{COLLECTIONS_SERVICE_URL}/collections/{collection_id}"
            )
            collection_response.raise_for_status()
            collection = collection_response.json()
            
            # Get presenters for the group (mock for now)
            presenters = [
                {
                    "id": "00000000-0000-0000-0000-000000000001",
                    "name": "Alex Chen",
                    "bio": "Tech-savvy financial analyst",
                    "expertise": ["Technology", "Finance", "AI"]
                }
            ]
            
            # Generate briefs from each presenter
            briefs = []
            for presenter in presenters:
                try:
                    # Prepare articles for brief generation
                    articles = [
                        item["content"] for item in collection["items"] 
                        if item["item_type"] == "feed"
                    ]
                    
                    brief_response = await self.http_client.post(
                        f"{PRESENTER_SERVICE_URL}/generate-brief",
                        json={
                            "presenter_id": presenter["id"],
                            "collection_id": collection_id,
                            "articles": articles
                        }
                    )
                    
                    if brief_response.status_code == 200:
                        brief_data = brief_response.json()
                        briefs.append(brief_data)
                        
                        # Add brief to collection
                        await self.http_client.post(
                            f"{COLLECTIONS_SERVICE_URL}/collections/{collection_id}/items",
                            json={
                                "item_type": "brief",
                                "content": brief_data,
                                "metadata": {"presenter_id": presenter["id"]}
                            }
                        )
                        
                except Exception as e:
                    logger.warning(f"Failed to generate brief for presenter {presenter['id']}: {e}")
            
            logger.info(f"Generated {len(briefs)} presenter briefs for collection {collection_id}")
            return briefs
            
        except Exception as e:
            logger.error(f"Error generating presenter briefs for collection {collection_id}: {e}")
            raise
    
    async def generate_script(self, collection_id: str, group_id: UUID) -> Dict[str, Any]:
        """Generate script from collection."""
        logger.info(f"Generating script for collection {collection_id}")
        
        try:
            # Get collection details
            collection_response = await self.http_client.get(
                f"{COLLECTIONS_SERVICE_URL}/collections/{collection_id}"
            )
            collection_response.raise_for_status()
            collection = collection_response.json()
            
            # Prepare collection data for script generation
            feeds = [item["content"] for item in collection["items"] if item["item_type"] == "feed"]
            reviews = [item["content"] for item in collection["items"] if item["item_type"] == "review"]
            briefs = [item["content"] for item in collection["items"] if item["item_type"] == "brief"]
            
            collection_data = {
                "collection_id": collection_id,
                "feeds": feeds,
                "reviewer_summaries": reviews,
                "presenter_briefs": briefs,
                "target_length_minutes": 10
            }
            
            # Generate script
            script_response = await self.http_client.post(
                f"{WRITER_SERVICE_URL}/generate-script",
                json={
                    "episode_id": str(uuid4()),
                    "group_id": str(group_id),
                    "collection": collection_data,
                    "style_preferences": {"tone": "conversational", "pacing": "moderate"}
                }
            )
            script_response.raise_for_status()
            script_data = script_response.json()
            
            # Add script to collection
            await self.http_client.post(
                f"{COLLECTIONS_SERVICE_URL}/collections/{collection_id}/items",
                json={
                    "item_type": "script",
                    "content": script_data,
                    "metadata": {"generated_by": "writer_service"}
                }
            )
            
            logger.info(f"Generated script for collection {collection_id}")
            return script_data
            
        except Exception as e:
            logger.error(f"Error generating script for collection {collection_id}: {e}")
            raise
    
    async def edit_script(self, collection_id: str, script_data: Dict[str, Any]) -> Dict[str, Any]:
        """Edit and polish script."""
        logger.info(f"Editing script for collection {collection_id}")
        
        try:
            # Prepare collection context
            collection_response = await self.http_client.get(
                f"{COLLECTIONS_SERVICE_URL}/collections/{collection_id}"
            )
            collection_response.raise_for_status()
            collection = collection_response.json()
            
            collection_context = {
                "topic": "General News",
                "subject": "Current Events",
                "article_count": len([item for item in collection["items"] if item["item_type"] == "feed"]),
                "themes": ["news", "analysis", "current events"]
            }
            
            # Edit script
            edit_response = await self.http_client.post(
                f"{EDITOR_SERVICE_URL}/edit-script",
                json={
                    "script_id": f"script-{collection_id}",
                    "script": script_data["script"],
                    "collection_context": collection_context,
                    "target_length_minutes": 10,
                    "target_audience": "general"
                }
            )
            edit_response.raise_for_status()
            edit_data = edit_response.json()
            
            # Add edited script to collection
            await self.http_client.post(
                f"{COLLECTIONS_SERVICE_URL}/collections/{collection_id}/items",
                json={
                    "item_type": "edited_script",
                    "content": edit_data,
                    "metadata": {"edited_by": "editor_service"}
                }
            )
            
            logger.info(f"Edited script for collection {collection_id}")
            return edit_data
            
        except Exception as e:
            logger.error(f"Error editing script for collection {collection_id}: {e}")
            raise
    
    async def generate_audio(self, collection_id: str, script_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate MP3 audio from script."""
        logger.info(f"Generating audio for collection {collection_id}")
        
        try:
            # Use the edited script if available, otherwise use original
            script_text = script_data.get("review", {}).get("edited_script", script_data["script"])
            
            # Generate audio
            audio_response = await self.http_client.post(
                f"{PRESENTER_AUDIO_SERVICE_URL}/generate-audio",
                json={
                    "episode_id": uuid4(),
                    "script": script_text,
                    "presenter_ids": ["00000000-0000-0000-0000-000000000001"],
                    "voice_settings": {"format": "mp3", "quality": "high"}
                }
            )
            audio_response.raise_for_status()
            audio_data = audio_response.json()
            
            logger.info(f"Generated audio for collection {collection_id}")
            return audio_data
            
        except Exception as e:
            logger.error(f"Error generating audio for collection {collection_id}: {e}")
            raise
    
    async def generate_complete_episode(self, request: EpisodeGenerationRequest) -> EpisodeGenerationResponse:
        """Generate a complete episode following the workflow."""
        logger.info(f"Generating complete episode for group {request.group_id}")
        
        processing_steps = []
        episode_id = uuid4()
        
        try:
            # Step 1: Process feeds
            step1 = {"step": "feed_processing", "status": "started", "timestamp": datetime.utcnow().isoformat()}
            processing_steps.append(step1)
            
            feed_results = await self.process_feeds_for_group(request.group_id)
            step1["status"] = "completed"
            step1["result"] = feed_results
            processing_steps.append(step1)
            
            # Step 2: Create collection
            step2 = {"step": "collection_creation", "status": "started", "timestamp": datetime.utcnow().isoformat()}
            processing_steps.append(step2)
            
            collection_id = await self.create_collection_from_reviews(
                request.group_id, feed_results["review_results"]
            )
            step2["status"] = "completed"
            step2["result"] = {"collection_id": collection_id}
            processing_steps.append(step2)
            
            # Step 3: Generate presenter briefs
            step3 = {"step": "presenter_briefs", "status": "started", "timestamp": datetime.utcnow().isoformat()}
            processing_steps.append(step3)
            
            briefs = await self.generate_presenter_briefs(collection_id, request.group_id)
            step3["status"] = "completed"
            step3["result"] = {"briefs_count": len(briefs)}
            processing_steps.append(step3)
            
            # Step 4: Generate script
            step4 = {"step": "script_generation", "status": "started", "timestamp": datetime.utcnow().isoformat()}
            processing_steps.append(step4)
            
            script_data = await self.generate_script(collection_id, request.group_id)
            step4["status"] = "completed"
            step4["result"] = {"script_length": len(script_data["script"].split())}
            processing_steps.append(step4)
            
            # Step 5: Edit script
            step5 = {"step": "script_editing", "status": "started", "timestamp": datetime.utcnow().isoformat()}
            processing_steps.append(step5)
            
            edit_data = await self.edit_script(collection_id, script_data)
            step5["status"] = "completed"
            step5["result"] = {"edited_script_length": len(edit_data["review"]["edited_script"].split())}
            processing_steps.append(step5)
            
            # Step 6: Generate audio
            step6 = {"step": "audio_generation", "status": "started", "timestamp": datetime.utcnow().isoformat()}
            processing_steps.append(step6)
            
            audio_data = await self.generate_audio(collection_id, edit_data)
            step6["status"] = "completed"
            step6["result"] = {
                "audio_url": audio_data["audio_url"],
                "duration_seconds": audio_data["duration_seconds"],
                "file_size_bytes": audio_data["file_size_bytes"]
            }
            processing_steps.append(step6)
            
            logger.info(f"Successfully generated complete episode {episode_id}")
            
            return EpisodeGenerationResponse(
                episode_id=episode_id,
                status="completed",
                message="Episode generated successfully",
                processing_steps=processing_steps
            )
            
        except Exception as e:
            logger.error(f"Error generating episode for group {request.group_id}: {e}")
            return EpisodeGenerationResponse(
                episode_id=episode_id,
                status="failed",
                message=f"Episode generation failed: {str(e)}",
                processing_steps=processing_steps
            )


# Initialize services
workflow_orchestrator = WorkflowOrchestrator()

# Create tables on startup
@app.on_event("startup")
async def startup_event():
    create_tables()
    logger.info("AI Overseer Service (Enhanced) started")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "ai-overseer-enhanced", "timestamp": datetime.utcnow()}


@app.post("/process-feeds", response_model=Dict[str, Any])
async def process_feeds(request: FeedProcessingRequest):
    """Process feeds for a podcast group."""
    try:
        result = await workflow_orchestrator.process_feeds_for_group(
            request.group_id, request.max_articles_per_feed
        )
        return result
    except Exception as e:
        logger.error(f"Error processing feeds: {e}")
        raise HTTPException(status_code=500, detail=f"Feed processing failed: {str(e)}")


@app.post("/generate-episode", response_model=EpisodeGenerationResponse)
async def generate_episode(request: EpisodeGenerationRequest):
    """Generate a complete episode following the full workflow."""
    try:
        result = await workflow_orchestrator.generate_complete_episode(request)
        return result
    except Exception as e:
        logger.error(f"Error generating episode: {e}")
        raise HTTPException(status_code=500, detail=f"Episode generation failed: {str(e)}")


@app.post("/test-complete-workflow")
async def test_complete_workflow(
    group_name: str = "Test Podcast Group",
    target_length_minutes: int = 10
):
    """Test the complete workflow to generate a 10-minute podcast."""
    
    try:
        # Create test request
        test_request = EpisodeGenerationRequest(
            group_id=UUID("00000000-0000-0000-0000-000000000001"),
            target_length_minutes=target_length_minutes,
            force_generation=True
        )
        
        # Generate complete episode
        result = await workflow_orchestrator.generate_complete_episode(test_request)
        
        return {
            "test_parameters": {
                "group_name": group_name,
                "target_length_minutes": target_length_minutes
            },
            "generation_result": result.dict(),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in test complete workflow: {e}")
        raise HTTPException(status_code=500, detail=f"Test workflow failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8012)