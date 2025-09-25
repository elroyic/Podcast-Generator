"""
AI Pod Text Generation Service - Generates podcast scripts using Ollama.
"""
import logging
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from uuid import UUID


import httpx
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

# Add the shared directory to Python path
import sys
import os
sys.path.append('/app/shared')

from database import get_db, create_tables
from models import PodcastGroup, Article, Presenter

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Text Generation Service", version="1.0.0")

# Configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:latest")


class ScriptGenerationRequest(BaseModel):
    group_id: UUID
    article_summaries: List[Dict[str, Any]]
    target_duration_minutes: int = 75
    style_preferences: Optional[Dict[str, Any]] = None


class ScriptGenerationResponse(BaseModel):
    script: str
    estimated_duration_minutes: float
    articles_used: List[UUID]
    generation_metadata: Dict[str, Any]


class OllamaClient:
    """Client for interacting with Ollama API."""
    
    def __init__(self, base_url: str = OLLAMA_BASE_URL):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=300.0)  # 5 minute timeout for generation
    
    async def generate_script(
        self,
        model: str,
        prompt: str,
        system_prompt: str = None
    ) -> str:
        """Generate text using Ollama."""
        try:
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "max_tokens": 8000  # Adjust based on model limits
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


class ScriptGenerator:
    """Handles podcast script generation logic."""
    
    def __init__(self):
        self.ollama_client = OllamaClient()
    
    def create_system_prompt(self, podcast_group: PodcastGroup) -> str:
        """Create system prompt based on podcast group configuration."""
        presenters_info = []
        for i, presenter in enumerate(podcast_group.presenters):
            presenters_info.append(
                f"Presenter {i+1}: {presenter.name} - {presenter.bio or 'No bio available'}"
            )
        
        system_prompt = f"""
You are an expert audio podcast script writer. Create comprehensive, detailed, and engaging podcast content. 

PODCAST DETAILS:
- Name: {podcast_group.name}
- Description: {podcast_group.description or 'No description'}
- Category: {podcast_group.category or 'General'}
- Language: {podcast_group.language or 'English'}
- Country: {podcast_group.country or 'International'}

PRESENTERS:
{chr(10).join(presenters_info)}

STYLE GUIDELINES:
- Write in a conversational, engaging tone
- Include natural transitions between topics
- Add appropriate humor and personality
- Structure content with clear segments
- Include introductions and conclusions
- Make content accessible to general audiences
- Use presenters' names naturally in dialogue
- PROVIDE COMPREHENSIVE COVERAGE - be thorough and detailed
- Include in-depth analysis and discussion
- Add multiple perspectives and viewpoints
- Expand on key points with examples and explanations
- Create substantial, meaningful content

FORMAT:
- Write as a dialogue between presenters as if they are speaking to each other. 
- The presenters are {podcast_group.presenters}
- Mark speaker changes clearly with the presenters names.
- Add natural pauses and emphasis
- Include timing estimates where relevant
- Create LONG, DETAILED segments with extensive discussion and in depth analysis. 
- Add comedy to the script and to descriptions of concepts by relating them to real life situations. 
- Have the {podcast_group.presenters} tell stories about their lives and experiences to add personality and depth to the script.
- Ensure the script is SUBSTANTIAL and COMPREHENSIVE

LENGTH REQUIREMENTS:
- Target MINIMUM 1000+ words
- The script should be at least 10 minutes long.
- Create detailed, in-depth content
- Include extensive analysis and discussion
- Add comprehensive coverage of all topics
- Provide thorough explanations and examples

Target audience: General listeners interested in {podcast_group.category or 'current events'}
"""
        return system_prompt
    
    def create_content_prompt(
        self,
        article_summaries: List[Dict[str, Any]],
        target_duration: int,
        podcast_group: PodcastGroup
    ) -> str:
        """Create the main content prompt for script generation."""
        
        # Format articles for the prompt
        articles_text = []
        for i, article in enumerate(article_summaries[:10]):  # Limit to 10 articles
            articles_text.append(f"""
Article {i+1}:
Title: {article.get('title', 'No title')}
Summary: {article.get('summary', 'No summary')}
Link: {article.get('link', 'No link')}
Published: {article.get('publish_date', 'Unknown date')}
""")
        
        prompt = f"""
Create a COMPREHENSIVE {target_duration}-minute podcast episode script based on the following news articles and podcast details.

PODCAST GROUP: {podcast_group.name}
CATEGORY: {podcast_group.category or 'General News'}
KEYWORDS: {', '.join(podcast_group.keywords or [])}
TAGS: {', '.join(podcast_group.tags or [])}

NEWS ARTICLES TO DISCUSS:
{chr(10).join(articles_text)}

CRITICAL REQUIREMENTS:
1. Create a script that runs approximately {target_duration} minutes when spoken at normal pace
2. MINIMUM 1000+ WORDS - this is absolutely essential
3. Include engaging introduction and conclusion
4. Discuss ALL articles in detail with comprehensive analysis
5. Add extensive natural conversation flow between presenters
6. Include detailed transitions, reactions, and commentary
7. Make it entertaining and informative with in-depth coverage
8. Use the presenters' personalities and expertise areas extensively
9. Include call-to-action or sign-off at the end
10. PROVIDE THOROUGH, DETAILED ANALYSIS of each topic
11. Add multiple perspectives and viewpoints on each story
12. Include extensive examples, explanations, and context
13. Create substantial, meaningful dialogue between presenters
14. Ensure comprehensive coverage of all topics

STRUCTURE:
- Opening (2-3 minutes): Introduction, show overview, presenter greetings
- Main Content (60-70 minutes): Discussion of selected articles with commentary
- Closing (3-5 minutes): Summary, thanks, and sign-off

Please generate the complete script now:
"""
        return prompt
    
    async def generate_podcast_script(
        self,
        request: ScriptGenerationRequest,
        podcast_group: PodcastGroup
    ) -> ScriptGenerationResponse:
        """Generate a complete podcast script."""
        
        logger.info(f"Generating script for podcast group: {podcast_group.name}")
        
        # Create prompts
        system_prompt = self.create_system_prompt(podcast_group)
        content_prompt = self.create_content_prompt(
            request.article_summaries,
            request.target_duration_minutes,
            podcast_group
        )
        
        # Determine model to use (could be configured per group in the future)
        model = DEFAULT_MODEL
        fallback_used = False
        
        # Generate the script (graceful fallback if Ollama fails)
        try:
            script = await self.ollama_client.generate_script(
                model=model,
                prompt=content_prompt,
                system_prompt=system_prompt
            )
        except Exception as e:
            logger.warning(f"Ollama failed to generate script, using fallback: {e}")
            fallback_used = True
            # Build a comprehensive script directly from the provided articles and group details
            parts = []
            parts.append(f"### [Podcast: {podcast_group.name}]\n")
            parts.append("[INTRO]\nPresenter 1: Welcome to today's episode. We have a deep dive into the latest developments across technology and AI.\nPresenter 2: We'll explore multiple stories with context, analysis, and practical implications. Let's get started!\n")
            
            for idx, article in enumerate(request.article_summaries, start=1):
                title = article.get("title", "Untitled")
                summary = article.get("summary", "")
                content = article.get("content", "")
                link = article.get("link", "")
                parts.append(f"\n[Segment {idx}]\nPresenter 1: The story titled '{title}'.\nPresenter 2: Summary: {summary}\nPresenter 1: Let's unpack the details and implications.\nPresenter 2: {content}\nPresenter 1: You can read more here: {link}\n")
                parts.append("Presenter 2: Key takeaways include broader context, potential risks, and opportunities.\nPresenter 1: Exactly, and we should consider ethical and social impact as well.\n")
            
            parts.append("\n[Closing]\nPresenter 1: That wraps up today's comprehensive discussion.\nPresenter 2: Thanks for listening. Subscribe for more deep dives and insights.\n")
            script = "\n".join(parts)
        
        # Estimate duration (rough calculation: ~150 words per minute)
        word_count = len(script.split())
        estimated_duration = word_count / 150.0
        
        # Extract article IDs used (simplified - in reality, you'd track which articles were actually used)
        articles_used = [article.get('id') for article in request.article_summaries[:5]]
        
        generation_metadata = {
            "model_used": model,
            "word_count": word_count,
            "generation_timestamp": datetime.utcnow().isoformat(),
            "articles_processed": len(request.article_summaries),
            "target_duration": request.target_duration_minutes,
            "style_preferences": request.style_preferences or {},
            "fallback_used": fallback_used
        }
        
        return ScriptGenerationResponse(
            script=script,
            estimated_duration_minutes=estimated_duration,
            articles_used=articles_used,
            generation_metadata=generation_metadata
        )


