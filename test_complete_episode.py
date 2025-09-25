#!/usr/bin/env python3
"""
Test script that creates a complete episode record in the database.
This will show up in the web dashboard at localhost:8000.
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

class CompleteEpisodeTester:
    """Test that creates a complete episode record in the database."""
    
    def __init__(self):
        self.session = requests.Session()
        self.base_url = "http://localhost:8000"
    
    def create_presenter(self) -> str:
        """Create a presenter and return its ID."""
        logger.info("👤 Creating presenter...")
        
        presenter_data = {
            "name": "Alex Chen",
            "bio": "Tech enthusiast and AI researcher with 10+ years experience in machine learning and software development.",
            "gender": "neutral",
            "country": "US",
            "city": "New York",
            "specialties": ["technology", "podcasting"],
            "expertise": ["AI", "software development"],
            "interests": ["tech news", "innovation"]
        }
        
        response = self.session.post(f"{self.base_url}/api/presenters", json=presenter_data)
        if response.status_code == 200:
            presenter = response.json()
            logger.info(f"✅ Created presenter: {presenter['name']} (ID: {presenter['id']})")
            return presenter['id']
        else:
            raise Exception(f"Failed to create presenter: {response.status_code} - {response.text}")
    
    def create_writer(self) -> str:
        """Create a writer and return its ID."""
        logger.info("✍️ Creating writer...")
        
        writer_data = {
            "name": "AI Script Writer",
            "capabilities": ["title", "description", "tags", "keywords", "category", "subcategory"]
        }
        
        response = self.session.post(f"{self.base_url}/api/writers", json=writer_data)
        if response.status_code == 200:
            writer = response.json()
            logger.info(f"✅ Created writer: {writer['name']} (ID: {writer['id']})")
            return writer['id']
        else:
            raise Exception(f"Failed to create writer: {response.status_code} - {response.text}")
    
    def create_news_feed(self) -> str:
        """Create a news feed and return its ID."""
        logger.info("📰 Creating news feed...")
        
        feed_data = {
            "name": "TechCrunch RSS",
            "source_url": "https://techcrunch.com/feed/",
            "type": "RSS",
            "is_active": True
        }
        
        response = self.session.post(f"{self.base_url}/api/news-feeds", json=feed_data)
        if response.status_code == 200:
            feed = response.json()
            logger.info(f"✅ Created news feed: {feed['name']} (ID: {feed['id']})")
            return feed['id']
        else:
            raise Exception(f"Failed to create news feed: {response.status_code} - {response.text}")
    
    def create_podcast_group(self, presenter_id: str, writer_id: str, news_feed_id: str) -> str:
        """Create a podcast group and return its ID."""
        logger.info("🎙️ Creating podcast group...")
        
        group_data = {
            "name": "AI Weekly",
            "description": "Weekly podcast covering the latest developments in artificial intelligence and machine learning.",
            "category": "Technology",
            "subcategory": "AI News",
            "language": "en",
            "country": "US",
            "tags": ["AI", "technology", "news"],
            "keywords": ["artificial intelligence", "machine learning", "tech news"],
            "schedule": "0 9 * * 1",  # Every Monday at 9 AM
            "status": "active",
            "presenter_ids": [presenter_id],
            "writer_id": writer_id,
            "news_feed_ids": [news_feed_id]
        }
        
        response = self.session.post(f"{self.base_url}/api/podcast-groups", json=group_data)
        if response.status_code == 200:
            group = response.json()
            logger.info(f"✅ Created podcast group: {group['name']} (ID: {group['id']})")
            return group['id']
        else:
            raise Exception(f"Failed to create podcast group: {response.status_code} - {response.text}")
    
    def generate_episode_via_api(self, group_id: str) -> Dict[str, Any]:
        """Generate an episode using the API Gateway."""
        logger.info("🚀 Generating episode via API Gateway...")
        
        request_data = {
            "group_id": group_id
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/generate-episode",
                json=request_data,
                timeout=1200  # 20 minutes for complete generation
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info("✅ Episode generation started via API")
                logger.info(f"📋 Response: {result}")
                return result
            else:
                logger.error(f"❌ Episode generation failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Episode generation request failed: {e}")
            return None
    
    def list_episodes(self) -> List[Dict[str, Any]]:
        """List all episodes."""
        logger.info("📋 Listing all episodes...")
        
        try:
            response = self.session.get(f"{self.base_url}/api/episodes")
            if response.status_code == 200:
                episodes = response.json()
                logger.info(f"✅ Found {len(episodes)} episodes")
                return episodes
            else:
                logger.error(f"❌ Failed to list episodes: {response.status_code} - {response.text}")
                return []
        except Exception as e:
            logger.error(f"❌ Error listing episodes: {e}")
            return []
    
    def list_podcast_groups(self) -> List[Dict[str, Any]]:
        """List all podcast groups."""
        logger.info("📋 Listing all podcast groups...")
        
        try:
            response = self.session.get(f"{self.base_url}/api/podcast-groups")
            if response.status_code == 200:
                groups = response.json()
                logger.info(f"✅ Found {len(groups)} podcast groups")
                return groups
            else:
                logger.error(f"❌ Failed to list podcast groups: {response.status_code} - {response.text}")
                return []
        except Exception as e:
            logger.error(f"❌ Error listing podcast groups: {e}")
            return []


def main():
    """Run the complete episode creation test."""
    tester = CompleteEpisodeTester()
    
    logger.info("🎯 Starting complete episode creation test...")
    
    try:
        # Step 1: Set up database entities
        presenter_id = tester.create_presenter()
        writer_id = tester.create_writer()
        news_feed_id = tester.create_news_feed()
        group_id = tester.create_podcast_group(presenter_id, writer_id, news_feed_id)
        
        # Step 2: List current state
        logger.info("📊 Current system state:")
        groups = tester.list_podcast_groups()
        episodes = tester.list_episodes()
        
        # Step 3: Generate episode via API Gateway
        episode_result = tester.generate_episode_via_api(group_id)
        
        if episode_result:
            logger.info("🎉 Episode generation initiated successfully!")
            logger.info("📋 Generation result:")
            logger.info(f"  - Status: {episode_result.get('status', 'unknown')}")
            logger.info(f"  - Message: {episode_result.get('message', 'N/A')}")
            
            # Wait a bit and check for episodes
            logger.info("⏳ Waiting for episode generation to complete...")
            time.sleep(30)  # Wait 30 seconds
            
            # Check episodes again
            episodes_after = tester.list_episodes()
            if len(episodes_after) > len(episodes):
                logger.info("✅ New episode(s) found in database!")
                for episode in episodes_after:
                    logger.info(f"  - Episode ID: {episode.get('id', 'N/A')}")
                    logger.info(f"  - Status: {episode.get('status', 'N/A')}")
                    logger.info(f"  - Created: {episode.get('created_at', 'N/A')}")
            else:
                logger.warning("⚠️ No new episodes found yet. Generation may still be in progress.")
            
            # Final state
            logger.info("📊 Final system state:")
            final_groups = tester.list_podcast_groups()
            final_episodes = tester.list_episodes()
            
            logger.info("🎯 Test completed!")
            logger.info(f"📋 Summary:")
            logger.info(f"  - Podcast groups: {len(final_groups)}")
            logger.info(f"  - Episodes: {len(final_episodes)}")
            logger.info(f"  - Web dashboard available at: http://localhost:8000")
            
        else:
            logger.error("❌ Episode generation failed")
            
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        raise


if __name__ == "__main__":
    main()
