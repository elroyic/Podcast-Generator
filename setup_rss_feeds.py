#!/usr/bin/env python3
"""
Setup script to add the 34 RSS feeds specified in the Workflow.md document.
This script will populate the news_feeds table with all the required RSS feeds.
"""

import asyncio
import httpx
import logging
from datetime import datetime
from typing import List, Dict

from shared.database import get_db, create_tables
from shared.models import NewsFeed, FeedType

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# RSS feeds from Workflow.md
RSS_FEEDS = [
    {"name": "MarketWatch", "url": "https://feeds.content.dowjones.io/public/rss/marketwatch/markets"},
    {"name": "Investing.com", "url": "https://www.investing.com/rss/news.rss"},
    {"name": "CNBC", "url": "https://search.cnbc.com/rs/search/company-news/rss"},
    {"name": "Seeking Alpha", "url": "https://seekingalpha.com/feed.xml"},
    {"name": "The Motley Fool UK", "url": "https://www.fool.co.uk/feed"},
    {"name": "INO.com Blog", "url": "https://ino.com/blog/feed"},
    {"name": "AlphaStreet", "url": "https://news.alphastreet.com/feed"},
    {"name": "Raging Bull", "url": "https://ragingbull.com/feed"},
    {"name": "Moneycontrol", "url": "https://www.moneycontrol.com/rss/latestnews.xml"},
    {"name": "Scanz Blog", "url": "https://scanz.com/feed"},
    {"name": "Market Screener", "url": "https://www.marketscreener.com/rss"},
    {"name": "Investors Business Daily", "url": "https://www.investors.com/Home/SliderRss"},
    {"name": "Yahoo Finance", "url": "https://finance.yahoo.com/rss"},
    {"name": "IIFL Securities", "url": "https://www.indiainfoline.com/news/rss"},
    {"name": "Nasdaq", "url": "https://www.nasdaq.com/feed/rss"},
    {"name": "Stock Market.com", "url": "https://stockmarket.com/rss"},
    {"name": "Equitymaster", "url": "https://www.equitymaster.com/feed"},
    {"name": "KlickAnalytics", "url": "https://klickanalytics.com/rss"},
    {"name": "BBC News – Top Stories", "url": "https://feeds.bbci.co.uk/news/rss.xml"},
    {"name": "CNN – Top Stories", "url": "http://rss.cnn.com/rss/edition.rss"},
    {"name": "Reuters – World News", "url": "http://feeds.reuters.com/Reuters/worldNews"},
    {"name": "The Guardian – World", "url": "https://www.theguardian.com/world/rss"},
    {"name": "Al Jazeera – All News", "url": "https://www.aljazeera.com/xml/rss/all.xml"},
    {"name": "Associated Press (AP)", "url": "https://apnews.com/rss"},
    {"name": "NPR News", "url": "https://feeds.npr.org/1001/rss.xml"},
    {"name": "DW News (Deutsche Welle)", "url": "https://rss.dw.com/rdf/rss-en-all"},
    {"name": "Politico – Politics", "url": "https://www.politico.com/rss/politics08.xml"},
    {"name": "New York Times – Home Page", "url": "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml"},
    {"name": "Reuters Top News", "url": "https://feeds.reuters.com/reuters/topNews"},
    {"name": "BBC News World", "url": "https://feeds.bbci.co.uk/news/world/rss.xml"},
    {"name": "The New York Times Home Page", "url": "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml"},
    {"name": "Al Jazeera All News", "url": "https://www.aljazeera.com/xml/rss/all.xml"},
    {"name": "Associated Press Top Stories", "url": "https://apnews.com/rss"},
    {"name": "NPR News Top Stories", "url": "https://feeds.npr.org/1001/rss.xml"},
]


async def test_feed_accessibility(feed_url: str) -> bool:
    """Test if a feed URL is accessible."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(feed_url)
            return response.status_code == 200
    except Exception as e:
        logger.warning(f"Feed {feed_url} not accessible: {e}")
        return False


async def setup_rss_feeds():
    """Setup all RSS feeds in the database."""
    logger.info("Starting RSS feeds setup...")
    
    # Create tables
    create_tables()
    
    # Get database session
    db = next(get_db())
    
    try:
        # Test feed accessibility first
        accessible_feeds = []
        for feed_data in RSS_FEEDS:
            logger.info(f"Testing accessibility of {feed_data['name']}...")
            if await test_feed_accessibility(feed_data['url']):
                accessible_feeds.append(feed_data)
                logger.info(f"✓ {feed_data['name']} is accessible")
            else:
                logger.warning(f"✗ {feed_data['name']} is not accessible")
        
        logger.info(f"Found {len(accessible_feeds)} accessible feeds out of {len(RSS_FEEDS)} total")
        
        # Add accessible feeds to database
        added_count = 0
        for feed_data in accessible_feeds:
            # Check if feed already exists
            existing_feed = db.query(NewsFeed).filter(
                NewsFeed.source_url == feed_data['url']
            ).first()
            
            if not existing_feed:
                feed = NewsFeed(
                    source_url=feed_data['url'],
                    name=feed_data['name'],
                    type=FeedType.RSS,
                    is_active=True
                )
                db.add(feed)
                added_count += 1
                logger.info(f"Added feed: {feed_data['name']}")
            else:
                logger.info(f"Feed already exists: {feed_data['name']}")
        
        db.commit()
        logger.info(f"Successfully added {added_count} new RSS feeds to the database")
        
        # List all feeds in database
        all_feeds = db.query(NewsFeed).filter(NewsFeed.type == FeedType.RSS).all()
        logger.info(f"Total RSS feeds in database: {len(all_feeds)}")
        
        for feed in all_feeds:
            logger.info(f"  - {feed.name}: {feed.source_url}")
        
    except Exception as e:
        logger.error(f"Error setting up RSS feeds: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(setup_rss_feeds())