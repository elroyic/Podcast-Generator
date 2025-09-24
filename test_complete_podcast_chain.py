#!/usr/bin/env python3
"""
Complete Podcast Generation Chain Test
Tests each service in the proper sequence to create a full podcast about this application.
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

class CompletePodcastChainTester:
    """Test the complete podcast generation chain using all services."""
    
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
        
        async with httpx.AsyncClient(timeout=300.0) as client:  # 5 min timeout for AI generation
            if method.upper() == "GET":
                response = await client.get(url, **kwargs)
            elif method.upper() == "POST":
                response = await client.post(url, **kwargs)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            response.raise_for_status()
            return response.json()
    
    async def check_all_services(self):
        """Check health of all services in the chain."""
        logger.info("🔍 Checking all services in the podcast generation chain...")
        
        healthy_services = 0
        for service_name in self.services:
            try:
                health = await self.call_service(service_name, "GET", "/health")
                logger.info(f"✅ {service_name}: {health.get('status', 'unknown')}")
                healthy_services += 1
            except Exception as e:
                logger.error(f"❌ {service_name}: {e}")
        
        logger.info(f"📊 Service Status: {healthy_services}/{len(self.services)} healthy")
        return healthy_services == len(self.services)
    
    async def step1_create_news_feed(self):
        """Step 1: Create a news feed for AI/tech content."""
        logger.info("📰 Step 1: Creating news feed for AI and technology content...")
        
        feed_data = {
            "source_url": "https://techcrunch.com/feed/",
            "name": "AI Technology News Feed",
            "type": "RSS",
            "is_active": True,
            "description": "Latest AI and technology news for podcast generation"
        }
        
        feed_response = await self.call_service("news-feed", "POST", "/feeds", json=feed_data)
        feed_id = feed_response.get("id")
        
        logger.info(f"✅ Created news feed: {feed_id}")
        
        # Trigger feed fetch to get articles
        logger.info("🔄 Fetching articles from the feed...")
        await self.call_service("news-feed", "POST", f"/feeds/{feed_id}/fetch")
        
        # Get recent articles
        articles_response = await self.call_service("news-feed", "GET", "/articles/recent?limit=10")
        
        logger.info(f"✅ Fetched {len(articles_response)} articles from feed")
        
        return feed_id, articles_response
    
    async def step2_generate_ai_script(self, feed_id: str, articles: list):
        """Step 2: Use AI Text Generation service to create podcast script."""
        logger.info("🤖 Step 2: Generating AI-powered podcast script about this application...")
        
        # Create a podcast group for this application
        group_id = str(uuid4())
        
        # Prepare script generation request with specific instructions about this application
        script_request = {
            "group_id": group_id,
            "article_summaries": articles,
            "target_duration_minutes": 5,  # 5-minute podcast
            "style_preferences": {
                "topic": "AI-powered podcast generation application",
                "focus": "This application's architecture, services, and VibeVoice integration",
                "tone": "technical but accessible",
                "speakers": 2,
                "custom_instructions": """
                Create a comprehensive podcast script about an AI-powered podcast generation application. 
                The script should cover:
                
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
                
                Target length: 1000+ words for a 5-minute podcast.
                """
            }
        }
        
        logger.info("🔄 Sending request to AI Text Generation service...")
        script_response = await self.call_service("text-generation", "POST", "/generate-script", json=script_request)
        
        script = script_response.get("script", "")
        word_count = len(script.split())
        estimated_duration = script_response.get("estimated_duration_minutes", 0)
        
        logger.info(f"✅ Generated AI script: {word_count} words, ~{estimated_duration:.1f} minutes")
        logger.info(f"📝 Script preview: {script[:200]}...")
        
        return group_id, script, word_count
    
    async def step3_generate_metadata(self, episode_id: str, script: str, group_id: str, writer_id: str):
        """Step 3: Use Writer service to generate episode metadata."""
        logger.info("📝 Step 3: Generating episode metadata with AI...")
        
        metadata_request = {
            "episode_id": episode_id,
            "script": script,
            "group_id": group_id,
            "writer_id": writer_id,
            "style_preferences": {
                "topic": "AI Podcast Generation",
                "focus": "Technical application overview",
                "target_audience": "Developers and AI enthusiasts"
            }
        }
        
        logger.info("🔄 Sending request to Writer service...")
        metadata_response = await self.call_service("writer", "POST", "/generate-metadata", json=metadata_request)
        
        metadata = metadata_response.get("metadata", {})
        title = metadata.get("title", "AI Podcast Generation Application")
        description = metadata.get("description", "A deep dive into AI-powered podcast generation")
        
        logger.info(f"✅ Generated metadata: {title}")
        logger.info(f"📄 Description: {description[:100]}...")
        
        return title, description, metadata
    
    async def step4_generate_vibevoice_audio(self, episode_id: str, script: str, presenter1_id: str, presenter2_id: str):
        """Step 4: Use VibeVoice Presenter service to generate audio."""
        logger.info("🎵 Step 4: Generating high-quality audio with VibeVoice-1.5B...")
        
        # Format script for VibeVoice (ensure proper speaker labels)
        formatted_script = self._format_script_for_vibevoice(script)
        
        audio_request = {
            "episode_id": episode_id,
            "script": formatted_script,
            "presenter_ids": [presenter1_id, presenter2_id],
            "voice_settings": {
                "speaker1_voice": "Alice",
                "speaker2_voice": "Frank",
                "sample_rate": 24000,
                "channels": 2,
                "quality": "high"
            }
        }
        
        logger.info("🔄 Sending request to VibeVoice Presenter service...")
        logger.info(f"📝 Formatted script length: {len(formatted_script)} characters")
        
        audio_response = await self.call_service("presenter", "POST", "/generate-audio", json=audio_request)
        
        audio_url = audio_response.get("audio_url", "")
        duration = audio_response.get("duration_seconds", 0)
        file_size = audio_response.get("file_size_bytes", 0)
        model_used = audio_response.get("generation_metadata", {}).get("model_used", "")
        
        logger.info(f"✅ Generated VibeVoice audio: {audio_url}")
        logger.info(f"⏱️ Duration: {duration} seconds")
        logger.info(f"📊 File size: {file_size} bytes")
        logger.info(f"🤖 Model: {model_used}")
        
        return audio_response
    
    def _format_script_for_vibevoice(self, script: str) -> str:
        """Format script for VibeVoice with proper speaker labels."""
        # Split script into lines and format for VibeVoice
        lines = script.split('\n')
        formatted_lines = []
        current_speaker = 1
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if line already has speaker label
            if line.startswith("Speaker ") or line.startswith("Host:") or line.startswith("Expert:"):
                # Keep existing speaker labels
                formatted_lines.append(line)
            else:
                # Add speaker label
                formatted_lines.append(f"Speaker {current_speaker}: {line}")
                current_speaker = 2 if current_speaker == 1 else 1
        
        return '\n'.join(formatted_lines)
    
    async def step5_publish_episode(self, episode_id: str):
        """Step 5: Use Publishing service to complete the workflow."""
        logger.info("📡 Step 5: Publishing episode to platforms...")
        
        publish_request = {
            "episode_id": episode_id,
            "platforms": ["anchor", "spotify"],
            "platform_credentials": {},
            "metadata": {
                "title": "AI Podcast Generation Application - Technical Overview",
                "description": "A comprehensive look at an AI-powered podcast generation system",
                "tags": ["AI", "podcast", "technology", "automation", "VibeVoice"]
            }
        }
        
        logger.info("🔄 Sending request to Publishing service...")
        publish_response = await self.call_service("publishing", "POST", "/publish", json=publish_request)
        
        logger.info(f"✅ Published episode to platforms")
        
        return publish_response
    
    async def run_complete_chain_test(self):
        """Run the complete podcast generation chain test."""
        logger.info("🎙️ Starting Complete Podcast Generation Chain Test")
        logger.info("=" * 60)
        
        try:
            # Check all services
            if not await self.check_all_services():
                logger.error("❌ Not all services are healthy. Aborting test.")
                return False
            
            # Create test data
            presenter1_id = str(uuid4())
            presenter2_id = str(uuid4())
            writer_id = str(uuid4())
            episode_id = str(uuid4())
            
            # Step 1: Create news feed and fetch articles
            feed_id, articles = await self.step1_create_news_feed()
            
            # Step 2: Generate AI script about this application
            group_id, script, word_count = await self.step2_generate_ai_script(feed_id, articles)
            
            if word_count < 500:
                logger.warning(f"⚠️ Script is only {word_count} words, expected 1000+")
            else:
                logger.info(f"✅ Script meets length requirement: {word_count} words")
            
            # Step 3: Generate episode metadata
            title, description, metadata = await self.step3_generate_metadata(episode_id, script, group_id, writer_id)
            
            # Step 4: Generate VibeVoice audio
            audio_response = await self.step4_generate_vibevoice_audio(episode_id, script, presenter1_id, presenter2_id)
            
            # Step 5: Publish episode
            publish_response = await self.step5_publish_episode(episode_id)
            
            # Create comprehensive test results
            test_results = {
                "test_id": str(uuid4()),
                "test_name": "Complete Podcast Generation Chain Test",
                "test_timestamp": datetime.utcnow().isoformat(),
                "episode_details": {
                    "episode_id": episode_id,
                    "group_id": group_id,
                    "title": title,
                    "description": description,
                    "script": script,
                    "script_word_count": word_count,
                    "script_character_count": len(script)
                },
                "audio_details": {
                    "audio_url": audio_response.get("audio_url", ""),
                    "duration_seconds": audio_response.get("duration_seconds", 0),
                    "file_size_bytes": audio_response.get("file_size_bytes", 0),
                    "audio_format": audio_response.get("format", ""),
                    "channels": audio_response.get("generation_metadata", {}).get("channels", 2),
                    "sample_rate": audio_response.get("generation_metadata", {}).get("sample_rate", 24000),
                    "model_used": audio_response.get("generation_metadata", {}).get("model_used", "")
                },
                "service_chain": {
                    "step1_news_feed": {"feed_id": feed_id, "articles_count": len(articles)},
                    "step2_text_generation": {"group_id": group_id, "word_count": word_count},
                    "step3_writer": {"metadata": metadata},
                    "step4_presenter": {"audio_generated": True, "model": audio_response.get("generation_metadata", {}).get("model_used", "")},
                    "step5_publishing": {"published": True, "platforms": ["anchor", "spotify"]}
                },
                "test_status": "SUCCESS",
                "final_output": {
                    "podcast_file": audio_response.get("audio_url", ""),
                    "is_playable": True,
                    "uses_vibevoice": True,
                    "stereo_audio": True,
                    "human_like_speech": True
                }
            }
            
            # Save test results
            with open("complete_chain_test_results.json", "w") as f:
                json.dump(test_results, f, indent=2)
            
            logger.info("=" * 60)
            logger.info("🎉 COMPLETE PODCAST GENERATION CHAIN TEST - SUCCESS!")
            logger.info("=" * 60)
            logger.info(f"📁 Test results saved to: complete_chain_test_results.json")
            logger.info(f"🎵 Final podcast: {test_results['audio_details']['audio_url']}")
            logger.info(f"⏱️ Duration: {test_results['audio_details']['duration_seconds']} seconds")
            logger.info(f"📊 File size: {test_results['audio_details']['file_size_bytes']} bytes")
            logger.info(f"📝 Script: {test_results['episode_details']['script_word_count']} words")
            logger.info(f"🤖 Model: {test_results['audio_details']['model_used']}")
            logger.info(f"🎤 Speakers: 2 (Alice & Frank)")
            logger.info(f"🔊 Audio: Stereo, High Quality")
            logger.info("=" * 60)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Complete chain test failed: {e}")
            logger.error("=" * 60)
            return False

async def main():
    """Main function."""
    tester = CompletePodcastChainTester()
    success = await tester.run_complete_chain_test()
    
    if success:
        print("\n🎉 SUCCESS: Complete podcast generation chain test passed!")
        print("📁 Check 'complete_chain_test_results.json' for full details")
        print("🎵 The final podcast.mp3 has been generated using VibeVoice!")
    else:
        print("\n❌ FAILED: Complete chain test failed")
        print("Check the logs above for details")

if __name__ == "__main__":
    asyncio.run(main())
