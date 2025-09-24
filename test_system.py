#!/usr/bin/env python3
"""
Comprehensive system test for Podcast AI application.
This script tests all services and their integration.
"""

import asyncio
import json
import logging
import sys
from datetime import datetime
from typing import Dict, Any
from uuid import uuid4

import httpx

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Service URLs
SERVICE_URLS = {
    "api-gateway": "http://localhost:8000",
    "news-feed": "http://localhost:8001",
    "text-generation": "http://localhost:8002",
    "writer": "http://localhost:8003",
    "presenter": "http://localhost:8004",
    "publishing": "http://localhost:8005",
    "ai-overseer": "http://localhost:8006",
    "podcast-host": "http://localhost:8006",
    "nginx": "http://localhost:8080"
}

class SystemTester:
    """Comprehensive system tester for Podcast AI."""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.test_results = {}
    
    async def test_service_health(self, service_name: str, url: str) -> bool:
        """Test if a service is healthy."""
        try:
            response = await self.client.get(f"{url}/health")
            if response.status_code == 200:
                logger.info(f"✅ {service_name} is healthy")
                return True
            else:
                logger.error(f"❌ {service_name} returned status {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ {service_name} is not responding: {e}")
            return False
    
    async def test_all_services_health(self) -> Dict[str, bool]:
        """Test health of all services."""
        logger.info("🔍 Testing service health...")
        results = {}
        
        for service_name, url in SERVICE_URLS.items():
            results[service_name] = await self.test_service_health(service_name, url)
        
        self.test_results["health"] = results
        return results
    
    async def test_presenter_creation(self) -> str:
        """Test creating a presenter."""
        logger.info("👤 Testing presenter creation...")
        
        presenter_data = {
            "name": "Test Presenter",
            "bio": "A test presenter for system testing",
            "gender": "non-binary",
            "country": "US",
            "city": "San Francisco",
            "specialties": ["technology", "AI"],
            "expertise": ["software development", "machine learning"],
            "interests": ["podcasting", "technology"]
        }
        
        try:
            response = await self.client.post(
                f"{SERVICE_URLS['api-gateway']}/api/presenters",
                json=presenter_data
            )
            
            if response.status_code == 200:
                presenter = response.json()
                logger.info(f"✅ Presenter created: {presenter['id']}")
                return presenter['id']
            else:
                logger.error(f"❌ Failed to create presenter: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error creating presenter: {e}")
            return None
    
    async def test_writer_creation(self) -> str:
        """Test creating a writer."""
        logger.info("✍️ Testing writer creation...")
        
        writer_data = {
            "name": "Test AI Writer",
            "capabilities": ["title", "description", "tags", "keywords", "category"]
        }
        
        try:
            response = await self.client.post(
                f"{SERVICE_URLS['api-gateway']}/api/writers",
                json=writer_data
            )
            
            if response.status_code == 200:
                writer = response.json()
                logger.info(f"✅ Writer created: {writer['id']}")
                return writer['id']
            else:
                logger.error(f"❌ Failed to create writer: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error creating writer: {e}")
            return None
    
    async def test_news_feed_creation(self) -> str:
        """Test creating a news feed."""
        logger.info("📰 Testing news feed creation...")
        
        feed_data = {
            "source_url": "https://feeds.bbci.co.uk/news/technology/rss.xml",
            "name": "BBC Technology Test Feed",
            "type": "RSS",
            "is_active": True
        }
        
        try:
            response = await self.client.post(
                f"{SERVICE_URLS['api-gateway']}/api/news-feeds",
                json=feed_data
            )
            
            if response.status_code == 200:
                feed = response.json()
                logger.info(f"✅ News feed created: {feed['id']}")
                return feed['id']
            else:
                logger.error(f"❌ Failed to create news feed: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error creating news feed: {e}")
            return None
    
    async def test_podcast_group_creation(self, presenter_id: str, writer_id: str, feed_id: str) -> str:
        """Test creating a podcast group."""
        logger.info("🎙️ Testing podcast group creation...")
        
        group_data = {
            "name": "Test Podcast Group",
            "description": "A test podcast group for system testing",
            "category": "Technology",
            "subcategory": "AI",
            "language": "en",
            "country": "US",
            "tags": ["technology", "AI", "testing"],
            "keywords": ["artificial intelligence", "machine learning", "podcast"],
            "schedule": "0 9 * * 1",  # Every Monday at 9 AM
            "status": "active",
            "presenter_ids": [presenter_id],
            "writer_id": writer_id,
            "news_feed_ids": [feed_id]
        }
        
        try:
            response = await self.client.post(
                f"{SERVICE_URLS['api-gateway']}/api/podcast-groups",
                json=group_data
            )
            
            if response.status_code == 200:
                group = response.json()
                logger.info(f"✅ Podcast group created: {group['id']}")
                return group['id']
            else:
                logger.error(f"❌ Failed to create podcast group: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error creating podcast group: {e}")
            return None
    
    async def test_episode_generation(self, group_id: str) -> str:
        """Test episode generation."""
        logger.info("🎬 Testing episode generation...")
        
        generation_request = {
            "group_id": group_id,
            "force_regenerate": False
        }
        
        try:
            response = await self.client.post(
                f"{SERVICE_URLS['api-gateway']}/api/generate-episode",
                json=generation_request
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"✅ Episode generation queued: {result['episode_id']}")
                return result['episode_id']
            else:
                logger.error(f"❌ Failed to generate episode: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error generating episode: {e}")
            return None
    
    async def test_text_generation(self) -> bool:
        """Test text generation service directly."""
        logger.info("📝 Testing text generation service...")
        
        test_request = {
            "group_id": str(uuid4()),
            "article_summaries": [
                {
                    "id": str(uuid4()),
                    "title": "Test Article 1",
                    "summary": "This is a test article about AI technology.",
                    "link": "https://example.com/article1",
                    "publish_date": datetime.utcnow().isoformat()
                }
            ],
            "target_duration_minutes": 5
        }
        
        try:
            response = await self.client.post(
                f"{SERVICE_URLS['text-generation']}/test-generation",
                params={"test_prompt": "Write a short 2-minute podcast introduction about today's tech news."}
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info("✅ Text generation test successful")
                return True
            else:
                logger.error(f"❌ Text generation test failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error in text generation test: {e}")
            return False
    
    async def test_audio_generation(self) -> bool:
        """Test audio generation service directly."""
        logger.info("🎵 Testing audio generation service...")
        
        try:
            response = await self.client.post(
                f"{SERVICE_URLS['presenter']}/test-audio-generation",
                params={"test_text": "Hello, this is a test of the text-to-speech system."}
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info("✅ Audio generation test successful")
                return True
            else:
                logger.error(f"❌ Audio generation test failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error in audio generation test: {e}")
            return False
    
    async def test_publishing(self) -> bool:
        """Test publishing service directly."""
        logger.info("📤 Testing publishing service...")
        
        try:
            response = await self.client.post(
                f"{SERVICE_URLS['publishing']}/test-publish"
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info("✅ Publishing test successful")
                return True
            else:
                logger.error(f"❌ Publishing test failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error in publishing test: {e}")
            return False
    
    async def test_metadata_generation(self) -> bool:
        """Test metadata generation service directly."""
        logger.info("📊 Testing metadata generation service...")
        
        try:
            response = await self.client.post(
                f"{SERVICE_URLS['writer']}/test-metadata-generation"
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info("✅ Metadata generation test successful")
                return True
            else:
                logger.error(f"❌ Metadata generation test failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error in metadata generation test: {e}")
            return False
    
    async def run_comprehensive_test(self):
        """Run comprehensive system test."""
        logger.info("🚀 Starting comprehensive system test...")
        
        # Test 1: Service Health
        health_results = await self.test_all_services_health()
        healthy_services = sum(health_results.values())
        total_services = len(health_results)
        
        if healthy_services < total_services:
            logger.warning(f"⚠️ Only {healthy_services}/{total_services} services are healthy")
        
        # Test 2: Create test data
        presenter_id = await self.test_presenter_creation()
        writer_id = await self.test_writer_creation()
        feed_id = await self.test_news_feed_creation()
        
        if not all([presenter_id, writer_id, feed_id]):
            logger.error("❌ Failed to create test data")
            return False
        
        # Test 3: Create podcast group
        group_id = await self.test_podcast_group_creation(presenter_id, writer_id, feed_id)
        if not group_id:
            logger.error("❌ Failed to create podcast group")
            return False
        
        # Test 4: Individual service tests
        text_gen_success = await self.test_text_generation()
        audio_gen_success = await self.test_audio_generation()
        metadata_gen_success = await self.test_metadata_generation()
        publishing_success = await self.test_publishing()
        
        # Test 5: Episode generation
        episode_id = await self.test_episode_generation(group_id)
        
        # Summary
        logger.info("\n" + "="*50)
        logger.info("📊 TEST SUMMARY")
        logger.info("="*50)
        logger.info(f"Service Health: {healthy_services}/{total_services} services healthy")
        logger.info(f"Text Generation: {'✅' if text_gen_success else '❌'}")
        logger.info(f"Audio Generation: {'✅' if audio_gen_success else '❌'}")
        logger.info(f"Metadata Generation: {'✅' if metadata_gen_success else '❌'}")
        logger.info(f"Publishing: {'✅' if publishing_success else '❌'}")
        logger.info(f"Episode Generation: {'✅' if episode_id else '❌'}")
        
        overall_success = (
            healthy_services >= total_services * 0.8 and  # At least 80% services healthy
            text_gen_success and
            audio_gen_success and
            metadata_gen_success and
            publishing_success
        )
        
        if overall_success:
            logger.info("🎉 All tests passed! System is ready.")
        else:
            logger.warning("⚠️ Some tests failed. Check the logs above.")
        
        return overall_success
    
    async def cleanup(self):
        """Clean up resources."""
        await self.client.aclose()

async def main():
    """Main test function."""
    tester = SystemTester()
    
    try:
        success = await tester.run_comprehensive_test()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("🛑 Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"💥 Unexpected error: {e}")
        sys.exit(1)
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    asyncio.run(main())