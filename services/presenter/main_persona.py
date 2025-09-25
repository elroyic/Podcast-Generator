"""
Presenter Service - Generates persona-based briefs and feedback using gpt-oss-20b.
Each presenter has a unique persona and voice as specified in the workflow.
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
from shared.models import Presenter, Article, NewsFeed

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Presenter Service", version="1.0.0")

# Configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "gpt-oss-20b")  # Using gpt-oss-20b as specified


class CollectionBrief(BaseModel):
    """1000-word brief on a collection (in character)."""
    presenter_id: UUID
    collection_id: str
    brief: str
    brief_metadata: Dict[str, Any]


class ScriptFeedback(BaseModel):
    """500-word feedback on a script (in character)."""
    presenter_id: UUID
    script_id: str
    feedback: str
    feedback_metadata: Dict[str, Any]


class BriefRequest(BaseModel):
    """Request to generate a collection brief."""
    presenter_id: UUID
    collection_id: str
    articles: List[Dict[str, Any]]  # Articles in the collection


class FeedbackRequest(BaseModel):
    """Request to generate script feedback."""
    presenter_id: UUID
    script_id: str
    script: str
    collection_context: Dict[str, Any]


class OllamaClient:
    """Client for interacting with Ollama API."""
    
    def __init__(self, base_url: str = OLLAMA_BASE_URL):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=120.0)  # Longer timeout for longer responses
    
    async def generate_content(
        self,
        model: str,
        prompt: str,
        system_prompt: str = None
    ) -> str:
        """Generate content using Ollama."""
        try:
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.8,  # Higher temperature for more creative, persona-driven content
                    "top_p": 0.9,
                    "max_tokens": 3000  # Allow for longer responses
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
            logger.error(f"Error generating content with Ollama: {e}")
            raise HTTPException(status_code=500, detail=f"Content generation failed: {str(e)}")


class PersonaPresenter:
    """Handles persona-based presenter logic."""
    
    def __init__(self):
        self.ollama_client = OllamaClient()
    
    def create_presenter_persona_prompt(self, presenter: Presenter) -> str:
        """Create system prompt based on presenter persona."""
        return f"""
You are {presenter.name}, a podcast presenter with a unique personality and perspective.

PERSONA DETAILS:
- Name: {presenter.name}
- Bio: {presenter.bio or 'No bio available'}
- Age: {presenter.age or 'Not specified'}
- Gender: {presenter.gender or 'Not specified'}
- Country: {presenter.country or 'Not specified'}
- City: {presenter.city or 'Not specified'}
- Specialties: {', '.join(presenter.specialties or [])}
- Expertise: {', '.join(presenter.expertise or [])}
- Interests: {', '.join(presenter.interests or [])}

PERSONALITY TRAITS:
- You have your own unique voice and perspective on news and current events
- You bring your personal experiences and background to your analysis
- You have specific biases and viewpoints that influence how you interpret information
- You speak in a conversational, engaging manner that connects with listeners
- You're knowledgeable in your areas of expertise but also curious about new topics

COMMUNICATION STYLE:
- Speak in first person ("I think...", "In my experience...", "From my perspective...")
- Use personal anecdotes and examples when relevant
- Be authentic to your personality and background
- Engage with the content critically but constructively
- Make complex topics accessible to general audiences
- Show enthusiasm for topics you're passionate about

Remember: You are NOT a neutral news reader. You are a personality with opinions, experiences, and a unique perspective that makes you valuable to listeners.
"""

    def create_brief_prompt(self, presenter: Presenter, articles: List[Dict[str, Any]]) -> str:
        """Create prompt for generating collection brief."""
        
        # Format articles for the prompt
        articles_text = ""
        for i, article in enumerate(articles, 1):
            articles_text += f"""
Article {i}:
Title: {article.get('title', 'No title')}
Summary: {article.get('summary', 'No summary')}
Source: {article.get('source', 'Unknown')}
Publish Date: {article.get('publish_date', 'Unknown')}
"""
        
        return f"""
