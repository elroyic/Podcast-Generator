"""
Reviewer Service – Two-tier Light/Heavy orchestration with Redis-backed config and metrics.
Backwards-compatible with existing /review-article endpoint; now persists review fields on Article.
"""
import logging
import os
from datetime import datetime
from typing import Dict, Any, Optional, List
from uuid import UUID

import httpx
import redis
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field
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
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

# Reviewer defaults (can be overridden via Redis config)
DEFAULT_CONF_THRESHOLD = float(os.getenv("REVIEWER_CONF_THRESHOLD", "0.85"))
DEFAULT_LIGHT_MODEL = os.getenv("REVIEWER_LIGHT_MODEL", "qwen2:0.5b")
DEFAULT_HEAVY_MODEL = os.getenv("REVIEWER_HEAVY_MODEL", "qwen3:4b")
DEFAULT_HEAVY_ENABLED = os.getenv("REVIEWER_HEAVY_ENABLED", "true").lower() == "true"


class ArticleReview(BaseModel):
    """Review result for an article."""
    article_id: UUID
    topic: str
    subject: str
    tags: List[str]
    summary: str  # ≤500 characters
    importance_rank: int  # 1-10
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
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
    reviewer_type: str
    fallback: bool = False


class ReviewerConfig(BaseModel):
    conf_threshold: float = Field(default=DEFAULT_CONF_THRESHOLD, ge=0.0, le=1.0)
    heavy_enabled: bool = Field(default=DEFAULT_HEAVY_ENABLED)
    light_model: str = Field(default=DEFAULT_LIGHT_MODEL)
    heavy_model: str = Field(default=DEFAULT_HEAVY_MODEL)
    light_workers: int = Field(default=1, ge=1, le=4)


class FeedReviewRequest(BaseModel):
    feed_id: str
    title: str
    url: str
    content: Optional[str] = None
    published: Optional[str] = None


class MetricsWindow(BaseModel):
    total_light: int
    total_heavy: int
    avg_latency_ms_light: float
    avg_latency_ms_heavy: float
    success_rate: float
    error_rate: float
    confidence_histogram: Dict[str, int]


