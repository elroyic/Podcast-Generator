"""
News Feed Service - Handles RSS/MCP feed fetching and article storage.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

import feedparser
import httpx
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import and_

from shared.database import get_db, create_tables
from shared.models import NewsFeed, Article, FeedType
from shared.schemas import NewsFeedCreate, NewsFeedUpdate, NewsFeed as NewsFeedSchema, Article as ArticleSchema

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="News Feed Service", version="1.0.0")

# Create tables on startup
@app.on_event("startup")
async def startup_event():
    create_tables()
    logger.info("News Feed Service started")


class NewsFeedProcessor:
    """Handles RSS feed processing and article extraction."""
    
    @staticmethod
    async def fetch_rss_feed(feed_url: str) -> List[dict]:
        """Fetch and parse RSS feed."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(feed_url)
                response.raise_for_status()
                
                # Parse RSS feed
                parsed = feedparser.parse(response.content)
                
                articles = []
                for entry in parsed.entries:
                    article = {
                        "title": entry.get("title", ""),
                        "link": entry.get("link", ""),
                        "summary": entry.get("summary", "") or entry.get("description", ""),
                        "content": entry.get("content", [{}])[0].get("value", "") if entry.get("content") else "",
                        "publish_date": None
                    }
                    
                    # Parse publish date
                    if hasattr(entry, "published_parsed") and entry.published_parsed:
                        article["publish_date"] = datetime(*entry.published_parsed[:6])
                    elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                        article["publish_date"] = datetime(*entry.updated_parsed[:6])
                    
                    articles.append(article)
                
                return articles
                
        except Exception as e:
            logger.error(f"Error fetching RSS feed {feed_url}: {e}")
            return []
    
    @staticmethod
    async def fetch_mcp_feed(feed_url: str) -> List[dict]:
        """Fetch and parse MCP feed."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(feed_url)
                response.raise_for_status()
                
                # Parse MCP feed (Model Context Protocol)
                # MCP feeds typically return JSON with structured data
                try:
                    mcp_data = response.json()
                    articles = []
                    
                    # Handle different MCP feed formats
                    if isinstance(mcp_data, dict):
                        # Check for common MCP feed structures
                        if "items" in mcp_data:
                            items = mcp_data["items"]
                        elif "articles" in mcp_data:
                            items = mcp_data["articles"]
                        elif "data" in mcp_data:
                            items = mcp_data["data"]
                        else:
                            # Try to extract articles from the root object
                            items = [mcp_data] if mcp_data else []
                    elif isinstance(mcp_data, list):
                        items = mcp_data
                    else:
                        logger.warning(f"Unexpected MCP feed format: {type(mcp_data)}")
                        return []
                    
                    for item in items:
                        if not isinstance(item, dict):
                            continue
                            
                        article = {
                            "title": item.get("title", item.get("headline", "")),
                            "link": item.get("url", item.get("link", "")),
                            "summary": item.get("summary", item.get("description", item.get("excerpt", ""))),
                            "content": item.get("content", item.get("body", "")),
                            "publish_date": None
                        }
                        
                        # Parse publish date from various formats
                        pub_date = item.get("published_at", item.get("date", item.get("created_at")))
                        if pub_date:
                            try:
                                from datetime import datetime
                                if isinstance(pub_date, str):
                                    # Try different date formats
                                    for fmt in ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%Y-%m-%d %H:%M:%S"]:
                                        try:
                                            article["publish_date"] = datetime.strptime(pub_date, fmt)
                                            break
                                        except ValueError:
                                            continue
                                elif isinstance(pub_date, (int, float)):
                                    # Unix timestamp
                                    article["publish_date"] = datetime.fromtimestamp(pub_date)
                            except Exception as e:
                                logger.warning(f"Could not parse date {pub_date}: {e}")
                        
                        articles.append(article)
                    
                    return articles
                    
                except ValueError as e:
                    logger.error(f"Error parsing MCP JSON feed {feed_url}: {e}")
                    # Fallback to RSS parsing
                    return await NewsFeedProcessor.fetch_rss_feed(feed_url)
                
        except Exception as e:
            logger.error(f"Error fetching MCP feed {feed_url}: {e}")
            return []


# API Endpoints

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "news-feed", "timestamp": datetime.utcnow()}


@app.post("/feeds", response_model=NewsFeedSchema)
async def create_news_feed(
    feed_data: NewsFeedCreate,
    db: Session = Depends(get_db)
):
    """Create a new news feed."""
    db_feed = NewsFeed(
        source_url=feed_data.source_url,
        name=feed_data.name,
        type=feed_data.type,
        is_active=feed_data.is_active
    )
    db.add(db_feed)
    db.commit()
    db.refresh(db_feed)
    
    # Trigger initial fetch
    asyncio.create_task(fetch_feed_articles(db_feed.id))
    
    return db_feed


@app.get("/feeds", response_model=List[NewsFeedSchema])
async def list_news_feeds(
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    """List all news feeds."""
    query = db.query(NewsFeed)
    if active_only:
        query = query.filter(NewsFeed.is_active == True)
    
    return query.all()


@app.get("/feeds/{feed_id}", response_model=NewsFeedSchema)
async def get_news_feed(
    feed_id: UUID,
    db: Session = Depends(get_db)
):
    """Get a specific news feed."""
    feed = db.query(NewsFeed).filter(NewsFeed.id == feed_id).first()
    if not feed:
        raise HTTPException(status_code=404, detail="News feed not found")
    return feed


@app.put("/feeds/{feed_id}", response_model=NewsFeedSchema)
async def update_news_feed(
    feed_id: UUID,
    feed_data: NewsFeedUpdate,
    db: Session = Depends(get_db)
):
    """Update a news feed."""
    feed = db.query(NewsFeed).filter(NewsFeed.id == feed_id).first()
    if not feed:
        raise HTTPException(status_code=404, detail="News feed not found")
    
    update_data = feed_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(feed, field, value)
    
    db.commit()
    db.refresh(feed)
    return feed


@app.delete("/feeds/{feed_id}")
async def delete_news_feed(
    feed_id: UUID,
    db: Session = Depends(get_db)
):
    """Delete a news feed."""
    feed = db.query(NewsFeed).filter(NewsFeed.id == feed_id).first()
    if not feed:
        raise HTTPException(status_code=404, detail="News feed not found")
    
    db.delete(feed)
    db.commit()
    return {"message": "News feed deleted successfully"}


@app.post("/feeds/{feed_id}/fetch")
async def trigger_feed_fetch(
    feed_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Manually trigger fetching of articles from a feed."""
    feed = db.query(NewsFeed).filter(NewsFeed.id == feed_id).first()
    if not feed:
        raise HTTPException(status_code=404, detail="News feed not found")
    
    background_tasks.add_task(fetch_feed_articles, feed_id)
    return {"message": "Feed fetch triggered"}


