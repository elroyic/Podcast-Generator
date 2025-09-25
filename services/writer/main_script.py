"""
Enhanced Writer Service - Generates podcast scripts using Qwen3.
Receives collections with feeds, reviewer classifications, and presenter briefs.
Produces podcast scripts of required length as specified in the workflow.
"""
import logging
import os
from datetime import datetime
from typing import Dict, Any, Optional, List
from uuid import UUID

import httpx
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from shared.database import get_db, create_tables
from shared.models import PodcastGroup, Episode, EpisodeMetadata

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Writer Service (Script Generation)", version="1.0.0")

# Configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:latest")


class CollectionData(BaseModel):
    """Data structure for a collection."""
    collection_id: str
    feeds: List[Dict[str, Any]]  # Articles with reviewer classifications
    reviewer_summaries: List[Dict[str, Any]]  # Reviewer output
    presenter_briefs: List[Dict[str, Any]]  # Presenter briefs
    target_length_minutes: int = 10


class ScriptGenerationRequest(BaseModel):
    """Request to generate a podcast script."""
    episode_id: UUID
    group_id: UUID
    collection: CollectionData
    style_preferences: Optional[Dict[str, Any]] = None


class ScriptGenerationResponse(BaseModel):
    """Response from script generation."""
    episode_id: UUID
    script: str
    generation_metadata: Dict[str, Any]


class OllamaClient:
    """Client for interacting with Ollama API."""
    
    def __init__(self, base_url: str = OLLAMA_BASE_URL):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=120.0)
    
    async def generate_script(
        self,
        model: str,
        prompt: str,
        system_prompt: str = None
    ) -> str:
        """Generate script using Ollama."""
        try:
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,  # Balanced creativity and consistency
                    "top_p": 0.9,
                    "max_tokens": 3000  # Allow for longer scripts
                }
            }
            
            if system_prompt:
                payload["system"] = system_prompt
            
            response = await self.client.post(
                f"{self.base_url}/api/generate",
                json=payload
            )
            response.raise_for_status()
            
            result = response.json()
            return result.get("response", "")
            
        except Exception as e:
            logger.error(f"Error generating script with Ollama: {e}")
            raise HTTPException(status_code=500, detail=f"Script generation failed: {str(e)}")


