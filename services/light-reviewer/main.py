"""
Light Reviewer Service - Fast, CPU-friendly article review using Qwen2:0.5B via Ollama.
Optimized for high throughput with low latency (~250ms per feed).
"""
import logging
import os
import asyncio
from datetime import datetime
from typing import Dict, Any, List
from uuid import UUID

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Light Reviewer Service", version="1.0.0")

# Configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
MODEL_NAME = os.getenv("MODEL_NAME", "qwen2:0.5b")
PORT = int(os.getenv("PORT", "8000"))


class FeedReviewRequest(BaseModel):
    """Request to review a feed item."""
    feed_id: str
    title: str
    url: str
    content: str
    published: str


class ReviewResponse(BaseModel):
    """Response from light reviewer."""
    tags: List[str]
    summary: str
    confidence: float
    model: str


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    model: str
    avg_latency_ms: float


class OllamaClient:
    """Client for Ollama API."""
    
    def __init__(self, base_url: str = OLLAMA_BASE_URL):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def generate_review(self, prompt: str) -> str:
        """Generate review using Ollama."""
        try:
            payload = {
                "model": MODEL_NAME,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "top_p": 0.9,
                    "num_predict": 200
                }
            }
            
            response = await self.client.post(
                f"{self.base_url}/api/generate",
                json=payload
            )
            response.raise_for_status()
            result = response.json()
            return result["response"]
        except Exception as e:
            logger.error(f"Ollama API error: {e}")
            raise
            raise HTTPException(status_code=500, detail=f"Review generation failed: {str(e)}")


class LightReviewer:
    """Light reviewer for fast article categorization."""
    
    def __init__(self):
        self.ollama_client = OllamaClient()
        self.latency_history = []
    
    def create_review_prompt(self, request: FeedReviewRequest) -> str:
        """Create optimized prompt for light review."""
        return f"""Example:
Title: Apple announces new AI features for iPhone
Content: Apple Inc. today announced significant updates to its iPhone lineup, focusing heavily on artificial intelligence integration.

Response:
TAGS: technology, ai, innovation
SUMMARY: Apple announces new AI features for iPhone
CONFIDENCE: 0.85

Now analyze this article:
Title: {request.title}
Content: {request.content[:1000]}

Response:"""
    
    def parse_review_response(self, response: str) -> Dict[str, Any]:
        """Parse the vLLM response into structured data."""
        try:
            # Debug: log the raw response
            logger.info(f"Raw light reviewer response: {response[:200]}...")
            
            lines = response.strip().split('\n')
            tags = []
            summary = ""
            confidence = 0.5
            
            for line in lines:
                line = line.strip()
                if line.startswith("TAGS:"):
                    tags = [tag.strip() for tag in line.replace("TAGS:", "").split(",") if tag.strip()]
                elif line.startswith("SUMMARY:"):
                    summary = line.replace("SUMMARY:", "").strip()
                elif line.startswith("CONFIDENCE:"):
                    try:
                        confidence = float(line.replace("CONFIDENCE:", "").strip())
                        confidence = max(0.0, min(1.0, confidence))
                    except ValueError:
                        confidence = 0.5
            
            # Fallback parsing if format is different
            if not tags and not summary:
                # Try to extract tags from content
                content_lower = response.lower()
                if any(word in content_lower for word in ["finance", "stock", "market"]):
                    tags = ["finance", "markets"]
                elif any(word in content_lower for word in ["tech", "ai", "technology"]):
                    tags = ["technology", "ai"]
                elif any(word in content_lower for word in ["politics", "government"]):
                    tags = ["politics", "government"]
                else:
                    tags = ["news", "general"]
                
                summary = response[:200] if response else "Article review completed"
            
            return {
                "tags": tags[:5],  # Limit to 5 tags
                "summary": summary[:200],  # Limit summary length
                "confidence": confidence
            }
            
        except Exception as e:
            logger.error(f"Error parsing review response: {e}")
            return {
                "tags": ["news", "general"],
                "summary": "Review parsing failed",
                "confidence": 0.0
            }
    
    async def review_feed(self, request: FeedReviewRequest) -> ReviewResponse:
        """Review a feed item quickly."""
        start_time = datetime.utcnow()
        
        try:
            prompt = self.create_review_prompt(request)
            response = await self.ollama_client.generate_review(prompt)
            result = self.parse_review_response(response)
            
            # Record latency
            latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            self.latency_history.append(latency_ms)
            if len(self.latency_history) > 100:
                self.latency_history.pop(0)
            
            return ReviewResponse(
                tags=result["tags"],
                summary=result["summary"],
                confidence=result["confidence"],
                model=MODEL_NAME
            )
            
        except Exception as e:
            logger.error(f"Error reviewing feed: {e}")
            # Return fallback response
            return ReviewResponse(
                tags=["news", "general"],
                summary="Review failed - using fallback",
                confidence=0.0,
                model=MODEL_NAME
            )


# Initialize reviewer
light_reviewer = LightReviewer()


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint with latency metrics."""
    avg_latency = 0.0
    if light_reviewer.latency_history:
        avg_latency = sum(light_reviewer.latency_history) / len(light_reviewer.latency_history)
    
    return HealthResponse(
        status="ok",
        model=MODEL_NAME,
        avg_latency_ms=avg_latency
    )


@app.post("/review", response_model=ReviewResponse)
async def review_feed(request: FeedReviewRequest):
    """Review a feed item."""
    logger.info(f"Light reviewing feed: {request.title[:50]}...")
    
    result = await light_reviewer.review_feed(request)
    
    logger.info(f"Light review completed: confidence={result.confidence:.2f}, tags={result.tags}")
    return result


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "light-reviewer",
        "model": MODEL_NAME,
        "status": "running",
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