# Initialize services
script_generator = ScriptGenerator()

# Create tables on startup
@app.on_event("startup")
async def startup_event():
    create_tables()
    logger.info("Text Generation Service started")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "text-generation", "timestamp": datetime.utcnow()}


@app.post("/generate-script", response_model=ScriptGenerationResponse)
async def generate_script(
    request: ScriptGenerationRequest,
    db: Session = Depends(get_db)
):
    """Generate a podcast script from news articles."""
    
    # Get podcast group details
    podcast_group = db.query(PodcastGroup).filter(
        PodcastGroup.id == request.group_id
    ).first()
    
    if not podcast_group:
        raise HTTPException(status_code=404, detail="Podcast group not found")
    
    try:
        result = await script_generator.generate_podcast_script(request, podcast_group)
        logger.info(f"Successfully generated script for group {request.group_id}")
        return result
        
    except Exception as e:
        logger.error(f"Error generating script for group {request.group_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Script generation failed: {str(e)}")


@app.get("/models")
async def list_available_models():
    """List available Ollama models."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            response.raise_for_status()
            
            models_data = response.json()
            return {
                "available_models": [model["name"] for model in models_data.get("models", [])],
                "default_model": DEFAULT_MODEL
            }
            
    except Exception as e:
        logger.error(f"Error fetching available models: {e}")
        return {
            "available_models": [],
            "default_model": DEFAULT_MODEL,
            "error": "Could not fetch model list"
        }


@app.post("/test-generation")
async def test_generation(
    test_prompt: str = "Write a short 2-minute podcast introduction about today's tech news.",
    db: Session = Depends(get_db)
):
    """Test endpoint for script generation."""
    try:
        result = await script_generator.ollama_client.generate_script(
            model=DEFAULT_MODEL,
            prompt=test_prompt,
            system_prompt="You are a podcast host. Write engaging, conversational content."
        )
        
        return {
            "generated_text": result,
            "model_used": DEFAULT_MODEL,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in test generation: {e}")
        raise HTTPException(status_code=500, detail=f"Test generation failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)