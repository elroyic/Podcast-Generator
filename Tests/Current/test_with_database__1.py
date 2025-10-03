#!/usr/bin/env python3
"""
Test script that properly sets up the database and tests all services.
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

class DatabaseServiceTester:
    """Test services with proper database setup."""
    
    def __init__(self):
        self.session = requests.Session()
        self.base_url = "http://localhost:8000"  # Use API Gateway
    
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
    
    def test_text_generation_direct(self, group_id: str) -> Dict[str, Any]:
        """Test text generation service directly."""
        logger.info("📝 Testing Text Generation Service directly...")
        
        # Test articles
        test_articles = [
            {
                "id": str(uuid4()),
                "title": "New AI Model Breaks Performance Records",
                "summary": "A new artificial intelligence model has achieved unprecedented performance on various benchmarks, showing significant improvements in reasoning and language understanding.",
                "content": "Researchers have developed a new AI model that demonstrates remarkable capabilities across multiple domains. The model shows particular strength in complex reasoning tasks and natural language understanding.",
                "publish_date": "2024-01-15T10:00:00Z"
            },
            {
                "id": str(uuid4()),
                "title": "AI Ethics Guidelines Updated",
                "summary": "Leading AI organizations have released updated guidelines for ethical AI development, emphasizing transparency and accountability.",
                "content": "The new guidelines focus on ensuring AI systems are developed with proper consideration for ethical implications, including bias mitigation and transparency in decision-making processes.",
                "publish_date": "2024-01-14T15:30:00Z"
            },
            {
                "id": str(uuid4()),
                "title": "Machine Learning in Healthcare",
                "summary": "New applications of machine learning in healthcare are showing promising results in early disease detection and treatment optimization.",
                "content": "Healthcare providers are increasingly adopting AI-powered tools for diagnostic assistance, treatment planning, and patient monitoring. These systems are helping to improve outcomes while reducing costs.",
                "publish_date": "2024-01-13T08:45:00Z"
            }
        ]
        
        script_request = {
            "group_id": group_id,
            "article_summaries": test_articles,
            "target_duration_minutes": 75,
            "style_preferences": {
                "tone": "professional",
                "style": "informative",
                "target_audience": "tech professionals"
            }
        }
        
        try:
            response = self.session.post(
                "http://localhost:8002/generate-script",
                json=script_request,
                timeout=300  # 5 minutes for script generation
            )
            
            if response.status_code == 200:
                result = response.json()
                script = result.get('script', '')
                logger.info("✅ Text Generation service generated script successfully")
                logger.info(f"📝 Script length: {len(script)} characters")
                logger.info(f"📊 Estimated duration: {result.get('estimated_duration_minutes', 0)} minutes")
                logger.info(f"📰 Articles used: {len(result.get('articles_used', []))}")
                
                # Check if script is over 1000 words
                word_count = len(script.split())
                if word_count >= 1000:
                    logger.info(f"✅ Script meets requirement: {word_count} words (≥1000)")
                else:
                    logger.warning(f"⚠️ Script is short: {word_count} words (<1000)")
                
                return result
            else:
                logger.error(f"❌ Text Generation service failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Text Generation service request failed: {e}")
            return None
    
    def test_writer_service_direct(self, script: str, group_id: str) -> Dict[str, Any]:
        """Test writer service directly."""
        logger.info("✍️ Testing Writer Service directly...")
        
        metadata_request = {
            "episode_id": str(uuid4()),
            "script": script,
            "group_id": group_id,
            "style_preferences": {
                "tone": "professional",
                "style": "informative"
            }
        }
        
        try:
            response = self.session.post(
                "http://localhost:8003/generate-metadata",
                json=metadata_request,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info("✅ Writer service generated metadata successfully")
                logger.info(f"📝 Generated title: {result.get('metadata', {}).get('title', 'N/A')}")
                logger.info(f"📄 Generated description: {result.get('metadata', {}).get('description', 'N/A')[:100]}...")
                return result
            else:
                logger.error(f"❌ Writer service failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Writer service request failed: {e}")
            return None
    
    def test_presenter_service_direct(self, script: str) -> Dict[str, Any]:
        """Test presenter service directly."""
        logger.info("🎤 Testing Presenter Service directly...")
        
        audio_request = {
            "episode_id": str(uuid4()),
            "script": script,
            "presenter_ids": [str(uuid4())],
            "voice_settings": {
                "speed": 1.0,
                "pitch": 1.0,
                "volume": 1.0
            }
        }
        
        try:
            response = self.session.post(
                "http://localhost:8004/generate-audio",
                json=audio_request,
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info("✅ Presenter service generated audio successfully")
                logger.info(f"🎵 Audio URL: {result.get('audio_url', 'N/A')}")
                logger.info(f"⏱️ Duration: {result.get('duration_seconds', 0)} seconds")
                logger.info(f"📁 File size: {result.get('file_size_bytes', 0)} bytes")
                logger.info(f"🎧 Format: {result.get('format', 'N/A')}")
                return result
            else:
                logger.error(f"❌ Presenter service failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Presenter service request failed: {e}")
            return None


def main():
    """Run the complete test workflow."""
    tester = DatabaseServiceTester()
    
    logger.info("🎯 Starting complete podcast generation test with database setup...")
    
    try:
        # Step 1: Set up database entities
        presenter_id = tester.create_presenter()
        writer_id = tester.create_writer()
        news_feed_id = tester.create_news_feed()
        group_id = tester.create_podcast_group(presenter_id, writer_id, news_feed_id)
        
        # Step 2: Test Text Generation Service
        script_result = tester.test_text_generation_direct(group_id)
        
        if script_result:
            script = script_result.get('script', '')
            
            # Step 3: Test Writer Service
            metadata_result = tester.test_writer_service_direct(script, group_id)
            
            if metadata_result:
                # Step 4: Test Presenter Service
                audio_result = tester.test_presenter_service_direct(script)
                
                if audio_result:
                    logger.info("🎉 All services tested successfully!")
                    logger.info("📋 Test Summary:")
                    logger.info(f"  - Script generated: {len(script)} characters")
                    logger.info(f"  - Word count: {len(script.split())} words")
                    logger.info(f"  - Metadata created: {metadata_result.get('metadata', {}).get('title', 'N/A')}")
                    logger.info(f"  - Audio generated: {audio_result.get('duration_seconds', 0)} seconds")
                    logger.info(f"  - Audio format: {audio_result.get('format', 'N/A')}")
                    logger.info(f"  - File size: {audio_result.get('file_size_bytes', 0)} bytes")
                    
                    # Check if it's MP3 format
                    if audio_result.get('format', '').lower() == 'mp3':
                        logger.info("✅ Audio is in MP3 format as requested")
                    else:
                        logger.warning(f"⚠️ Audio format is {audio_result.get('format', 'unknown')}, not MP3")
                else:
                    logger.error("❌ Presenter service test failed")
            else:
                logger.error("❌ Writer service test failed")
        else:
            logger.error("❌ Text Generation service test failed")
            
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        raise


if __name__ == "__main__":
    main()
