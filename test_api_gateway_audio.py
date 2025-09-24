#!/usr/bin/env python3
"""
Test script to test the API Gateway's call_service function directly.
"""

import asyncio
import json
import logging
from uuid import uuid4
import httpx

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def call_service(service_name: str, method: str, endpoint: str, **kwargs):
    """Make HTTP request to a microservice."""
    SERVICE_URLS = {
        "news-feed": "http://localhost:8001",
        "text-generation": "http://localhost:8002", 
        "writer": "http://localhost:8003",
        "presenter": "http://localhost:8004",
        "publishing": "http://localhost:8005",
        "podcast-host": "http://localhost:8006"
    }
    
    if service_name not in SERVICE_URLS:
        raise Exception(f"Unknown service: {service_name}")
    
    url = f"{SERVICE_URLS[service_name]}{endpoint}"
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        raise Exception(f"HTTP error: {e.response.status_code} - {e.response.text}")
    except Exception as e:
        raise Exception(f"Service communication error: {str(e)}")

async def test_api_gateway_audio():
    """Test the API Gateway's audio generation through call_service."""
    
    # Create a test episode ID and script
    episode_id = str(uuid4())
    presenter_id = "b6512094-017b-4483-af6c-5c2d0a231a40"  # Alex Weather presenter ID from setup
    
    script = """Welcome to Spring Weather Watch! I'm Alex Weather, and today we're talking about a phenomenon many of us are experiencing this season: Spring is here, but the rain hasn't come yet.

It's that time of year when we expect to see flowers blooming, trees budding, and gentle spring showers watering our gardens. But this year seems different. The temperatures are warming up nicely, and we're getting plenty of sunshine, but those refreshing spring rains that usually accompany the season are noticeably absent.

This dry spring pattern can have several implications. For gardeners, it means we need to be more diligent about watering our plants. The soil is warming up, which is great for seed germination, but without natural rainfall, our gardens need extra attention.

That's all for today's Spring Weather Watch. Remember to stay hydrated, water your gardens responsibly, and enjoy the beautiful spring weather while it lasts. Until next time, keep looking up at the sky!

This has been Spring Weather Watch with Alex Weather. Thank you for listening!"""
    
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
    
    try:
        logger.info(f"🎙️ Testing API Gateway audio generation for episode {episode_id}")
        logger.info(f"👤 Using presenter {presenter_id}")
        
        # Test the call_service function directly
        audio_response = await call_service("presenter", "POST", "/generate-audio", json=audio_request)
        
        logger.info("✅ API Gateway audio generation successful!")
        logger.info(f"📁 Audio file: {audio_response.get('audio_url', 'N/A')}")
        logger.info(f"⏱️ Duration: {audio_response.get('duration_seconds', 'N/A')} seconds")
        logger.info(f"📊 File size: {audio_response.get('file_size_bytes', 'N/A')} bytes")
        logger.info(f"🎵 Format: {audio_response.get('format', 'N/A')}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error in API Gateway audio generation: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_api_gateway_audio())
    if success:
        logger.info("🎉 API Gateway audio generation test completed successfully!")
    else:
        logger.error("❌ API Gateway audio generation test failed!")