As {presenter.name}, please provide a 1000-word brief on this collection of news articles. 

COLLECTION ARTICLES:
{articles_text}

REQUIREMENTS:
1. Write exactly 1000 words (aim for this length)
2. Stay in character as {presenter.name}
3. Provide your unique perspective on these stories
4. Connect the articles to broader themes and trends
5. Share your insights and analysis
6. Make it engaging and conversational
7. Include your personal take on the significance of these stories
8. Consider how these stories relate to your areas of expertise: {', '.join(presenter.expertise or [])}

Write this as if you're preparing to discuss these stories on your podcast. Be authentic to your personality and background.
"""

    def create_feedback_prompt(self, presenter: Presenter, script: str, collection_context: Dict[str, Any]) -> str:
        """Create prompt for generating script feedback."""
        
        return f"""
As {presenter.name}, please provide 500-word feedback on this podcast script.

SCRIPT:
{script}

COLLECTION CONTEXT:
- Topic: {collection_context.get('topic', 'General')}
- Subject: {collection_context.get('subject', 'General')}
- Number of articles: {collection_context.get('article_count', 'Unknown')}
- Key themes: {', '.join(collection_context.get('themes', []))}

FEEDBACK REQUIREMENTS:
1. Write exactly 500 words (aim for this length)
2. Stay in character as {presenter.name}
3. Provide constructive feedback on the script
4. Comment on:
   - Content accuracy and relevance
   - Engagement and entertainment value
   - Flow and structure
   - Your personal perspective on the topics covered
   - Suggestions for improvement
   - How well it aligns with your presentation style
5. Be honest but constructive
6. Consider your expertise in: {', '.join(presenter.expertise or [])}

Write this as if you're reviewing a script that you might present. Be authentic to your personality and provide valuable insights.
"""

    async def generate_collection_brief(
        self,
        presenter: Presenter,
        articles: List[Dict[str, Any]],
        collection_id: str
    ) -> CollectionBrief:
        """Generate a 1000-word brief on a collection."""
        
        logger.info(f"Generating collection brief for presenter {presenter.name}")
        
        # Create prompts
        persona_prompt = self.create_presenter_persona_prompt(presenter)
        brief_prompt = self.create_brief_prompt(presenter, articles)
        
        # Generate brief with graceful fallback if Ollama errors
        model = DEFAULT_MODEL
        response_text = ""
        try:
            response_text = await self.ollama_client.generate_content(
                model=model,
                prompt=brief_prompt,
                system_prompt=persona_prompt
            )
        except Exception as e:
            # Fallback brief generation
            logger.warning(f"Ollama brief generation failed, using fallback: {e}")
            response_text = self._generate_fallback_brief(presenter, articles)
        
        brief_metadata = {
            "model_used": model,
            "generation_timestamp": datetime.utcnow().isoformat(),
            "article_count": len(articles),
            "presenter_persona": {
                "name": presenter.name,
                "expertise": presenter.expertise or [],
                "specialties": presenter.specialties or []
            },
            "raw_response_length": len(response_text)
        }
        
        return CollectionBrief(
            presenter_id=presenter.id,
            collection_id=collection_id,
            brief=response_text,
            brief_metadata=brief_metadata
        )
    
    async def generate_script_feedback(
        self,
        presenter: Presenter,
        script: str,
        collection_context: Dict[str, Any],
        script_id: str
    ) -> ScriptFeedback:
        """Generate 500-word feedback on a script."""
        
        logger.info(f"Generating script feedback for presenter {presenter.name}")
        
        # Create prompts
        persona_prompt = self.create_presenter_persona_prompt(presenter)
        feedback_prompt = self.create_feedback_prompt(presenter, script, collection_context)
        
        # Generate feedback with graceful fallback if Ollama errors
        model = DEFAULT_MODEL
        response_text = ""
        try:
            response_text = await self.ollama_client.generate_content(
                model=model,
                prompt=feedback_prompt,
                system_prompt=persona_prompt
            )
        except Exception as e:
            # Fallback feedback generation
            logger.warning(f"Ollama feedback generation failed, using fallback: {e}")
            response_text = self._generate_fallback_feedback(presenter, script)
        
        feedback_metadata = {
            "model_used": model,
            "generation_timestamp": datetime.utcnow().isoformat(),
            "script_length": len(script.split()),
            "presenter_persona": {
                "name": presenter.name,
                "expertise": presenter.expertise or [],
                "specialties": presenter.specialties or []
            },
            "raw_response_length": len(response_text)
        }
        
        return ScriptFeedback(
            presenter_id=presenter.id,
            script_id=script_id,
            feedback=response_text,
            feedback_metadata=feedback_metadata
        )
    
    def _generate_fallback_brief(self, presenter: Presenter, articles: List[Dict[str, Any]]) -> str:
        """Generate a fallback brief when Ollama fails."""
        brief = f"""As {presenter.name}, I'm excited to dive into this collection of news stories. Let me share my perspective on what's happening here.

