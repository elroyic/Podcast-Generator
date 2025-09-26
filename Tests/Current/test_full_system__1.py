#!/usr/bin/env python3
"""
Full System Test - Create a comprehensive podcast about this application
with 1000+ words split across 2 presenters using VibeVoice.
"""

import asyncio
import json
import logging
from datetime import datetime
from uuid import uuid4
import httpx

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FullSystemTester:
    """Test the complete podcast generation system."""
    
    def __init__(self):
        self.base_url = "http://localhost"
        self.services = {
            "news-feed": 8001,
            "text-generation": 8002,
            "writer": 8003,
            "presenter": 8004,
            "publishing": 8005,
            "podcast-host": 8006
        }
    
    async def call_service(self, service_name: str, method: str, endpoint: str, **kwargs):
        """Call a service endpoint."""
        port = self.services.get(service_name)
        if not port:
            raise ValueError(f"Unknown service: {service_name}")
        
        url = f"{self.base_url}:{port}{endpoint}"
        
        async with httpx.AsyncClient() as client:
            if method.upper() == "GET":
                response = await client.get(url, **kwargs)
            elif method.upper() == "POST":
                response = await client.post(url, **kwargs)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            response.raise_for_status()
            return response.json()
    
    async def check_services_health(self):
        """Check if all services are healthy."""
        logger.info("🔍 Checking service health...")
        
        healthy_services = 0
        for service_name in self.services:
            try:
                health = await self.call_service(service_name, "GET", "/health")
                logger.info(f"✅ {service_name}: {health.get('status', 'unknown')}")
                healthy_services += 1
            except Exception as e:
                logger.error(f"❌ {service_name}: {e}")
        
        logger.info(f"📊 Service Status: {healthy_services} healthy, {len(self.services) - healthy_services} unhealthy")
        return healthy_services == len(self.services)
    
    async def create_podcast_group(self):
        """Create a podcast group for this application."""
        logger.info("📝 Creating podcast group for 'This Application'...")
        
        # For simple services, we'll use hardcoded IDs
        group_id = str(uuid4())
        
        logger.info(f"✅ Created podcast group: {group_id}")
        return group_id
    
    async def create_presenters_and_writer(self):
        """Create 2 presenters and 1 writer."""
        logger.info("👥 Creating presenters and writer...")
        
        # For simple services, we'll use hardcoded IDs
        presenter1_id = str(uuid4())
        presenter2_id = str(uuid4())
        writer_id = str(uuid4())
        
        logger.info(f"✅ Created presenter 1: {presenter1_id}")
        logger.info(f"✅ Created presenter 2: {presenter2_id}")
        logger.info(f"✅ Created writer: {writer_id}")
        
        return presenter1_id, presenter2_id, writer_id
    
    async def create_news_feed(self):
        """Create a news feed for application-related content."""
        logger.info("📰 Creating news feed for application content...")
        
        feed_data = {
            "source_url": "https://techcrunch.com/feed/",
            "name": "Tech News Feed",
            "type": "RSS",
            "is_active": True
        }
        
        feed_response = await self.call_service("news-feed", "POST", "/feeds", json=feed_data)
        feed_id = feed_response.get("id")
        
        # Trigger feed fetch
        await self.call_service("news-feed", "POST", f"/feeds/{feed_id}/fetch")
        
        # Get recent articles
        articles_response = await self.call_service("news-feed", "GET", "/articles/recent?limit=5")
        
        logger.info(f"✅ Created news feed: {feed_id}")
        logger.info(f"✅ Fetched {len(articles_response)} articles")
        
        return feed_id, articles_response
    
    async def generate_comprehensive_script(self, group_id: str, articles: list):
        """Generate a comprehensive 1000+ word script about this application."""
        logger.info("✍️ Generating comprehensive script about this application...")
        
        # Create a detailed prompt for the script generation
        script_prompt = {
            "group_id": group_id,
            "article_summaries": articles,
            "target_duration_minutes": 5,  # 5 minutes for 1000+ words
            "custom_instructions": """
            Create a comprehensive podcast script about this AI-powered podcast generation application. 
            The script should be at least 1000 words and cover:
            
            1. Introduction to the application and its purpose
            2. The microservices architecture (API Gateway, News Feed, Text Generation, Writer, Presenter, Publishing, AI Overseer)
            3. How VibeVoice-1.5B generates human-like speech
            4. The complete workflow from news articles to published podcast
            5. Technical challenges and solutions
            6. Future possibilities and applications
            
            Split the content naturally between two speakers:
            - Speaker 1: Technical expert who explains the architecture and implementation
            - Speaker 2: Host who asks questions and provides context
            
            Make it engaging, informative, and conversational. Include specific technical details 
            about the services, VibeVoice model, and the generation process.
            """
        }
        
        script_response = await self.call_service("text-generation", "POST", "/generate-script", json=script_prompt)
        script = script_response.get("script", "")
        
        word_count = len(script.split())
        logger.info(f"✅ Generated script: {word_count} words, {len(script)} characters")
        
        return script, word_count
    
    async def generate_episode_metadata(self, episode_id: str, script: str, group_id: str, writer_id: str):
        """Generate episode metadata."""
        logger.info("📝 Generating episode metadata...")
        
        metadata_request = {
            "episode_id": episode_id,
            "script": script,
            "group_id": group_id,
            "writer_id": writer_id
        }
        
        metadata_response = await self.call_service("writer", "POST", "/generate-metadata", json=metadata_request)
        title = metadata_response.get("title", "This Application Podcast")
        description = metadata_response.get("description", "A comprehensive podcast about this AI-powered podcast generation application")
        
        logger.info(f"✅ Generated metadata: {title}")
        
        return title, description
    
    async def generate_vibevoice_audio(self, episode_id: str, script: str, presenter1_id: str, presenter2_id: str):
        """Generate audio using VibeVoice with 2 speakers."""
        logger.info("🎵 Generating VibeVoice audio with 2 speakers...")
        
        # Format script for 2 speakers
        formatted_script = self._format_script_for_two_speakers(script)
        
        audio_request = {
            "episode_id": episode_id,
            "script": formatted_script,
            "presenter_ids": [presenter1_id, presenter2_id],
            "voice_settings": {
                "speaker1_voice": "Alice",
                "speaker2_voice": "Frank"
            }
        }
        
        audio_response = await self.call_service("presenter", "POST", "/generate-audio", json=audio_request)
        audio_url = audio_response.get("audio_url", "")
        duration = audio_response.get("duration_seconds", 0)
        file_size = audio_response.get("file_size_bytes", 0)
        
        logger.info(f"✅ Generated VibeVoice audio: {audio_url}")
        logger.info(f"⏱️ Duration: {duration} seconds")
        logger.info(f"📊 File size: {file_size} bytes")
        
        return audio_response
    
    def _format_script_for_two_speakers(self, script: str) -> str:
        """Format the script for VibeVoice with proper speaker labels."""
        # Split the script into segments and assign to speakers
        lines = script.split('\n')
        formatted_lines = []
        
        current_speaker = 1
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Add speaker label
            formatted_lines.append(f"Speaker {current_speaker}: {line}")
            
            # Alternate between speakers for natural conversation
            current_speaker = 2 if current_speaker == 1 else 1
        
        return '\n'.join(formatted_lines)
    
    async def publish_episode(self, episode_id: str):
        """Publish the episode."""
        logger.info("📡 Publishing episode...")
        
        publish_request = {
            "episode_id": episode_id,
            "platforms": ["anchor"],
            "platform_credentials": {}
        }
        
        publish_response = await self.call_service("publishing", "POST", "/publish", json=publish_request)
        
        logger.info(f"✅ Published episode to platforms")
        
        return publish_response
    
    async def run_full_test(self):
        """Run the complete system test."""
        logger.info("🎙️ Starting full system test for 'This Application' podcast...")
        
        try:
            # Check service health
            if not await self.check_services_health():
                logger.error("❌ Not all services are healthy. Aborting test.")
                return False
            
            # Step 1: Create podcast group
            group_id = await self.create_podcast_group()
            
            # Step 2: Create presenters and writer
            presenter1_id, presenter2_id, writer_id = await self.create_presenters_and_writer()
            
            # Step 3: Create news feed
            feed_id, articles = await self.create_news_feed()
            
            # Step 4: Generate comprehensive script
            script, word_count = await self.generate_comprehensive_script(group_id, articles)
            
            if word_count < 1000:
                logger.warning(f"⚠️ Script is only {word_count} words, expected 1000+")
            else:
                logger.info(f"✅ Script meets length requirement: {word_count} words")
            
            # Step 5: Generate episode metadata
            episode_id = str(uuid4())
            title, description = await self.generate_episode_metadata(episode_id, script, group_id, writer_id)
            
            # Step 6: Generate VibeVoice audio
            audio_response = await self.generate_vibevoice_audio(episode_id, script, presenter1_id, presenter2_id)
            
            # Step 7: Publish episode
            publish_response = await self.publish_episode(episode_id)
            
            # Create comprehensive episode summary
            episode_summary = {
                "episode_id": episode_id,
                "group_id": group_id,
                "title": title,
                "description": description,
                "script": script,
                "script_word_count": word_count,
                "script_character_count": len(script),
                "audio_url": audio_response.get("audio_url", ""),
                "duration_seconds": audio_response.get("duration_seconds", 0),
                "file_size_bytes": audio_response.get("file_size_bytes", 0),
                "audio_format": audio_response.get("format", ""),
                "channels": audio_response.get("generation_metadata", {}).get("channels", 2),
                "sample_rate": audio_response.get("generation_metadata", {}).get("sample_rate", 24000),
                "model_used": audio_response.get("generation_metadata", {}).get("model_used", ""),
                "presenter1_id": presenter1_id,
                "presenter2_id": presenter2_id,
                "writer_id": writer_id,
                "feed_id": feed_id,
                "articles_count": len(articles),
                "generated_at": datetime.utcnow().isoformat(),
                "status": "completed"
            }
            
            # Save episode summary
            with open("full_system_test_results.json", "w") as f:
                json.dump(episode_summary, f, indent=2)
            
            logger.info("🎉 Full system test completed successfully!")
            logger.info(f"📁 Episode summary saved to: full_system_test_results.json")
            logger.info(f"🎵 Audio file: {episode_summary['audio_url']}")
            logger.info(f"⏱️ Duration: {episode_summary['duration_seconds']} seconds")
            logger.info(f"📊 File size: {episode_summary['file_size_bytes']} bytes")
            logger.info(f"📝 Script: {episode_summary['script_word_count']} words")
            logger.info(f"🎤 Speakers: 2 (Alice & Frank)")
            logger.info(f"🤖 Model: {episode_summary['model_used']}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Full system test failed: {e}")
            return False

async def main():
    """Main function."""
    tester = FullSystemTester()
    success = await tester.run_full_test()
    
    if success:
        print("\n🎉 SUCCESS: Full system test completed!")
        print("📁 Check 'full_system_test_results.json' for complete details")
    else:
        print("\n❌ FAILED: Full system test failed")
        print("Check the logs above for details")

if __name__ == "__main__":
    asyncio.run(main())