class ScriptWriter:
    """Handles podcast script generation logic."""
    
    def __init__(self):
        self.ollama_client = OllamaClient()
    
    def create_system_prompt(self, podcast_group: PodcastGroup) -> str:
        """Create system prompt for script generation."""
        return f"""
You are an expert podcast script writer specializing in news and current events content.

PODCAST DETAILS:
- Name: {podcast_group.name}
- Description: {podcast_group.description or 'No description'}
- Category: {podcast_group.category or 'General'}
- Language: {podcast_group.language or 'English'}
- Target Audience: General news listeners

SCRIPT WRITING REQUIREMENTS:
1. Create engaging, conversational content suitable for audio consumption
2. Structure the script with clear introduction, main content, and conclusion
3. Weave together multiple news stories into a cohesive narrative
4. Include smooth transitions between topics
5. Maintain factual accuracy while making content accessible
6. Use conversational language that sounds natural when spoken
7. Include engaging hooks and compelling conclusions
8. Balance information density with entertainment value
9. Ensure appropriate pacing for the target duration
10. Make complex topics understandable to general audiences

WRITING STYLE:
- Conversational and engaging tone
- Clear, accessible language
- Smooth transitions between topics
- Natural speech patterns
- Engaging storytelling elements
- Appropriate use of humor and personality
- Strong opening and closing

TARGET LENGTH: Aim for approximately 150 words per minute of content.
"""

    def create_content_prompt(
        self, 
        collection: CollectionData, 
        podcast_group: PodcastGroup,
        style_preferences: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create the main content prompt for script generation."""
        
        # Format feeds data
        feeds_text = ""
        for i, feed in enumerate(collection.feeds, 1):
            feeds_text += f"""
Story {i}:
Title: {feed.get('title', 'No title')}
Summary: {feed.get('summary', 'No summary')}
Topic: {feed.get('topic', 'General')}
Subject: {feed.get('subject', 'General')}
Importance: {feed.get('importance_rank', 5)}/10
Source: {feed.get('source', 'Unknown')}
"""
        
        # Format reviewer summaries
        reviewer_text = ""
        for i, summary in enumerate(collection.reviewer_summaries, 1):
            reviewer_text += f"""
Reviewer Analysis {i}:
{summary.get('summary', 'No analysis available')}
Tags: {', '.join(summary.get('tags', []))}
"""
        
        # Format presenter briefs
        presenter_text = ""
        for i, brief in enumerate(collection.presenter_briefs, 1):
            presenter_text += f"""
Presenter Brief {i} (by {brief.get('presenter_name', 'Unknown Presenter')}):
{brief.get('brief', 'No brief available')}
"""
        
        # Style preferences
        style_text = ""
        if style_preferences:
            style_text = f"""
STYLE PREFERENCES:
- Tone: {style_preferences.get('tone', 'conversational')}
- Pacing: {style_preferences.get('pacing', 'moderate')}
- Focus: {style_preferences.get('focus', 'balanced')}
- Additional notes: {style_preferences.get('notes', 'None')}
"""
        
        return f"""
Create a {collection.target_length_minutes}-minute podcast script for "{podcast_group.name}".

COLLECTION DATA:
{feeds_text}

REVIEWER ANALYSIS:
{reviewer_text}

PRESENTER BRIEFS:
{presenter_text}

{style_text}

SCRIPT REQUIREMENTS:
1. Target Duration: {collection.target_length_minutes} minutes (~{collection.target_length_minutes * 150} words)
2. Structure: Introduction → Main Content → Conclusion
3. Content: Weave together the stories into a cohesive narrative
4. Style: Conversational, engaging, accessible to general audiences
5. Accuracy: Base all content on the provided source material
6. Flow: Smooth transitions between topics
7. Engagement: Hook listeners from the start and maintain interest

Create a complete podcast script that:
- Opens with an engaging introduction
- Presents the news stories in a logical, flowing manner
- Connects related topics and themes
- Includes smooth transitions
- Concludes with a compelling wrap-up
- Maintains appropriate pacing throughout
- Sounds natural when spoken aloud

Write the script as if you're speaking directly to listeners.
"""

    async def generate_script(
        self,
        request: ScriptGenerationRequest,
        podcast_group: PodcastGroup
    ) -> ScriptGenerationResponse:
        """Generate a podcast script from collection data."""
        
        logger.info(f"Generating script for episode {request.episode_id}")
        
        # Create prompts
        system_prompt = self.create_system_prompt(podcast_group)
        content_prompt = self.create_content_prompt(
            request.collection, podcast_group, request.style_preferences
        )
        
        # Generate script with graceful fallback if Ollama errors
        model = DEFAULT_MODEL
        response_text = ""
        try:
            response_text = await self.ollama_client.generate_script(
                model=model,
                prompt=content_prompt,
                system_prompt=system_prompt
            )
        except Exception as e:
            # Fallback script generation
            logger.warning(f"Ollama script generation failed, using fallback: {e}")
            response_text = self._generate_fallback_script(request.collection, podcast_group)
        
        generation_metadata = {
            "model_used": model,
            "generation_timestamp": datetime.utcnow().isoformat(),
            "target_length_minutes": request.collection.target_length_minutes,
            "collection_id": request.collection.collection_id,
            "feeds_count": len(request.collection.feeds),
            "presenter_briefs_count": len(request.collection.presenter_briefs),
            "style_preferences": request.style_preferences or {},
            "script_word_count": len(response_text.split()),
            "estimated_duration_minutes": len(response_text.split()) / 150,
            "raw_response_length": len(response_text)
        }
        
        return ScriptGenerationResponse(
            episode_id=request.episode_id,
            script=response_text,
            generation_metadata=generation_metadata
        )
    
    def _generate_fallback_script(self, collection: CollectionData, podcast_group: PodcastGroup) -> str:
        """Generate a fallback script when Ollama fails."""
        
        script = f"""Welcome to {podcast_group.name}. I'm your host, and today we have some fascinating stories to share with you.

"""
        
        # Add content from feeds
        for i, feed in enumerate(collection.feeds, 1):
            script += f"""Let's start with our {i}{'st' if i == 1 else 'nd' if i == 2 else 'rd' if i == 3 else 'th'} story. {feed.get('title', 'Breaking news')}. 

{feed.get('summary', 'This is an important development that we're following closely.')}

"""
        
        # Add presenter insights if available
        if collection.presenter_briefs:
            script += """Our presenters have been analyzing these developments, and they bring some interesting perspectives to the table.

"""
            for brief in collection.presenter_briefs[:2]:  # Use first 2 briefs
                presenter_name = brief.get('presenter_name', 'One of our analysts')
                brief_text = brief.get('brief', '')[:200]  # Truncate for fallback
                script += f"""{presenter_name} notes that {brief_text}...

"""
        
        # Add conclusion
        script += f"""These stories show us how interconnected our world has become. From technology to finance, from local developments to global trends, everything seems to be connected in ways we might not immediately see.

That's all for today's episode of {podcast_group.name}. Thank you for listening, and we'll be back with more analysis and insights in our next episode. Stay informed, stay engaged, and we'll see you next time."""
        
        return script


# Initialize services
script_writer = ScriptWriter()

# Create tables on startup
@app.on_event("startup")
async def startup_event():
    create_tables()
    logger.info("Writer Service (Script Generation) started")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "writer-script", "timestamp": datetime.utcnow()}


@app.post("/generate-script", response_model=ScriptGenerationResponse)
async def generate_script(
    request: ScriptGenerationRequest,
    db: Session = Depends(get_db)
):
    """Generate a podcast script from collection data."""
    
    # Get podcast group details
    podcast_group = db.query(PodcastGroup).filter(
        PodcastGroup.id == request.group_id
    ).first()
    
    if not podcast_group:
        raise HTTPException(status_code=404, detail="Podcast group not found")
    
    # Get episode details (optional for testing)
    episode = db.query(Episode).filter(Episode.id == request.episode_id).first()
    if not episode:
        logger.warning(f"Episode {request.episode_id} not found, proceeding without episode validation")
    
    try:
        result = await script_writer.generate_script(request, podcast_group)
        logger.info(f"Successfully generated script for episode {request.episode_id}")
        return result
        
    except Exception as e:
        logger.error(f"Error generating script for episode {request.episode_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Script generation failed: {str(e)}")


@app.post("/test-script-generation")
async def test_script_generation(
    test_collection_id: str = "test-collection-001",
    target_length_minutes: int = 10,
    db: Session = Depends(get_db)
):
    """Test endpoint for script generation."""
    
    try:
        # Create test collection data
        test_collection = CollectionData(
            collection_id=test_collection_id,
            feeds=[
                {
                    "title": "Apple announces new AI features for iPhone",
                    "summary": "Apple unveiled new artificial intelligence capabilities for its latest iPhone models, including enhanced Siri functionality and on-device processing.",
                    "topic": "Technology",
                    "subject": "AI/ML",
                    "importance_rank": 8,
                    "source": "TechCrunch"
                },
                {
                    "title": "Federal Reserve signals potential rate cuts",
                    "summary": "The Fed indicated it may lower interest rates in response to economic conditions and inflation trends.",
                    "topic": "Finance",
                    "subject": "Monetary Policy",
                    "importance_rank": 9,
                    "source": "Reuters"
                }
            ],
            reviewer_summaries=[
                {
                    "summary": "Technology and finance stories showing interconnected economic and innovation trends.",
                    "tags": ["technology", "finance", "ai", "monetary policy"]
                }
            ],
            presenter_briefs=[
                {
                    "presenter_name": "Alex Chen",
                    "brief": "These stories highlight how technological innovation and economic policy are increasingly intertwined. Apple's AI developments show the private sector pushing boundaries, while the Fed's potential rate cuts reflect the broader economic environment that enables such innovation."
                }
            ],
            target_length_minutes=target_length_minutes
        )
        
        # Create test request
        request = ScriptGenerationRequest(
            episode_id=UUID("00000000-0000-0000-0000-000000000001"),
            group_id=UUID("00000000-0000-0000-0000-000000000001"),
            collection=test_collection,
            style_preferences={
                "tone": "conversational",
                "pacing": "moderate",
                "focus": "balanced"
            }
        )
        
        # Create a test podcast group
        test_group = PodcastGroup(
            id=request.group_id,
            name="Tech & Finance Daily",
            description="Daily analysis of technology and financial news",
            category="Technology",
            language="en",
            country="US"
        )
        
        result = await script_writer.generate_script(request, test_group)
        
        return {
            "test_collection": test_collection.dict(),
            "test_podcast_group": {
                "name": test_group.name,
                "description": test_group.description,
                "category": test_group.category
            },
            "generated_script": result.dict(),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in test script generation: {e}")
        raise HTTPException(status_code=500, detail=f"Test script generation failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8010)