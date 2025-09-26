#!/usr/bin/env python3
"""
Setup script to add the 34 RSS feeds from Workflow.md to the system.
This script creates news feeds in the database for all the specified RSS sources.
"""
import asyncio
import httpx
import logging
from typing import List, Dict

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

# API Gateway URL
API_GATEWAY_URL = "http://localhost:8000"


async def create_news_feed(client: httpx.AsyncClient, feed_data: Dict[str, str]) -> bool:
    """Create a news feed via the API."""
    try:
        payload = {
            "source_url": feed_data["url"],
            "name": feed_data["name"],
            "type": "RSS",
            "is_active": True
        }
        
        response = await client.post(
            f"{API_GATEWAY_URL}/api/news-feeds",
            json=payload,
            timeout=30.0
        )
        
        if response.status_code == 200:
            logger.info(f"✅ Created feed: {feed_data['name']}")
            return True
        else:
            logger.error(f"❌ Failed to create feed {feed_data['name']}: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error creating feed {feed_data['name']}: {e}")
        return False


async def check_existing_feeds(client: httpx.AsyncClient) -> List[str]:
    """Check which feeds already exist."""
    try:
        response = await client.get(f"{API_GATEWAY_URL}/api/news-feeds", timeout=30.0)
        if response.status_code == 200:
            existing_feeds = response.json()
            return [feed["source_url"] for feed in existing_feeds]
        else:
            logger.warning(f"Could not check existing feeds: {response.status_code}")
            return []
    except Exception as e:
        logger.warning(f"Error checking existing feeds: {e}")
        return []


async def main():
    """Main function to set up RSS feeds."""
    logger.info("🚀 Starting RSS feeds setup...")
    
    async with httpx.AsyncClient() as client:
        # Check existing feeds
        logger.info("📋 Checking existing feeds...")
        existing_urls = await check_existing_feeds(client)
        
        # Filter out existing feeds
        new_feeds = [feed for feed in RSS_FEEDS if feed["url"] not in existing_urls]
        
        if not new_feeds:
            logger.info("✅ All RSS feeds already exist in the system!")
            return
        
        logger.info(f"📝 Found {len(new_feeds)} new feeds to create out of {len(RSS_FEEDS)} total feeds")
        
        # Create new feeds
        success_count = 0
        for feed_data in new_feeds:
            success = await create_news_feed(client, feed_data)
            if success:
                success_count += 1
            
            # Small delay to avoid overwhelming the API
            await asyncio.sleep(0.5)
        
        logger.info(f"🎉 Setup complete! Created {success_count}/{len(new_feeds)} new feeds")
        
        # Show summary
        total_feeds = len(existing_urls) + success_count
        logger.info(f"📊 Total feeds in system: {total_feeds}")
        
        if success_count < len(new_feeds):
            failed_count = len(new_feeds) - success_count
            logger.warning(f"⚠️  {failed_count} feeds failed to create. Check the logs above for details.")


if __name__ == "__main__":
    asyncio.run(main())