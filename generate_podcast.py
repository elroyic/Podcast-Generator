#!/usr/bin/env python3
"""
Generate a 30-second podcast episode using the simplified services.
"""

import asyncio
import httpx
import json
from datetime import datetime
from uuid import uuid4

class PodcastGenerator:
    """Generates a complete podcast episode."""
    
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.client = httpx.AsyncClient(timeout=60.0)
    
    async def create_test_data(self):
        """Create test data for podcast generation."""
        print("📝 Creating test data...")
        
        # Create presenter
        presenter_data = {
            "name": "Tech Talk Sarah",
            "bio": "A technology enthusiast who loves discussing the latest in AI and software development.",
            "gender": "female",
            "country": "US",
            "city": "San Francisco",
            "specialties": ["technology", "AI"],
            "expertise": ["software development", "machine learning"],
            "interests": ["podcasting", "technology"]
        }
        
        response = await self.client.post(f"{self.base_url}/api/presenters", json=presenter_data)
        presenter = response.json()
        print(f"✅ Created presenter: {presenter['name']}")
        
        # Create writer
        writer_data = {
            "name": "AI Content Writer",
            "capabilities": ["title", "description", "tags", "keywords", "category"]
        }
        
        response = await self.client.post(f"{self.base_url}/api/writers", json=writer_data)
        writer = response.json()
        print(f"✅ Created writer: {writer['name']}")
        
        # Create news feed
        feed_data = {
            "source_url": "https://feeds.bbci.co.uk/news/technology/rss.xml",
            "name": "BBC Technology Test Feed",
            "type": "RSS",
            "is_active": True
        }
        
        response = await self.client.post(f"{self.base_url}/api/news-feeds", json=feed_data)
        feed = response.json()
        print(f"✅ Created news feed: {feed['name']}")
        
        return presenter['id'], writer['id'], feed['id']
    
    async def create_podcast_group(self, presenter_id, writer_id, feed_id):
        """Create a podcast group."""
        print("🎙️ Creating podcast group...")
        
        group_data = {
            "name": "30-Second Tech Brief",
            "description": "A quick 30-second tech news podcast for testing",
            "category": "Technology",
            "subcategory": "News",
            "language": "en",
            "country": "US",
            "tags": ["technology", "news", "brief"],
            "keywords": ["tech news", "AI", "software"],
            "schedule": "0 9 * * 1",
            "status": "active",
            "presenter_ids": [presenter_id],
            "writer_id": writer_id,
            "news_feed_ids": [feed_id]
        }
        
        response = await self.client.post(f"{self.base_url}/api/podcast-groups", json=group_data)
        group = response.json()
        print(f"✅ Created podcast group: {group['name']}")
        
        return group['id']
    
    async def generate_script(self, group_id):
        """Generate a 30-second podcast script."""
        print("📝 Generating script...")
        
        # Create mock articles for a 30-second episode
        mock_articles = [
            {
                "id": str(uuid4()),
                "title": "AI Breakthrough in Healthcare",
                "summary": "New AI technology helps doctors diagnose diseases faster and more accurately.",
                "link": "https://example.com/ai-healthcare",
                "publish_date": datetime.utcnow().isoformat()
            },
            {
                "id": str(uuid4()),
                "title": "Tech Stocks Rise on Strong Earnings",
                "summary": "Major technology companies report better than expected quarterly results.",
                "link": "https://example.com/tech-stocks",
                "publish_date": datetime.utcnow().isoformat()
            }
        ]
        
        script_request = {
            "group_id": group_id,
            "article_summaries": mock_articles,
            "target_duration_minutes": 1  # 1 minute (minimum allowed)
        }
        
        response = await self.client.post("http://localhost:8002/generate-script", json=script_request)
        script_result = response.json()
        
        print(f"✅ Generated script ({len(script_result['script'])} characters)")
        return script_result['script']
    
    async def generate_audio(self, episode_id, script):
        """Generate audio from script."""
        print("🎵 Generating audio...")
        
        # Create a mock episode ID for audio generation
        audio_request = {
            "episode_id": episode_id,
            "script": script,
            "presenter_ids": [str(uuid4())]  # Generate a valid UUID
        }
        
        response = await self.client.post("http://localhost:8004/generate-audio", json=audio_request)
        audio_result = response.json()
        
        print(f"✅ Generated audio: {audio_result['audio_url']}")
        print(f"   Duration: {audio_result['duration_seconds']} seconds")
        print(f"   File size: {audio_result['file_size_bytes']} bytes")
        
        return audio_result
    
    async def generate_metadata(self, episode_id, script, group_id):
        """Generate episode metadata."""
        print("📊 Generating metadata...")
        
        metadata_request = {
            "episode_id": episode_id,
            "script": script,
            "group_id": group_id
        }
        
        response = await self.client.post("http://localhost:8003/generate-metadata", json=metadata_request)
        metadata_result = response.json()
        
        print(f"✅ Generated metadata: {metadata_result['metadata']['title']}")
        return metadata_result['metadata']
    
    async def publish_episode(self, episode_id):
        """Publish the episode."""
        print("📤 Publishing episode...")
        
        publish_request = {
            "episode_id": episode_id,
            "platforms": ["local_podcast_host", "local_rss_feed"],
            "platform_credentials": {}
        }
        
        response = await self.client.post("http://localhost:8005/publish", json=publish_request)
        publish_result = response.json()
        
        print(f"✅ Published to {len(publish_result['publish_records'])} platforms")
        return publish_result
    
    async def generate_complete_episode(self):
        """Generate a complete 30-second podcast episode."""
        print("🚀 Starting 30-second podcast generation...")
        print("=" * 50)
        
        try:
            # Step 1: Create test data
            presenter_id, writer_id, feed_id = await self.create_test_data()
            
            # Step 2: Create podcast group
            group_id = await self.create_podcast_group(presenter_id, writer_id, feed_id)
            
            # Step 3: Generate script
            script = await self.generate_script(group_id)
            
            # Step 4: Create episode record
            episode_id = str(uuid4())
            print(f"📝 Created episode: {episode_id}")
            
            # Step 5: Generate audio
            audio_result = await self.generate_audio(episode_id, script)
            
            # Step 6: Generate metadata
            metadata = await self.generate_metadata(episode_id, script, group_id)
            
            # Step 7: Publish episode
            publish_result = await self.publish_episode(episode_id)
            
            print("\n" + "=" * 50)
            print("🎉 30-SECOND PODCAST GENERATION COMPLETE!")
            print("=" * 50)
            print(f"Episode ID: {episode_id}")
            print(f"Title: {metadata['title']}")
            print(f"Duration: {audio_result['duration_seconds']} seconds")
            print(f"Audio URL: {audio_result['audio_url']}")
            print(f"Published to: {len(publish_result['publish_records'])} platforms")
            
            # Display the script
            print(f"\n📝 Script Preview:")
            print("-" * 30)
            print(script[:200] + "..." if len(script) > 200 else script)
            print("-" * 30)
            
            return {
                "episode_id": episode_id,
                "title": metadata['title'],
                "script": script,
                "audio_url": audio_result['audio_url'],
                "duration_seconds": audio_result['duration_seconds'],
                "publish_records": publish_result['publish_records']
            }
            
        except Exception as e:
            print(f"❌ Error generating podcast: {e}")
            raise
        finally:
            await self.client.aclose()


async def main():
    """Main function."""
    generator = PodcastGenerator()
    
    try:
        result = await generator.generate_complete_episode()
        
        print(f"\n✅ Successfully generated 30-second podcast!")
        print(f"📁 Audio file location: {result['audio_url']}")
        
        # Save results to file
        with open('/tmp/podcast_generation_result.json', 'w') as f:
            json.dump(result, f, indent=2, default=str)
        print(f"💾 Results saved to: /tmp/podcast_generation_result.json")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to generate podcast: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)