class MetricsResponse(BaseModel):
    last_5m: MetricsWindow
    last_1h: MetricsWindow
    queue_length: int


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
        self.redis = redis.Redis.from_url(REDIS_URL, decode_responses=True)
        self.config_key = "reviewer:config"
        self.metrics_prefix = "reviewer:metrics"
        self.lat_list_light = f"{self.metrics_prefix}:lat:light"
        self.lat_list_heavy = f"{self.metrics_prefix}:lat:heavy"
        self.err_list = f"{self.metrics_prefix}:errors"
        self.conf_hist = f"{self.metrics_prefix}:conf_hist"
        self.queue_key = "reviewer:queue"
    
    def create_system_prompt(self) -> str:
        """Create system prompt for article review."""
        return """
You are an expert news article reviewer and categorizer. Analyze the article and output JSON only.

REVIEW REQUIREMENTS:
1. topic: Main subject area (specific, creative)
2. subject: More specific subject within topic
3. tags: 3-5 relevant tags (diverse, trending keywords)
4. summary: Concise summary (<= 500 chars)
5. importance_rank: Integer 1-10 (1=low, 10=critical)
6. confidence: Float 0.0-1.0 representing confidence in your topic classification

OUTPUT STRICTLY JSON (no prose):
{
  "topic": "...",
  "subject": "...",
  "tags": ["..."],
  "summary": "...",
  "importance_rank": 7,
  "confidence": 0.84
}
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
            confidence_val = review_dict.get("confidence", 0.0)
            try:
                confidence = float(confidence_val)
            except Exception:
                confidence = 0.0
            confidence = max(0.0, min(1.0, confidence))
            
            return ArticleReview(
                article_id=article_id,
                topic=topic,
                subject=subject,
                tags=tags,
                summary=summary,
                importance_rank=importance_rank,
                confidence=confidence,
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
                confidence=0.0,
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
    ) -> Dict[str, Any]:
        """Two-tier review with Light/Heavy based on confidence threshold."""
        logger.info(f"Reviewing article: {article.title[:80]}...")

        # Build prompts once
        system_prompt = self.create_system_prompt()
        content_prompt = self.create_content_prompt(article)

        # Load runtime config
        cfg = self._load_config()

        timings: Dict[str, float] = {}
        reviewer_type = "light"
        fallback_used = False
        model_used = cfg.light_model

        # LIGHT pass
        t0 = datetime.utcnow()
        try:
            light_resp = await self.ollama_client.generate_review(
                model=cfg.light_model,
                prompt=content_prompt,
                system_prompt=system_prompt
            )
            review = self.parse_review_response(light_resp, article.id)
            timings["light_ms"] = (datetime.utcnow() - t0).total_seconds() * 1000.0
            self._record_latency("light", timings["light_ms"]) 
            self._record_confidence(review.confidence)
            model_used = cfg.light_model
        except Exception as e:
            logger.warning(f"Light review failed, using fallback heuristics: {e}")
            review = self._fallback_review(article, model=cfg.light_model, error=e)
            timings["light_ms"] = (datetime.utcnow() - t0).total_seconds() * 1000.0
            self._record_error(str(e))
            self._record_latency("light", timings["light_ms"]) 
            self._record_confidence(review.confidence)

        # Route to HEAVY if enabled and below threshold
        if cfg.heavy_enabled and (review.confidence < cfg.conf_threshold):
            reviewer_type = "heavy"
            model_used = cfg.heavy_model
            retries = 0
            last_exc: Optional[Exception] = None
            while retries < 3:
                t1 = datetime.utcnow()
                try:
                    heavy_resp = await self.ollama_client.generate_review(
                        model=cfg.heavy_model,
                        prompt=content_prompt,
                        system_prompt=system_prompt
                    )
                    review = self.parse_review_response(heavy_resp, article.id)
                    timings["heavy_ms"] = (datetime.utcnow() - t1).total_seconds() * 1000.0
                    self._record_latency("heavy", timings["heavy_ms"]) 
                    self._record_confidence(review.confidence)
                    break
                except Exception as he:
                    last_exc = he
                    retries += 1
                    self._record_error(str(he))
            else:
                # Fallback to light output
                fallback_used = True
                reviewer_type = "light"
                model_used = cfg.light_model

        # Enrich review metadata
        review.review_metadata.update({
            "light_model": cfg.light_model,
            "heavy_model": cfg.heavy_model,
            "model_used": model_used,
            "reviewer_type": reviewer_type,
            "timings_ms": timings,
            "fallback_used": fallback_used,
        })

        return {
            "review": review,
            "reviewer_type": reviewer_type,
            "fallback": fallback_used,
            "timings": timings,
        }

    def _fallback_review(self, article: Article, model: str, error: Exception) -> ArticleReview:
        title_lower = (article.title or "").lower()
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
        return ArticleReview(
            article_id=article.id,
            topic=topic,
            subject=subject,
            tags=tags,
            summary=(article.summary or article.title or "")[:500],
            importance_rank=5,
            confidence=0.0,
            review_metadata={
                "model_used": model,
                "review_timestamp": datetime.utcnow().isoformat(),
                "fallback_used": True,
                "error": str(error),
                "raw_response": ""
            }
        )

    def _load_config(self) -> ReviewerConfig:
        try:
            cfg_map = self.redis.hgetall(self.config_key) or {}
            conf_threshold = float(cfg_map.get("conf_threshold", DEFAULT_CONF_THRESHOLD))
            heavy_enabled = str(cfg_map.get("heavy_enabled", str(DEFAULT_HEAVY_ENABLED))).lower() in ("1", "true", "yes")
            light_model = cfg_map.get("light_model", DEFAULT_LIGHT_MODEL)
            heavy_model = cfg_map.get("heavy_model", DEFAULT_HEAVY_MODEL)
            light_workers = int(cfg_map.get("light_workers", 1))
            return ReviewerConfig(
                conf_threshold=conf_threshold,
                heavy_enabled=heavy_enabled,
                light_model=light_model,
                heavy_model=heavy_model,
                light_workers=light_workers
            )
        except Exception:
            return ReviewerConfig()

    def _record_latency(self, which: str, ms: float) -> None:
        try:
            key = self.lat_list_light if which == "light" else self.lat_list_heavy
            self.redis.lpush(key, f"{int(datetime.utcnow().timestamp())}|{int(ms)}")
            self.redis.ltrim(key, 0, 4999)
        except Exception:
            pass

    def _record_error(self, message: str) -> None:
        try:
            self.redis.lpush(self.err_list, f"{int(datetime.utcnow().timestamp())}|{message[:200]}")
            self.redis.ltrim(self.err_list, 0, 999)
        except Exception:
            pass

    def _record_confidence(self, confidence: float) -> None:
        try:
            bucket = max(0, min(19, int(confidence / 0.05)))
            bucket_label = f"{bucket*0.05:.2f}-{(bucket+1)*0.05:.2f}"
            self.redis.hincrby(self.conf_hist, bucket_label, 1)
        except Exception:
            pass


# Initialize services
article_reviewer = ArticleReviewer()

# Create tables on startup
@app.on_event("startup")
async def startup_event():
    create_tables()
    logger.info("Reviewer Service started")


@app.get("/health")
async def health_check():
    """Health check endpoint with avg latency."""
    r = article_reviewer.redis
    try:
        light_lat = _avg_latency_ms(r, article_reviewer.lat_list_light, window_seconds=300)
        heavy_lat = _avg_latency_ms(r, article_reviewer.lat_list_heavy, window_seconds=300)
    except Exception:
        light_lat = heavy_lat = 0.0
    cfg = article_reviewer._load_config()
    return {
        "status": "ok",
        "service": "reviewer",
        "model_light": cfg.light_model,
        "model_heavy": cfg.heavy_model,
        "avg_latency_ms": {"light": light_lat, "heavy": heavy_lat},
        "timestamp": datetime.utcnow()
    }


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
        result = await article_reviewer.review_article(article)
        review: ArticleReview = result["review"]
        reviewer_type: str = result["reviewer_type"]
        fallback_used: bool = result["fallback"]
        timings = result.get("timings", {})

        # Persist review on Article (transactional: store once)
        article.review_tags = review.tags
        article.review_summary = review.summary
        article.confidence = review.confidence
        article.reviewer_type = reviewer_type
        article.processed_at = datetime.utcnow()
        # Compute fingerprint if missing
        try:
            if not getattr(article, "fingerprint", None):
                import hashlib
                pub_iso = article.publish_date.isoformat() if article.publish_date else ""
                to_hash = f"{article.link}|{article.title}|{pub_iso}".encode("utf-8", errors="ignore")
                article.fingerprint = hashlib.sha256(to_hash).hexdigest()
        except Exception:
            pass
        # Store metadata
        meta = dict(review.review_metadata or {})
        meta.update({"fallback": fallback_used, "timings_ms": timings})
        article.review_metadata = meta
        db.commit()

        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        logger.info(f"Successfully reviewed article {request.article_id} ({reviewer_type})")
        
        return ReviewResponse(
            article_id=request.article_id,
            review=review,
            processing_time_seconds=processing_time,
            reviewer_type=reviewer_type,
            fallback=fallback_used
        )
        
    except Exception as e:
        logger.error(f"Error reviewing article {request.article_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Article review failed: {str(e)}")
@app.post("/review")
async def review_feed(request: FeedReviewRequest):
    """Review a feed item (stateless) and return tags/summary/confidence."""
    # Build transient Article-like object
    dummy = Article(
        id=UUID("00000000-0000-0000-0000-000000000000"),
        feed_id=UUID("00000000-0000-0000-0000-000000000000"),
        title=request.title,
        link=request.url,
        summary=request.content or "",
        content=request.content or "",
        publish_date=datetime.fromisoformat(request.published.replace("Z", "+00:00")) if request.published else None
    )
    result = await article_reviewer.review_article(dummy)
    review: ArticleReview = result["review"]
    cfg = article_reviewer._load_config()
    return {
        "tags": review.tags,
        "summary": review.summary,
        "confidence": review.confidence,
        "model": review.review_metadata.get("model_used", cfg.light_model),
        "reviewer_type": result.get("reviewer_type", "light"),
    }


@app.get("/config", response_model=ReviewerConfig)
async def get_config():
    return article_reviewer._load_config()


@app.put("/config", response_model=ReviewerConfig)
async def put_config(cfg: ReviewerConfig):
    r = article_reviewer.redis
    try:
        r.hset(article_reviewer.config_key, mapping={
            "conf_threshold": cfg.conf_threshold,
            "heavy_enabled": int(cfg.heavy_enabled),
            "light_model": cfg.light_model,
            "heavy_model": cfg.heavy_model,
            "light_workers": cfg.light_workers,
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save config: {e}")
    return article_reviewer._load_config()


@app.get("/metrics", response_model=MetricsResponse)
async def get_metrics():
    r = article_reviewer.redis
    hist = r.hgetall(article_reviewer.conf_hist) or {}
    # Windows: last 5 minutes and 1 hour
    last_5m = _window_metrics(r, 300, hist)
    last_1h = _window_metrics(r, 3600, hist)
    qlen = 0
    try:
        qlen = r.llen(article_reviewer.queue_key)
    except Exception:
        pass
    return MetricsResponse(last_5m=last_5m, last_1h=last_1h, queue_length=qlen)


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
        
        result = await article_reviewer.review_article(test_article)
        review = result["review"]
        
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
        
        result = await article_reviewer.review_article(article)
        review: ArticleReview = result["review"]
        reviewer_type = result["reviewer_type"]
        logger.info(f"Background review completed for article {article_id}: {review.topic}/{review.subject} ({reviewer_type})")
        # Persist minimal fields
        article.review_tags = review.tags
        article.review_summary = review.summary
        article.confidence = review.confidence
        article.reviewer_type = reviewer_type
        article.processed_at = datetime.utcnow()
        db.commit()
        
    except Exception as e:
        logger.error(f"Error in background review for article {article_id}: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8007)


# Helper functions (module-level)
def _avg_latency_ms(r: redis.Redis, list_key: str, window_seconds: int) -> float:
    try:
        now = int(datetime.utcnow().timestamp())
        entries = r.lrange(list_key, 0, 999)
        vals = []
        for e in entries:
            try:
                ts_s, ms_s = e.split("|", 1)
                if now - int(ts_s) <= window_seconds:
                    vals.append(int(ms_s))
            except Exception:
                continue
        if not vals:
            return 0.0
        return sum(vals) / len(vals)
    except Exception:
        return 0.0


def _window_metrics(r: redis.Redis, window_seconds: int, hist: Dict[str, str]) -> MetricsWindow:
    now = int(datetime.utcnow().timestamp())
    def _count_and_avg(list_key: str) -> (int, float):
        entries = r.lrange(list_key, 0, 1999)
        vals = []
        for e in entries:
            try:
                ts_s, ms_s = e.split("|", 1)
                if now - int(ts_s) <= window_seconds:
                    vals.append(int(ms_s))
            except Exception:
                continue
        if not vals:
            return 0, 0.0
        return len(vals), sum(vals) / len(vals)

    light_count, light_avg = _count_and_avg(article_reviewer.lat_list_light)
    heavy_count, heavy_avg = _count_and_avg(article_reviewer.lat_list_heavy)
    err_entries = r.lrange(article_reviewer.err_list, 0, 999)
    errors = 0
    for e in err_entries:
        try:
            ts_s, _ = e.split("|", 1)
            if now - int(ts_s) <= window_seconds:
                errors += 1
        except Exception:
            continue
    total = light_count + heavy_count + errors
    success = light_count + heavy_count
    success_rate = (success / total) if total else 1.0
    error_rate = (errors / total) if total else 0.0
    # Confidence histogram: return raw stored counts
    conf_hist = {k: int(v) for k, v in (hist or {}).items()}
    return MetricsWindow(
        total_light=light_count,
        total_heavy=heavy_count,
        avg_latency_ms_light=light_avg,
        avg_latency_ms_heavy=heavy_avg,
        success_rate=success_rate,
        error_rate=error_rate,
        confidence_histogram=conf_hist,
    )