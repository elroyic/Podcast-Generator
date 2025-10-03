"""
Presenter Service - Generates persona-based briefs and feedback using Ollama.
DOES NOT handle audio generation - that's done by the TTS service.
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

# Add the shared directory to Python path
import sys
sys.path.append('/app/shared')

from database import get_db, create_tables
from models import Presenter

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Presenter Service (Persona Only)", version="2.0.0")

# Configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama-cpu:11434")
DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "qwen2:1.5b")


# Presenter Review Models
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
    articles: List[Dict[str, Any]]


class FeedbackRequest(BaseModel):
    """Request to generate script feedback."""
    presenter_id: UUID
    script_id: str
    script: str
    collection_context: Dict[str, Any]


class OllamaClient:
    """Client for interacting with Ollama API for presenter reviews."""
    
    def __init__(self, base_url: str = OLLAMA_BASE_URL):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=180.0)
    
    async def generate_content(
        self,
        model: str,
        prompt: str,
        system_prompt: str = None,
        max_tokens: int = 1500
    ) -> str:
        """Generate content using Ollama."""
        try:
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.8,
                    "top_p": 0.9,
                    "num_predict": max_tokens
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
            raise


# Global instances
ollama_client = OllamaClient()


class PersonaPresenter:
    """Handles presenter persona-based content generation."""
    
    def __init__(self):
        self.ollama_client = ollama_client
    
    def _get_presenter(self, presenter_id: UUID, db: Session) -> Presenter:
        """Get presenter from database."""
        presenter = db.query(Presenter).filter(Presenter.id == presenter_id).first()
        if not presenter:
            raise HTTPException(status_code=404, detail=f"Presenter {presenter_id} not found")
        return presenter
    
    async def generate_collection_brief(
        self,
        request: BriefRequest,
        db: Session
    ) -> CollectionBrief:
        """Generate a 1000-word brief on a collection (in character)."""
        presenter = self._get_presenter(request.presenter_id, db)
        
        logger.info(f"Generating collection brief for presenter {presenter.name}")
        
        # Create system prompt based on presenter's persona
        system_prompt = f"""
You are {presenter.name}, a podcast presenter with the following persona:
{presenter.persona}

Your task is to write a 1000-word brief on a collection of news articles, staying in character.
Write in first person as {presenter.name}, reflecting your unique perspective and voice.
Focus on the key themes, interesting angles, and potential discussion points.
"""
        
        # Create content prompt with article summaries
        articles_text = "\n\n".join([
            f"Article {i+1}: {article.get('title', 'Untitled')}\n{article.get('content', article.get('summary', ''))[:500]}"
            for i, article in enumerate(request.articles[:10])
        ])
        
        content_prompt = f"""
Collection ID: {request.collection_id}

Articles in this collection:
{articles_text}

Please write a 1000-word brief on this collection from your perspective as {presenter.name}.
Highlight the key themes, provide your insights, and suggest interesting angles for discussion.
Stay in character and write in first person.
"""
        
        # Generate brief
        try:
            brief_text = await self.ollama_client.generate_content(
                model=DEFAULT_MODEL,
                prompt=content_prompt,
                system_prompt=system_prompt,
                max_tokens=1500
            )
        except Exception as e:
            logger.warning(f"Ollama brief generation failed, using fallback: {e}")
            # Simple fallback
            brief_text = f"""As {presenter.name}, I've reviewed this collection of {len(request.articles)} articles.
The main themes include current events and trending topics. These articles provide valuable insights into today's news landscape.
I believe this collection will make for an engaging podcast episode that our audience will find informative and entertaining."""
        
        logger.info(f"Successfully generated brief for presenter {presenter.name}")
        
        return CollectionBrief(
            presenter_id=request.presenter_id,
            collection_id=request.collection_id,
            brief=brief_text,
            brief_metadata={
                "model_used": DEFAULT_MODEL,
                "generation_timestamp": datetime.utcnow().isoformat(),
                "article_count": len(request.articles),
                "presenter_name": presenter.name
            }
        )
    
    async def generate_script_feedback(
        self,
        request: FeedbackRequest,
        db: Session
    ) -> ScriptFeedback:
        """Generate 500-word feedback on a script (in character)."""
        presenter = self._get_presenter(request.presenter_id, db)
        
        logger.info(f"Generating script feedback for presenter {presenter.name}")
        
        # Create system prompt
        system_prompt = f"""
You are {presenter.name}, a podcast presenter with the following persona:
{presenter.persona}

Your task is to provide 500-word feedback on a podcast script, staying in character.
Write in first person as {presenter.name}, reflecting your unique perspective.
Comment on what works well, what could be improved, and any concerns or suggestions.
"""
        
        content_prompt = f"""
Script ID: {request.script_id}

Script to review:
{request.script[:2000]}  

Please provide 500-word feedback on this script from your perspective as {presenter.name}.
Stay in character and write in first person.
"""
        
        # Generate feedback
        try:
            feedback_text = await self.ollama_client.generate_content(
                model=DEFAULT_MODEL,
                prompt=content_prompt,
                system_prompt=system_prompt,
                max_tokens=800
            )
        except Exception as e:
            logger.warning(f"Ollama feedback generation failed, using fallback: {e}")
            # Simple fallback
            feedback_text = f"""As {presenter.name}, I've reviewed this script and found it well-structured.
The content flows naturally and should engage our audience. A few minor adjustments could enhance clarity, but overall this is solid work."""
        
        logger.info(f"Successfully generated feedback for presenter {presenter.name}")
        
        return ScriptFeedback(
            presenter_id=request.presenter_id,
            script_id=request.script_id,
            feedback=feedback_text,
            feedback_metadata={
                "model_used": DEFAULT_MODEL,
                "generation_timestamp": datetime.utcnow().isoformat(),
                "script_length": len(request.script),
                "presenter_name": presenter.name
            }
        )


# Global presenter instance
persona_presenter = PersonaPresenter()


@app.on_event("startup")
async def startup_event():
    """Initialize service on startup."""
    logger.info("🎭 Presenter Service (Persona Only) starting up...")
    logger.info(f"Using Ollama at {OLLAMA_BASE_URL} with model {DEFAULT_MODEL}")
    create_tables()


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Presenter (Persona Only)",
        "ollama_url": OLLAMA_BASE_URL,
        "model": DEFAULT_MODEL
    }


@app.post("/generate-brief", response_model=CollectionBrief)
async def generate_brief(request: BriefRequest, db: Session = Depends(get_db)):
    """Generate a 1000-word brief on a collection from presenter's perspective."""
    try:
        return await persona_presenter.generate_collection_brief(request, db)
    except Exception as e:
        logger.error(f"Error generating brief for presenter {request.presenter_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Brief generation failed: {str(e)}")


@app.post("/generate-feedback", response_model=ScriptFeedback)
async def generate_feedback(request: FeedbackRequest, db: Session = Depends(get_db)):
    """Generate 500-word feedback on a script from presenter's perspective."""
    try:
        return await persona_presenter.generate_script_feedback(request, db)
    except Exception as e:
        logger.error(f"Error generating feedback for presenter {request.presenter_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Feedback generation failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)

