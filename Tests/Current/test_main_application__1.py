#!/usr/bin/env python3
"""
Test the main application workflow for episode generation.
"""

import asyncio
import json
import logging
from uuid import uuid4
import httpx

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_main_application():
    """Test the main application episode generation workflow."""
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            # Step 1: Check system health
            logger.info("🔍 Checking system health...")
            health_response = await client.get("http://localhost:8000/health")
            health_data = health_response.json()
            logger.info(f"System status: {health_data.get('status', 'unknown')}")
            
            # Step 2: Create test data through the main API
            logger.info("👤 Creating presenter...")
            presenter_data = {
                "name": "Alex Weather",
                "bio": "A friendly weather enthusiast who loves talking about seasonal changes",
                "gender": "non-binary",
                "country": "US",
                "city": "San Francisco"
            }
            
            presenter_response = await client.post(
                "http://localhost:8000/api/presenters",
                json=presenter_data
            )
            presenter = presenter_response.json()
            logger.info(f"✅ Created presenter: {presenter['name']} (ID: {presenter['id']})")
            
            # Step 3: Create writer
            logger.info("✍️ Creating writer...")
            writer_data = {
                "name": "Spring Content Writer",
                "capabilities": ["title", "description", "tags", "keywords", "category"]
            }
            
            writer_response = await client.post(
                "http://localhost:8000/api/writers",
                json=writer_data
            )
            writer = writer_response.json()
            logger.info(f"✅ Created writer: {writer['name']} (ID: {writer['id']})")
            
            # Step 4: Create news feed
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
            
            # Step 5: Create podcast group
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
            
            # Step 6: Generate episode through the main workflow
            logger.info("🎬 Generating episode through main application...")
            episode_request = {
                "group_id": group['id'],
                "force_regenerate": False
            }
            
            episode_response = await client.post(
                "http://localhost:8000/api/generate-episode",
                json=episode_request
            )
            
            if episode_response.status_code == 200:
                episode_result = episode_response.json()
                logger.info("✅ Episode generation successful!")
                logger.info(f"📋 Response: {json.dumps(episode_result, indent=2)}")
                return True
            else:
                logger.error(f"❌ Episode generation failed: {episode_response.status_code}")
                logger.error(f"Response: {episode_response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error in main application test: {e}")
            return False

if __name__ == "__main__":
    success = asyncio.run(test_main_application())
    if success:
        logger.info("🎉 Main application test completed successfully!")
    else:
        logger.error("❌ Main application test failed!")