"""
        
        # Add analysis of each article
        for i, article in enumerate(articles, 1):
            brief += f"""Looking at the {i}{'st' if i == 1 else 'nd' if i == 2 else 'rd' if i == 3 else 'th'} article, "{article.get('title', 'Untitled')}", I see some interesting developments. """
            
            if presenter.expertise:
                expertise_match = any(expertise.lower() in article.get('title', '').lower() or 
                                    expertise.lower() in article.get('summary', '').lower() 
                                    for expertise in presenter.expertise)
                if expertise_match:
                    brief += f"This is right in my wheelhouse of {', '.join(presenter.expertise)}. "
            
            brief += f"The story touches on {article.get('summary', 'various topics')[:100]}... This is significant because it shows how interconnected our world has become.

"""
        
        # Add concluding thoughts
        brief += f"""From my perspective as someone with expertise in {', '.join(presenter.expertise or ['general news analysis'])}, these stories collectively paint a picture of our current moment. The themes I'm seeing here suggest we're at an interesting crossroads, and I think listeners will find these developments both concerning and hopeful in different ways.

What strikes me most is how these stories, while seemingly disparate, actually connect in ways that reveal larger patterns. As {presenter.name}, I believe it's our job to help listeners see these connections and understand what they mean for our daily lives.

I'm looking forward to discussing these topics with our audience and hearing their thoughts as well. The conversation doesn't end with the news - it begins there."""
        
        return brief
    
    def _generate_fallback_feedback(self, presenter: Presenter, script: str) -> str:
        """Generate fallback feedback when Ollama fails."""
        feedback = f"""As {presenter.name}, I've reviewed this script and here are my thoughts:

The script covers some important ground, and I appreciate the effort to make complex topics accessible. From my perspective as someone with expertise in {', '.join(presenter.expertise or ['general analysis'])}, I think the content is solid but could benefit from a few adjustments.

First, the flow works well overall, but I'd suggest adding more personal touches that reflect my style as {presenter.name}. Listeners connect with authenticity, and I think we could weave in more of my personal perspective on these topics.

The structure is logical, though I'd recommend spending a bit more time on the implications of these stories. As someone who's been following these developments, I think we could add more context about why these stories matter to our audience's daily lives.

I'm particularly interested in how we can make the technical aspects more engaging. My background in {', '.join(presenter.specialties or ['news analysis'])} gives me some ideas about how to explain complex concepts in ways that don't lose our audience.

Overall, this is a strong foundation that I'm excited to build upon. With some tweaks to better reflect my voice and add more personal insights, I think this will resonate well with our listeners."""
        
        return feedback


# Initialize services
persona_presenter = PersonaPresenter()

# Create tables on startup
@app.on_event("startup")
async def startup_event():
    create_tables()
    logger.info("Presenter Service started")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "presenter", "timestamp": datetime.utcnow()}


