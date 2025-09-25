"""
Reviewer Service - Categorizes and classifies news articles using Qwen3.
Handles feed processing with queuing (not batching) as specified in the workflow.
"""
import logging
import os
from datetime import datetime
from typing import Dict, Any, Optional, List
from uuid import UUID

import httpx
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session

from shared.database import get_db, create_tables
from shared.models import Article, NewsFeed

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Reviewer Service", version="1.0.0")

# Configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:latest")


class ArticleReview(BaseModel):
    """Review result for an article."""
    article_id: UUID
    topic: str
    subject: str
    tags: List[str]
    summary: str  # ≤500 characters
    importance_rank: int  # 1-10
    review_metadata: Dict[str, Any]


class ReviewRequest(BaseModel):
    """Request to review an article."""
    article_id: UUID
    force_review: bool = False


class ReviewResponse(BaseModel):
    """Response from article review."""
    article_id: UUID
    review: ArticleReview
    processing_time_seconds: float


class OllamaClient:
    """Client for interacting with Ollama API."""
    
    def __init__(self, base_url: str = OLLAMA_BASE_URL):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=60.0)
    
    async def generate_review(
        self,
        model: str,
        prompt: str,
        system_prompt: str = None
    ) -> str:
        """Generate article review using Ollama."""
        try:
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,  # Lower temperature for more consistent categorization
                    "top_p": 0.8,
                    "max_tokens": 1000
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
            logger.error(f"Error generating review with Ollama: {e}")
            raise HTTPException(status_code=500, detail=f"Review generation failed: {str(e)}")


