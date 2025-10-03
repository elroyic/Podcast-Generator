#!/usr/bin/env python3
"""
Script to set up test data for the podcast generation system.
"""

import asyncio
import json
import logging
import httpx

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def setup_test_data():
    """Set up test data including presenter, writer, news feed, and podcast group."""
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            # Step 1: Create presenter
            logger.info("👤 Creating presenter...")
            presenter_data = {
                "name": "Alex Weather",
                "bio": "A friendly weather enthusiast who loves talking about seasonal changes",
                "gender": "non-binary",
                "country": "US",
                "city": "San Francisco",
                "specialties": ["weather", "nature", "seasonal topics"],
                "expertise": ["meteorology", "climate science"],
                "interests": ["outdoor activities", "gardening", "seasonal changes"]
            }
            
            presenter_response = await client.post(
                "http://localhost:8000/api/presenters",
                json=presenter_data
            )
            presenter = presenter_response.json()
            logger.info(f"✅ Created presenter: {presenter['name']} (ID: {presenter['id']})")
            
            # Step 2: Create writer
            logger.info("✍️ Creating writer...")
            writer_data = {
                "name": "Spring Content Writer",
                "capabilities": ["title", "description", "tags", "keywords", "category", "script"]
            }
            
            writer_response = await client.post(
                "http://localhost:8000/api/writers",
                json=writer_data
            )
            writer = writer_response.json()
            logger.info(f"✅ Created writer: {writer['name']} (ID: {writer['id']})")
            
            # Step 3: Create news feed
            logger.info("📰 Creating news feed...")
            feed_data = {
                "source_url": "https://weather.com/news/rss.xml",
                "name": "Weather News Feed",
                "type": "RSS",
                "is_active": True
            }
            
            feed_response = await client.post(
                "http://localhost:8000/api/news-feeds",
                json=feed_data
            )
            feed = feed_response.json()
            logger.info(f"✅ Created news feed: {feed['name']} (ID: {feed['id']})")
            
            # Step 4: Create podcast group
            logger.info("🎙️ Creating podcast group...")
            group_data = {
                "name": "Spring Weather Podcast",
                "description": "A podcast about spring weather patterns and seasonal changes",
                "category": "Weather",
                "presenter_ids": [presenter['id']],
                "writer_id": writer['id'],
                "news_feed_ids": [feed['id']]
            }
            
            group_response = await client.post(
                "http://localhost:8000/api/podcast-groups",
                json=group_data
            )
            group = group_response.json()
            logger.info(f"✅ Created podcast group: {group['name']} (ID: {group['id']})")
            
            # Save the group ID for later use
            with open("test_group_id.txt", "w") as f:
                f.write(group['id'])
            
            logger.info("🎉 Test data setup completed successfully!")
            return group['id']
            
        except Exception as e:
            logger.error(f"❌ Error setting up test data: {e}")
            return None

if __name__ == "__main__":
    group_id = asyncio.run(setup_test_data())
    if group_id:
        logger.info(f"📝 Group ID saved: {group_id}")
    else:
        logger.error("❌ Failed to set up test data")