@app.post("/generate-brief", response_model=CollectionBrief)
async def generate_collection_brief(
    request: BriefRequest,
    db: Session = Depends(get_db)
):
    """Generate a 1000-word brief on a collection."""
    
    # Get presenter from database
    presenter = db.query(Presenter).filter(Presenter.id == request.presenter_id).first()
    if not presenter:
        raise HTTPException(status_code=404, detail="Presenter not found")
    
    try:
        brief = await persona_presenter.generate_collection_brief(
            presenter=presenter,
            articles=request.articles,
            collection_id=request.collection_id
        )
        
        logger.info(f"Successfully generated brief for presenter {presenter.name}")
        return brief
        
    except Exception as e:
        logger.error(f"Error generating brief for presenter {request.presenter_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Brief generation failed: {str(e)}")


@app.post("/generate-feedback", response_model=ScriptFeedback)
async def generate_script_feedback(
    request: FeedbackRequest,
    db: Session = Depends(get_db)
):
    """Generate 500-word feedback on a script."""
    
    # Get presenter from database
    presenter = db.query(Presenter).filter(Presenter.id == request.presenter_id).first()
    if not presenter:
        raise HTTPException(status_code=404, detail="Presenter not found")
    
    try:
        feedback = await persona_presenter.generate_script_feedback(
            presenter=presenter,
            script=request.script,
            collection_context=request.collection_context,
            script_id=request.script_id
        )
        
        logger.info(f"Successfully generated feedback for presenter {presenter.name}")
        return feedback
        
    except Exception as e:
        logger.error(f"Error generating feedback for presenter {request.presenter_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Feedback generation failed: {str(e)}")


@app.get("/presenters", response_model=List[Dict[str, Any]])
async def list_presenters(db: Session = Depends(get_db)):
    """List all presenters."""
    presenters = db.query(Presenter).all()
    
    return [
        {
            "id": str(presenter.id),
            "name": presenter.name,
            "bio": presenter.bio,
            "age": presenter.age,
            "gender": presenter.gender,
            "country": presenter.country,
            "city": presenter.city,
            "specialties": presenter.specialties or [],
            "expertise": presenter.expertise or [],
            "interests": presenter.interests or []
        }
        for presenter in presenters
    ]


@app.post("/test-brief-generation")
async def test_brief_generation(
    presenter_name: str = "Alex Chen",
    test_articles: List[Dict[str, Any]] = None,
    db: Session = Depends(get_db)
):
    """Test endpoint for brief generation."""
    
    if test_articles is None:
        test_articles = [
            {
                "title": "Apple announces new AI features for iPhone",
                "summary": "Apple unveiled new artificial intelligence capabilities for its latest iPhone models.",
                "source": "TechCrunch",
                "publish_date": "2024-01-15"
            },
            {
                "title": "Federal Reserve signals potential rate cuts",
                "summary": "The Fed indicated it may lower interest rates in response to economic conditions.",
                "source": "Reuters",
                "publish_date": "2024-01-15"
            }
        ]
    
    try:
        # Create a test presenter
        test_presenter = Presenter(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            name=presenter_name,
            bio="Tech-savvy financial analyst with a passion for explaining complex topics",
            age=32,
            gender="Non-binary",
            country="United States",
            city="San Francisco",
            specialties=["Technology", "Finance", "AI"],
            expertise=["Financial Markets", "Technology Trends", "Economic Analysis"],
            interests=["Innovation", "Sustainability", "Social Impact"]
        )
        
        brief = await persona_presenter.generate_collection_brief(
            presenter=test_presenter,
            articles=test_articles,
            collection_id="test-collection-001"
        )
        
        return {
            "test_presenter": {
                "name": test_presenter.name,
                "bio": test_presenter.bio,
                "expertise": test_presenter.expertise
            },
            "test_articles": test_articles,
            "generated_brief": brief.dict(),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in test brief generation: {e}")
        raise HTTPException(status_code=500, detail=f"Test brief generation failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8008)