class ArticleReviewer:
    """Handles article review and categorization logic."""
    
    def __init__(self):
        self.ollama_client = OllamaClient()
    
    def create_system_prompt(self) -> str:
        """Create system prompt for article review."""
        return """
You are an expert news article reviewer and categorizer. Your task is to analyze news articles and provide structured categorization and classification.

REVIEW REQUIREMENTS:
1. Topic: Identify the main subject area (be creative and specific - don't limit to preset categories)
2. Subject: Define a more specific subject within the topic (be detailed and precise)
3. Tags: Generate 3-5 relevant tags for categorization (be creative and comprehensive - include trending topics, themes, and relevant keywords)
4. Summary: Concise summary of the article (≤500 characters)
5. Importance Rank: Rate importance from 1-10 (1=low, 10=critical/breaking news)

CATEGORIZATION GUIDELINES:
- Be creative and comprehensive in your categorization
- Don't limit yourself to preset categories - create new ones as needed
- Consider global impact and relevance
- Factor in recency and trending nature
- Consider audience interest and engagement potential
- Balance between specificity and broad appeal
- Include emerging topics and themes
- Consider cross-cutting issues and interdisciplinary connections

TAGGING GUIDELINES:
- Create tags that capture the essence of the story
- Include both broad and specific tags
- Consider trending topics and hashtags
- Include geographic, temporal, and thematic tags
- Add tags for audience segments and interests
- Include tags for content type (analysis, breaking, opinion, etc.)

OUTPUT FORMAT (JSON):
{
    "topic": "Your identified main topic category",
    "subject": "Your specific subject within topic",
    "tags": ["your", "creative", "relevant", "tags"],
    "summary": "Concise summary under 500 characters",
    "importance_rank": 8
}

IMPORTANCE RANKING CRITERIA:
- 1-3: Local news, minor updates, routine announcements
- 4-6: Regional news, moderate impact, industry updates
- 7-8: National/international news, significant impact, major developments
- 9-10: Breaking news, critical events, global impact, major policy changes
"""

    def create_content_prompt(self, article: Article) -> str:
        """Create the main content prompt for article review."""
        return f"""
Please review and categorize the following news article:

TITLE: {article.title}

SUMMARY: {article.summary or 'No summary available'}

CONTENT: {article.content[:2000] if article.content else 'No content available'}

PUBLISH DATE: {article.publish_date.isoformat() if article.publish_date else 'Unknown'}

SOURCE: {article.news_feed.name if article.news_feed else 'Unknown'}

Please provide a structured review with topic, subject, tags, summary, and importance ranking as specified in the system prompt.
"""

    def parse_review_response(self, response: str, article_id: UUID) -> ArticleReview:
        """Parse the Ollama response into structured review."""
        try:
            import json
            import re
            
            # Look for JSON in the response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                review_dict = json.loads(json_str)
            else:
                # Fallback: parse manually from text
                review_dict = self._parse_text_response(response)
            
            # Validate and clean the data
            topic = review_dict.get("topic", "General").strip()
            subject = review_dict.get("subject", "General").strip()
            tags = review_dict.get("tags", [])
            if isinstance(tags, str):
                tags = [tag.strip() for tag in tags.split(",")]
            tags = [tag.strip() for tag in tags if tag.strip()][:5]  # Limit to 5 tags
            
            summary = review_dict.get("summary", "").strip()
            if len(summary) > 500:
                summary = summary[:497] + "..."
            
            importance_rank = review_dict.get("importance_rank", 5)
            if not isinstance(importance_rank, int) or importance_rank < 1 or importance_rank > 10:
                importance_rank = 5
            
            return ArticleReview(
                article_id=article_id,
                topic=topic,
                subject=subject,
                tags=tags,
                summary=summary,
                importance_rank=importance_rank,
                review_metadata={
                    "model_used": DEFAULT_MODEL,
                    "review_timestamp": datetime.utcnow().isoformat(),
                    "raw_response": response[:500] + "..." if len(response) > 500 else response
                }
            )
            
        except Exception as e:
            logger.error(f"Error parsing review response: {e}")
            # Return default review
            return ArticleReview(
                article_id=article_id,
                topic="General",
                subject="General",
                tags=["news", "general"],
                summary="Article review failed - using default categorization",
                importance_rank=5,
                review_metadata={
                    "model_used": DEFAULT_MODEL,
                    "review_timestamp": datetime.utcnow().isoformat(),
                    "error": str(e),
                    "raw_response": response[:200] if response else ""
                }
            )
    
    def _parse_text_response(self, response: str) -> Dict[str, Any]:
        """Parse review from text response when JSON parsing fails."""
        lines = response.split('\n')
        review = {}
        
        for line in lines:
            line = line.strip()
            if line.startswith("Topic:"):
                review["topic"] = line.replace("Topic:", "").strip()
            elif line.startswith("Subject:"):
                review["subject"] = line.replace("Subject:", "").strip()
            elif line.startswith("Tags:"):
                tags_str = line.replace("Tags:", "").strip()
                review["tags"] = [tag.strip() for tag in tags_str.split(",")]
            elif line.startswith("Summary:"):
                review["summary"] = line.replace("Summary:", "").strip()
            elif line.startswith("Importance Rank:"):
                try:
                    review["importance_rank"] = int(line.replace("Importance Rank:", "").strip())
                except ValueError:
                    review["importance_rank"] = 5
        
        return review
    
    async def review_article(
        self,
        article: Article
    ) -> ArticleReview:
        """Review a single article."""
        
        logger.info(f"Reviewing article: {article.title[:50]}...")
        
        # Create prompts
        system_prompt = self.create_system_prompt()
        content_prompt = self.create_content_prompt(article)
        
        # Generate review with graceful fallback if Ollama errors
        model = DEFAULT_MODEL
        response_text = ""
        try:
            response_text = await self.ollama_client.generate_review(
                model=model,
                prompt=content_prompt,
                system_prompt=system_prompt
            )
            # Parse response into structured review
            review = self.parse_review_response(response_text, article.id)
        except Exception as e:
            # Fallback review generation to avoid 500s
            logger.warning(f"Ollama review generation failed, using fallback: {e}")
            # Simple fallback heuristics
            title_lower = article.title.lower()
            if any(word in title_lower for word in ["stock", "market", "finance", "trading", "investment"]):
                topic, subject = "Finance", "Stock Market"
                tags = ["finance", "markets", "trading"]
            elif any(word in title_lower for word in ["ai", "artificial", "machine learning", "tech"]):
                topic, subject = "Technology", "AI/ML"
                tags = ["technology", "ai", "innovation"]
            elif any(word in title_lower for word in ["politics", "election", "government", "policy"]):
                topic, subject = "Politics", "Government"
                tags = ["politics", "government", "policy"]
            else:
                topic, subject = "General", "News"
                tags = ["news", "general"]
            
            review = ArticleReview(
                article_id=article.id,
                topic=topic,
                subject=subject,
                tags=tags,
                summary=article.summary[:500] if article.summary else article.title,
                importance_rank=5,
                review_metadata={
                    "model_used": model,
                    "review_timestamp": datetime.utcnow().isoformat(),
                    "fallback_used": True,
                    "error": str(e),
                    "raw_response": ""
                }
            )
        
        return review


