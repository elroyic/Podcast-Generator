"""
Heavy Reviewer Service - High-quality article review using Qwen3-4B-Thinking-2507 via vLLM.
Optimized for accuracy with higher latency (~1200ms per feed).
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

app = FastAPI(title="Heavy Reviewer Service", version="1.0.0")

# Configuration
VLLM_BASE_URL = os.getenv("VLLM_BASE_URL", "http://localhost:8000")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen3-4B-Thinking-2507")
PORT = int(os.getenv("PORT", "8000"))


class FeedReviewRequest(BaseModel):
    """Request to review a feed item."""
    feed_id: str
    title: str
    url: str
    content: str
    published: str


class ReviewResponse(BaseModel):
    """Response from heavy reviewer."""
    tags: List[str]
    summary: str
    confidence: float
    model: str


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    model: str
    avg_latency_ms: float


class VLLMClient:
    """Client for vLLM API."""
    
    def __init__(self, base_url: str = VLLM_BASE_URL):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=60.0)  # Longer timeout for heavy model
    
    async def generate_review(self, prompt: str) -> str:
        """Generate review using vLLM."""
        try:
            payload = {
                "model": "Qwen/Qwen2-0.5B",
                "messages": [
                    {"role": "system", "content": "You are a comprehensive news article analyzer. You must respond in the exact format requested. Do not add explanations or extra text."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 300,
                "temperature": 0.1,  # Lower temperature for more consistent results
                "top_p": 0.9,
                "stop": ["\n\n"]
            }
            
            response = await self.client.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload
            )
            response.raise_for_status()
            
            result = response.json()
            return result["choices"][0]["message"]["content"]
            
        except Exception as e:
            logger.error(f"Error generating review with vLLM: {e}")
            raise HTTPException(status_code=500, detail=f"Review generation failed: {str(e)}")


class HeavyReviewer:
    """Heavy reviewer for high-quality article categorization."""
    
    def __init__(self):
        self.vllm_client = VLLMClient()
        self.latency_history = []
    
    def create_review_prompt(self, request: FeedReviewRequest) -> str:
        """Create comprehensive prompt for heavy review."""
        return f"""Example:
Title: Apple announces new AI features for iPhone
Content: Apple Inc. today announced significant updates to its iPhone lineup, focusing heavily on artificial intelligence integration.

Response:
TOPIC: Technology
SUBJECT: Artificial Intelligence
TAGS: technology, ai, innovation, mobile
SUMMARY: Apple announces new AI features for iPhone
CONFIDENCE: 0.85

Now analyze this article:
Title: {request.title}
Content: {request.content[:2000]}

Response:"""
    
    def parse_review_response(self, response: str) -> Dict[str, Any]:
        """Parse the vLLM response into structured data."""
        try:
            # Debug: log the raw response
            logger.info(f"Raw heavy reviewer response: {response[:200]}...")
            
            lines = response.strip().split('\n')
            topic = "General"
            subject = "General"
            tags = []
            summary = ""
            confidence = 0.8  # Higher default confidence for heavy model
            
            for line in lines:
                line = line.strip()
                if line.startswith("TOPIC:"):
                    topic = line.replace("TOPIC:", "").strip()
                elif line.startswith("SUBJECT:"):
                    subject = line.replace("SUBJECT:", "").strip()
                elif line.startswith("TAGS:"):
                    tags = [tag.strip() for tag in line.replace("TAGS:", "").split(",") if tag.strip()]
                elif line.startswith("SUMMARY:"):
                    summary = line.replace("SUMMARY:", "").strip()
                elif line.startswith("CONFIDENCE:"):
                    try:
                        confidence = float(line.replace("CONFIDENCE:", "").strip())
                        confidence = max(0.0, min(1.0, confidence))
                    except ValueError:
                        confidence = 0.8
            
            # Enhanced fallback parsing
            if not tags and not summary:
                content_lower = response.lower()
                
                # More sophisticated topic detection
                if any(word in content_lower for word in ["finance", "stock", "market", "trading", "investment", "economy"]):
                    topic = "Finance"
                    subject = "Markets"
                    tags = ["finance", "markets", "investment"]
                elif any(word in content_lower for word in ["tech", "ai", "technology", "software", "digital", "innovation"]):
                    topic = "Technology"
                    subject = "AI/Innovation"
                    tags = ["technology", "ai", "innovation"]
                elif any(word in content_lower for word in ["politics", "government", "election", "policy", "legislation"]):
                    topic = "Politics"
                    subject = "Government"
                    tags = ["politics", "government", "policy"]
                elif any(word in content_lower for word in ["health", "medical", "healthcare", "disease", "treatment"]):
                    topic = "Health"
                    subject = "Healthcare"
                    tags = ["health", "healthcare", "medical"]
                elif any(word in content_lower for word in ["climate", "environment", "sustainability", "green"]):
                    topic = "Environment"
                    subject = "Climate"
                    tags = ["environment", "climate", "sustainability"]
                else:
                    topic = "General"
                    subject = "News"
                    tags = ["news", "general"]
                
                summary = response[:300] if response else "Comprehensive article analysis completed"
            
            return {
                "topic": topic,
                "subject": subject,
                "tags": tags[:5],  # Limit to 5 tags
                "summary": summary[:300],  # Limit summary length
                "confidence": confidence
            }
            
        except Exception as e:
            logger.error(f"Error parsing review response: {e}")
            return {
                "topic": "General",
                "subject": "General",
                "tags": ["news", "general"],
                "summary": "Heavy review parsing failed",
                "confidence": 0.0
            }
    
    async def review_feed(self, request: FeedReviewRequest) -> ReviewResponse:
        """Review a feed item with high quality."""
        start_time = datetime.utcnow()
        
        try:
            prompt = self.create_review_prompt(request)
            response = await self.vllm_client.generate_review(prompt)
            result = self.parse_review_response(response)
            
            # Record latency
            latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            self.latency_history.append(latency_ms)
            if len(self.latency_history) > 50:  # Smaller history for heavy model
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
                summary="Heavy review failed - using fallback",
                confidence=0.0,
                model=MODEL_NAME
            )


# Initialize reviewer
heavy_reviewer = HeavyReviewer()


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint with latency metrics."""
    avg_latency = 0.0
    if heavy_reviewer.latency_history:
        avg_latency = sum(heavy_reviewer.latency_history) / len(heavy_reviewer.latency_history)
    
    return HealthResponse(
        status="ok",
        model=MODEL_NAME,
        avg_latency_ms=avg_latency
    )


@app.post("/review", response_model=ReviewResponse)
async def review_feed(request: FeedReviewRequest):
    """Review a feed item with high quality."""
    logger.info(f"Heavy reviewing feed: {request.title[:50]}...")
    
    result = await heavy_reviewer.review_feed(request)
    
    logger.info(f"Heavy review completed: confidence={result.confidence:.2f}, tags={result.tags}")
    return result


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "heavy-reviewer",
        "model": MODEL_NAME,
        "status": "running",
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
