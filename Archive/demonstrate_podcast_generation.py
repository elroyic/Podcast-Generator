#!/usr/bin/env python3
"""
Comprehensive demonstration of the working podcast generation system.
This shows the complete workflow from news fetching to MP3 generation.
"""

import asyncio
import json
import logging
from datetime import datetime
from uuid import uuid4
import httpx

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PodcastGenerator:
    """Complete podcast generation system using working simple services."""
    
    def __init__(self):
        self.base_url = "http://localhost"
        self.services = {
            "news-feed": f"{self.base_url}:8001",
            "text-generation": f"{self.base_url}:8002",
            "writer": f"{self.base_url}:8003",
            "presenter": f"{self.base_url}:8004",
            "publishing": f"{self.base_url}:8005",
            "podcast-host": f"{self.base_url}:8006"
        }
    
    async def call_service(self, service_name: str, method: str, endpoint: str, **kwargs):
        """Make HTTP request to a service."""
        if service_name not in self.services:
            raise Exception(f"Unknown service: {service_name}")
        
        url = f"{self.services[service_name]}{endpoint}"
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
    
    async def generate_complete_podcast(self, topic: str = "Spring Weather"):
        """Generate a complete podcast episode."""
        logger.info("🎙️ Starting complete podcast generation workflow...")
        
        try:
            # Step 1: Create test data
            logger.info("📝 Step 1: Creating test data...")
            
            # Create test data (using hardcoded IDs since simple services don't have management endpoints)
            presenter_id = str(uuid4())
            writer_id = str(uuid4())
            feed_id = str(uuid4())
            group_id = str(uuid4())
            
            logger.info(f"✅ Using test data with IDs: presenter={presenter_id}, writer={writer_id}, feed={feed_id}, group={group_id}")
            
            # Step 2: Create news feed and fetch articles
            logger.info("📰 Step 2: Creating news feed and fetching articles...")
            
            # First create a news feed
            feed_data = {
                "source_url": "https://weather.com/news/rss.xml",
                "name": "Weather News Feed",
                "type": "RSS",
                "is_active": True
            }
            feed_response = await self.call_service("news-feed", "POST", "/feeds", json=feed_data)
            actual_feed_id = feed_response.get("id", feed_id)
            logger.info(f"✅ Created news feed: {actual_feed_id}")
            
            # Trigger feed fetch
            await self.call_service("news-feed", "POST", f"/feeds/{actual_feed_id}/fetch")
            logger.info("✅ Triggered feed fetch")
            
            # Get recent articles
            articles_response = await self.call_service("news-feed", "GET", "/articles/recent?limit=10")
            articles = articles_response
            logger.info(f"✅ Fetched {len(articles)} articles")
            
            # Step 3: Generate script
            logger.info("✍️ Step 3: Generating podcast script...")
            script_request = {
                "group_id": group_id,
                "article_summaries": articles,  # Convert articles to summaries
                "target_duration_minutes": 1  # 1 minute
            }
            script_response = await self.call_service("text-generation", "POST", "/generate-script", json=script_request)
            script = script_response.get("script", "")
            logger.info(f"✅ Generated script ({len(script)} characters)")
            
            # Step 4: Generate metadata
            logger.info("📝 Step 4: Generating episode metadata...")
            episode_id = str(uuid4())
            metadata_request = {
                "episode_id": episode_id,
                "script": script,
                "group_id": group_id
            }
            metadata_response = await self.call_service("writer", "POST", "/generate-metadata", json=metadata_request)
            title = metadata_response.get("title", f"{topic} Episode")
            description = metadata_response.get("description", f"A podcast about {topic.lower()}")
            logger.info(f"✅ Generated metadata: {title}")
            
            # Step 5: Generate MP3 audio
            logger.info("🎵 Step 5: Generating MP3 audio...")
            audio_request = {
                "episode_id": episode_id,
                "script": script,
                "presenter_ids": [presenter_id],
                "voice_settings": {
                    "speed": 1.0,
                    "pitch": 1.0,
                    "volume": 1.0
                }
            }
            audio_response = await self.call_service("presenter", "POST", "/generate-audio", json=audio_request)
            audio_url = audio_response.get("audio_url", "")
            duration = audio_response.get("duration_seconds", 0)
            file_size = audio_response.get("file_size_bytes", 0)
            logger.info(f"✅ Generated MP3 audio: {audio_url}")
            
            # Step 6: Publish episode
            logger.info("📡 Step 6: Publishing episode...")
            publish_request = {
                "episode_id": episode_id,
                "platforms": ["anchor"],
                "platform_credentials": {}
            }
            publish_response = await self.call_service("publishing", "POST", "/publish", json=publish_request)
            logger.info(f"✅ Published episode to platforms")
            
            # Create complete episode summary
            episode_summary = {
                "episode_id": episode_id,
                "group_id": group_id,
                "title": title,
                "description": description,
                "script": script,
                "audio_url": audio_url,
                "duration_seconds": duration,
                "file_size_bytes": file_size,
                "presenter_id": presenter_id,
                "writer_id": writer_id,
                "feed_id": actual_feed_id,
                "articles_count": len(articles),
                "generated_at": datetime.utcnow().isoformat(),
                "status": "completed"
            }
            
            # Save episode summary
            with open("complete_episode_demo.json", "w") as f:
                json.dump(episode_summary, f, indent=2)
            
            logger.info("🎉 Podcast generation completed successfully!")
            logger.info(f"📁 Episode summary saved to: complete_episode_demo.json")
            logger.info(f"🎵 Audio file: {audio_url}")
            logger.info(f"⏱️ Duration: {duration} seconds")
            logger.info(f"📊 File size: {file_size} bytes")
            
            return episode_summary
            
        except Exception as e:
            logger.error(f"❌ Podcast generation failed: {e}")
            raise
    
    async def check_services_health(self):
        """Check if all services are healthy."""
        logger.info("🔍 Checking service health...")
        
        healthy_services = []
        unhealthy_services = []
        
        for service_name, base_url in self.services.items():
            try:
                response = await self.call_service(service_name, "GET", "/health")
                if response.get("status") == "healthy":
                    healthy_services.append(service_name)
                    logger.info(f"✅ {service_name}: healthy")
                else:
                    unhealthy_services.append(service_name)
                    logger.warning(f"⚠️ {service_name}: degraded")
            except Exception as e:
                unhealthy_services.append(service_name)
                logger.error(f"❌ {service_name}: error - {e}")
        
        logger.info(f"📊 Service Status: {len(healthy_services)} healthy, {len(unhealthy_services)} unhealthy")
        return len(unhealthy_services) == 0

async def main():
    """Main demonstration function."""
    generator = PodcastGenerator()
    
    # Check service health first
    if not await generator.check_services_health():
        logger.warning("⚠️ Some services are unhealthy, but continuing with demonstration...")
    
    # Generate the podcast
    try:
        episode = await generator.generate_complete_podcast("Spring is here but the Rain hasn't come!")
        logger.info("🎊 Demonstration completed successfully!")
        return True
    except Exception as e:
        logger.error(f"💥 Demonstration failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    if success:
        print("\n🎉 SUCCESS: Complete podcast generation workflow demonstrated!")
        print("📁 Check 'complete_episode_demo.json' for the full episode details")
    else:
        print("\n❌ FAILED: Podcast generation demonstration failed")