# Initialize services
article_reviewer = ArticleReviewer()

# Create tables on startup
@app.on_event("startup")
async def startup_event():
    create_tables()
    logger.info("Reviewer Service started")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "reviewer", "timestamp": datetime.utcnow()}


@app.post("/review-article", response_model=ReviewResponse)
async def review_article(
    request: ReviewRequest,
    db: Session = Depends(get_db)
):
    """Review a single article."""
    
    # Get article from database
    article = db.query(Article).filter(Article.id == request.article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    start_time = datetime.utcnow()
    
    try:
        review = await article_reviewer.review_article(article)
        
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        logger.info(f"Successfully reviewed article {request.article_id}")
        
        return ReviewResponse(
            article_id=request.article_id,
            review=review,
            processing_time_seconds=processing_time
        )
        
    except Exception as e:
        logger.error(f"Error reviewing article {request.article_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Article review failed: {str(e)}")


@app.post("/review-articles-batch")
async def review_articles_batch(
    article_ids: List[UUID],
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Review multiple articles in background."""
    
    logger.info(f"Queuing {len(article_ids)} articles for review")
    
    # Queue each article for individual review (not batching as per workflow)
    for article_id in article_ids:
        background_tasks.add_task(review_article_background, article_id)
    
    return {
        "message": f"Queued {len(article_ids)} articles for review",
        "article_ids": [str(aid) for aid in article_ids]
    }


@app.get("/articles/unreviewed")
async def get_unreviewed_articles(
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get articles that haven't been reviewed yet."""
    
    # For now, return all articles (in a real system, you'd track review status)
    articles = db.query(Article).order_by(Article.created_at.desc()).limit(limit).all()
    
    return [
        {
            "id": str(article.id),
            "title": article.title,
            "summary": article.summary,
            "publish_date": article.publish_date.isoformat() if article.publish_date else None,
            "source": article.news_feed.name if article.news_feed else "Unknown"
        }
        for article in articles
    ]


@app.post("/test-review")
async def test_review(
    test_title: str = "Apple announces new AI features for iPhone",
    test_summary: str = "Apple unveiled new artificial intelligence capabilities for its latest iPhone models, including enhanced Siri functionality and on-device processing.",
    test_content: str = "Apple Inc. today announced significant updates to its iPhone lineup, focusing heavily on artificial intelligence integration. The new features include improved Siri capabilities, enhanced photo processing, and on-device machine learning for better privacy and performance.",
    db: Session = Depends(get_db)
):
    """Test endpoint for article review."""
    
    try:
        # Create a test article
        test_article = Article(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            feed_id=UUID("00000000-0000-0000-0000-000000000001"),
            title=test_title,
            link="https://example.com/test-article",
            summary=test_summary,
            content=test_content,
            publish_date=datetime.utcnow()
        )
        
        review = await article_reviewer.review_article(test_article)
        
        return {
            "test_article": {
                "title": test_article.title,
                "summary": test_article.summary,
                "content_preview": test_article.content[:200] + "..." if len(test_article.content) > 200 else test_article.content
            },
            "review": review.dict(),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in test review: {e}")
        raise HTTPException(status_code=500, detail=f"Test review failed: {str(e)}")


async def review_article_background(article_id: UUID):
    """Background task to review an article."""
    db = next(get_db())
    try:
        article = db.query(Article).filter(Article.id == article_id).first()
        if not article:
            logger.error(f"Article {article_id} not found for background review")
            return
        
        review = await article_reviewer.review_article(article)
        logger.info(f"Background review completed for article {article_id}: {review.topic}/{review.subject}")
        
        # In a real system, you would store the review results in the database
        # For now, we just log the results
        
    except Exception as e:
        logger.error(f"Error in background review for article {article_id}: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8007)