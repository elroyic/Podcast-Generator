"""
Simplified Text Generation Service for local testing.
This version generates mock scripts without requiring Ollama.
"""

import logging
import random
from datetime import datetime
from typing import List, Dict, Any, Optional
from uuid import UUID

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Text Generation Service (Simple)", version="1.0.0")


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


def generate_mock_script(article_summaries: List[Dict[str, Any]], target_duration: int) -> str:
    """Generate a mock podcast script."""
    
    # Select a few articles to discuss
    selected_articles = article_summaries[:3] if len(article_summaries) >= 3 else article_summaries
    
    script_parts = [
        "Welcome to today's podcast! I'm your host, and we have some fascinating stories to share with you today.",
        "",
        "Let's dive right into the news:",
        ""
    ]
    
    for i, article in enumerate(selected_articles, 1):
        script_parts.extend([
            f"[Segment {i}]",
            f"First up, we have a story about {article.get('title', 'current events')}.",
            f"This is really interesting because it touches on some important topics that our listeners should know about.",
            f"The key points here are quite significant, and I think it's worth discussing the implications.",
            f"What do you think about this development? It seems like this could have broader impacts on the industry.",
            f"Absolutely, and it's also worth noting how this connects to other stories we've been following.",
            ""
        ])
    
    # Add conclusion
    script_parts.extend([
        "That wraps up our main stories for today.",
        "Thank you for listening, and we'll be back with more news and analysis next time.",
        "Until then, stay informed and stay curious!",
        ""
    ])
    
    return "\n".join(script_parts)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "text-generation-simple", "timestamp": datetime.utcnow()}


@app.post("/generate-script", response_model=ScriptGenerationResponse)
async def generate_script(request: ScriptGenerationRequest):
    """Generate a podcast script from news articles."""
    
    logger.info(f"Generating script for group {request.group_id}")
    
    try:
        # Generate mock script
        script = generate_mock_script(request.article_summaries, request.target_duration_minutes)
        
        # Estimate duration (rough calculation: ~150 words per minute)
        word_count = len(script.split())
        estimated_duration = word_count / 150.0
        
        # Extract article IDs used
        articles_used = []
        for article in request.article_summaries[:3]:
            article_id = article.get('id')
            if article_id:
                try:
                    # Validate UUID format
                    from uuid import UUID
                    UUID(article_id)
                    articles_used.append(article_id)
                except (ValueError, TypeError):
                    # Skip invalid UUIDs
                    continue
        
        generation_metadata = {
            "model_used": "mock-generator",
            "word_count": word_count,
            "generation_timestamp": datetime.utcnow().isoformat(),
            "articles_processed": len(request.article_summaries),
            "target_duration": request.target_duration_minutes,
            "style_preferences": request.style_preferences or {}
        }
        
        return ScriptGenerationResponse(
            script=script,
            estimated_duration_minutes=estimated_duration,
            articles_used=articles_used,
            generation_metadata=generation_metadata
        )
        
    except Exception as e:
        logger.error(f"Error generating script: {e}")
        raise HTTPException(status_code=500, detail=f"Script generation failed: {str(e)}")


@app.post("/test-generation")
async def test_generation(test_prompt: str = "Write a short 2-minute podcast introduction about today's tech news."):
    """Test endpoint for script generation."""
    
    mock_script = f"""
Welcome to Tech Talk Daily!

Today we're diving into the latest developments in technology that are shaping our world.

{test_prompt}

This is really exciting news for anyone following the tech industry. The implications are significant and worth discussing.

Thank you for tuning in to Tech Talk Daily. We'll be back tomorrow with more insights from the world of technology.
"""
    
    return {
        "generated_text": mock_script,
        "model_used": "mock-generator",
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)