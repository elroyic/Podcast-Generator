"""
Simplified News Feed Service for local testing.
This version creates mock articles without fetching real feeds.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="News Feed Service (Simple)", version="1.0.0")


class NewsFeedCreate(BaseModel):
    source_url: str
    name: Optional[str] = None
    type: str = "RSS"
    is_active: bool = True


class NewsFeed(BaseModel):
    id: UUID
    source_url: str
    name: Optional[str] = None
    type: str
    is_active: bool
    last_fetched: Optional[datetime] = None
    created_at: datetime


class Article(BaseModel):
    id: UUID
    feed_id: UUID
    title: str
    link: str
    summary: Optional[str] = None
    content: Optional[str] = None
    publish_date: Optional[datetime] = None
    created_at: datetime


# In-memory storage for testing
mock_feeds = []
mock_articles = []


def generate_mock_articles(feed_id: UUID, count: int = 5) -> List[Article]:
    """Generate mock articles for a feed."""
    
    mock_titles = [
        "Breaking: New AI Technology Revolutionizes Industry",
        "Tech Giants Announce Major Partnership Deal",
        "Scientists Discover Breakthrough in Quantum Computing",
        "Startup Raises $50M in Series A Funding",
        "New Software Update Improves Performance by 300%",
        "Cybersecurity Experts Warn of New Threats",
        "Mobile App Downloads Reach Record High",
        "Cloud Computing Market Sees Unprecedented Growth"
    ]
    
    articles = []
    for i in range(count):
        title = mock_titles[i % len(mock_titles)]
        article = Article(
            id=uuid4(),
            feed_id=feed_id,
            title=title,
            link=f"https://example.com/article/{uuid4()}",
            summary=f"This is a summary of the article: {title}. It covers important developments in the technology sector.",
            content=f"Full content of the article: {title}. This would contain the complete article text in a real implementation.",
            publish_date=datetime.utcnow() - timedelta(hours=i),
            created_at=datetime.utcnow()
        )
        articles.append(article)
        mock_articles.append(article)
    
    return articles


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "news-feed-simple", "timestamp": datetime.utcnow()}


@app.post("/feeds", response_model=NewsFeed)
async def create_news_feed(feed_data: NewsFeedCreate):
    """Create a new news feed."""
    
    feed = NewsFeed(
        id=uuid4(),
        source_url=feed_data.source_url,
        name=feed_data.name or f"Feed {len(mock_feeds) + 1}",
        type=feed_data.type,
        is_active=feed_data.is_active,
        created_at=datetime.utcnow()
    )
    
    mock_feeds.append(feed)
    
    # Generate mock articles for the feed
    articles = generate_mock_articles(feed.id)
    
    logger.info(f"Created feed {feed.name} with {len(articles)} mock articles")
    
    return feed


@app.get("/feeds", response_model=List[NewsFeed])
async def list_news_feeds(active_only: bool = True):
    """List all news feeds."""
    
    if active_only:
        return [feed for feed in mock_feeds if feed.is_active]
    return mock_feeds


@app.get("/feeds/{feed_id}", response_model=NewsFeed)
async def get_news_feed(feed_id: UUID):
    """Get a specific news feed."""
    
    for feed in mock_feeds:
        if feed.id == feed_id:
            return feed
    
    raise HTTPException(status_code=404, detail="News feed not found")


@app.get("/articles", response_model=List[Article])
async def list_articles(feed_id: Optional[UUID] = None, limit: int = 100):
    """List articles, optionally filtered by feed."""
    
    if feed_id:
        articles = [article for article in mock_articles if article.feed_id == feed_id]
    else:
        articles = mock_articles
    
    return articles[:limit]


@app.get("/feeds/{feed_id}/articles", response_model=List[Article])
async def get_feed_articles(feed_id: UUID, limit: int = 100):
    """Get articles from a specific feed."""
    
    # Check if feed exists
    feed_exists = any(feed.id == feed_id for feed in mock_feeds)
    if not feed_exists:
        raise HTTPException(status_code=404, detail="News feed not found")
    
    articles = [article for article in mock_articles if article.feed_id == feed_id]
    return articles[:limit]


@app.get("/articles/recent", response_model=List[Article])
async def get_recent_articles(hours: int = 24, limit: int = 50):
    """Get recent articles from all feeds."""
    
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
    recent_articles = [
        article for article in mock_articles 
        if article.publish_date and article.publish_date >= cutoff_time
    ]
    
    # Sort by publish date (newest first)
    recent_articles.sort(key=lambda x: x.publish_date or datetime.min, reverse=True)
    
    return recent_articles[:limit]


@app.post("/feeds/{feed_id}/fetch")
async def trigger_feed_fetch(feed_id: UUID):
    """Manually trigger fetching of articles from a feed."""
    
    # Find the feed
    feed = None
    for f in mock_feeds:
        if f.id == feed_id:
            feed = f
            break
    
    if not feed:
        raise HTTPException(status_code=404, detail="News feed not found")
    
    # Generate new mock articles
    new_articles = generate_mock_articles(feed_id, count=3)
    
    # Update last_fetched timestamp
    feed.last_fetched = datetime.utcnow()
    
    logger.info(f"Fetched {len(new_articles)} new articles for feed {feed.name}")
    
    return {
        "message": f"Fetched {len(new_articles)} new articles",
        "articles_count": len(new_articles)
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)