#!/usr/bin/env python3
"""
Test script for full podcast generation workflow.
Tests all services in order: AI Overseer -> Writer -> Presenter
"""

import asyncio
import json
import logging
import requests
import time
from typing import Dict, Any, List
from uuid import UUID, uuid4

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API Gateway URL
API_BASE_URL = "http://localhost:8000"

class PodcastTestClient:
    """Client for testing podcast generation services."""
    
    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request to API Gateway."""
        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise
    
    def create_presenter(self, name: str, bio: str, gender: str = "neutral") -> Dict[str, Any]:
        """Create a presenter."""
        presenter_data = {
            "name": name,
            "bio": bio,
            "gender": gender,
            "country": "US",
            "city": "New York",
            "specialties": ["technology", "podcasting"],
            "expertise": ["AI", "software development"],
            "interests": ["tech news", "innovation"]
        }
        return self._make_request("POST", "/api/presenters", json=presenter_data)
    
    def create_writer(self, name: str = "AI Writer") -> Dict[str, Any]:
        """Create a writer."""
        writer_data = {
            "name": name,
            "capabilities": ["title", "description", "tags", "keywords", "category", "subcategory"]
        }
        return self._make_request("POST", "/api/writers", json=writer_data)
    
    def create_news_feed(self, name: str, url: str) -> Dict[str, Any]:
        """Create a news feed."""
        feed_data = {
            "name": name,
            "source_url": url,
            "type": "RSS",
            "is_active": True
        }
        return self._make_request("POST", "/api/news-feeds", json=feed_data)
    
    def create_podcast_group(
        self, 
        name: str, 
        description: str, 
        presenter_ids: List[str], 
        writer_id: str, 
        news_feed_ids: List[str]
    ) -> Dict[str, Any]:
        """Create a podcast group."""
        group_data = {
            "name": name,
            "description": description,
            "category": "Technology",
            "subcategory": "AI News",
            "language": "en",
            "country": "US",
            "tags": ["AI", "technology", "news"],
            "keywords": ["artificial intelligence", "machine learning", "tech news"],
            "schedule": "0 9 * * 1",  # Every Monday at 9 AM
            "status": "active",
            "presenter_ids": presenter_ids,
            "writer_id": writer_id,
            "news_feed_ids": news_feed_ids
        }
        return self._make_request("POST", "/api/podcast-groups", json=group_data)
    
    def generate_episode(self, group_id: str) -> Dict[str, Any]:
        """Generate an episode for a podcast group."""
        request_data = {
            "group_id": group_id
        }
        return self._make_request("POST", "/api/generate-episode", json=request_data)
    
    def get_episode(self, episode_id: str) -> Dict[str, Any]:
        """Get episode details."""
        return self._make_request("GET", f"/api/episodes/{episode_id}")
    
    def list_episodes(self, group_id: str = None) -> List[Dict[str, Any]]:
        """List episodes."""
        params = {}
        if group_id:
            params["group_id"] = group_id
        return self._make_request("GET", "/api/episodes", params=params)


async def test_full_podcast_generation():
    """Test the complete podcast generation workflow."""
    client = PodcastTestClient()
    
    logger.info("🎯 Starting full podcast generation test...")
    
    try:
        # Step 1: Create Presenter
        logger.info("👤 Creating presenter...")
        presenter = client.create_presenter(
            name="Alex Chen",
            bio="Tech enthusiast and AI researcher with 10+ years experience in machine learning and software development.",
            gender="neutral"
        )
        logger.info(f"✅ Created presenter: {presenter['name']} (ID: {presenter['id']})")
        
        # Step 2: Create Writer
        logger.info("✍️ Creating writer...")
        writer = client.create_writer("AI Script Writer")
        logger.info(f"✅ Created writer: {writer['name']} (ID: {writer['id']})")
        
        # Step 3: Create News Feed
        logger.info("📰 Creating news feed...")
        news_feed = client.create_news_feed(
            name="TechCrunch RSS",
            url="https://techcrunch.com/feed/"
        )
        logger.info(f"✅ Created news feed: {news_feed['name']} (ID: {news_feed['id']})")
        
        # Step 4: Create Podcast Group
        logger.info("🎙️ Creating podcast group...")
        podcast_group = client.create_podcast_group(
            name="AI Weekly",
            description="Weekly podcast covering the latest developments in artificial intelligence and machine learning.",
            presenter_ids=[presenter['id']],
            writer_id=writer['id'],
            news_feed_ids=[news_feed['id']]
        )
        logger.info(f"✅ Created podcast group: {podcast_group['name']} (ID: {podcast_group['id']})")
        
        # Step 5: Generate Episode
        logger.info("🚀 Generating episode...")
        generation_response = client.generate_episode(podcast_group['id'])
        logger.info(f"✅ Episode generation started: {generation_response}")
        
        # Wait for generation to complete
        episode_id = generation_response.get('episode_id')
        if episode_id:
            logger.info(f"⏳ Waiting for episode generation to complete...")
            
            # Poll for completion
            max_attempts = 30  # 5 minutes max
            for attempt in range(max_attempts):
                time.sleep(10)  # Wait 10 seconds between checks
                
                try:
                    episode = client.get_episode(episode_id)
                    status = episode.get('status', 'unknown')
                    logger.info(f"📊 Episode status: {status}")
                    
                    if status in ['completed', 'published']:
                        logger.info("🎉 Episode generation completed!")
                        logger.info(f"📝 Script length: {len(episode.get('script', ''))} characters")
                        logger.info(f"🎵 Audio file: {episode.get('file_path', 'N/A')}")
                        logger.info(f"⏱️ Duration: {episode.get('duration_seconds', 0)} seconds")
                        break
                    elif status == 'failed':
                        logger.error("❌ Episode generation failed!")
                        break
                        
                except Exception as e:
                    logger.warning(f"⚠️ Error checking episode status: {e}")
                    
                if attempt == max_attempts - 1:
                    logger.warning("⏰ Timeout waiting for episode generation")
        
        # Step 6: List all episodes
        logger.info("📋 Listing all episodes...")
        episodes = client.list_episodes()
        logger.info(f"✅ Found {len(episodes)} episodes")
        
        for episode in episodes:
            logger.info(f"  - Episode {episode['id'][:8]}... - Status: {episode.get('status', 'unknown')}")
        
        logger.info("🎯 Test completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(test_full_podcast_generation())