@app.get("/articles", response_model=List[ArticleSchema])
async def list_articles(
    feed_id: Optional[UUID] = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """List articles, optionally filtered by feed."""
    query = db.query(Article)
    
    if feed_id:
        query = query.filter(Article.feed_id == feed_id)
    
    return query.order_by(Article.publish_date.desc()).offset(offset).limit(limit).all()


@app.get("/feeds/{feed_id}/articles", response_model=List[ArticleSchema])
async def get_feed_articles(
    feed_id: UUID,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get articles from a specific feed."""
    feed = db.query(NewsFeed).filter(NewsFeed.id == feed_id).first()
    if not feed:
        raise HTTPException(status_code=404, detail="News feed not found")
    
    return db.query(Article).filter(Article.feed_id == feed_id)\
        .order_by(Article.publish_date.desc()).limit(limit).all()


@app.get("/articles/recent", response_model=List[ArticleSchema])
async def get_recent_articles(
    hours: int = 24,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get recent articles from all feeds."""
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
    
    return db.query(Article).filter(Article.publish_date >= cutoff_time)\
        .order_by(Article.publish_date.desc()).limit(limit).all()


async def fetch_feed_articles(feed_id: UUID):
    """Background task to fetch articles from a feed."""
    db = next(get_db())
    try:
        feed = db.query(NewsFeed).filter(NewsFeed.id == feed_id).first()
        if not feed or not feed.is_active:
            return
        
        logger.info(f"Fetching articles from feed: {feed.source_url}")
        
        # Fetch articles based on feed type
        if feed.type == FeedType.RSS:
            articles_data = await NewsFeedProcessor.fetch_rss_feed(feed.source_url)
        elif feed.type == FeedType.MCP:
            articles_data = await NewsFeedProcessor.fetch_mcp_feed(feed.source_url)
        else:
            logger.error(f"Unknown feed type: {feed.type}")
            return
        
        # Store new articles
        new_articles_count = 0
        for article_data in articles_data:
            # Check if article already exists
            existing = db.query(Article).filter(
                and_(
                    Article.feed_id == feed_id,
                    Article.link == article_data["link"]
                )
            ).first()
            
            if not existing:
                article = Article(
                    feed_id=feed_id,
                    title=article_data["title"],
                    link=article_data["link"],
                    summary=article_data["summary"],
                    content=article_data["content"],
                    publish_date=article_data["publish_date"]
                )
                db.add(article)
                new_articles_count += 1
        
        # Update last_fetched timestamp
        feed.last_fetched = datetime.utcnow()
        
        db.commit()
        logger.info(f"Fetched {new_articles_count} new articles from {feed.source_url}")
        
    except Exception as e:
        logger.error(f"Error fetching articles for feed {feed_id}: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)