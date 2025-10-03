#!/usr/bin/env python3
"""
Test script to directly call the presenter service for audio generation.
"""

import asyncio
import json
import logging
from uuid import uuid4
import httpx

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_direct_audio_generation():
    """Test direct audio generation with the presenter service."""
    
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
        async with httpx.AsyncClient(timeout=120.0) as client:
            logger.info(f"🎙️ Generating audio for episode {episode_id}")
            logger.info(f"👤 Using presenter {presenter_id}")
            
            response = await client.post(
                "http://localhost:8004/generate-audio",
                json=audio_request
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info("✅ Audio generation successful!")
                logger.info(f"📁 Audio file: {result.get('audio_url', 'N/A')}")
                logger.info(f"⏱️ Duration: {result.get('duration_seconds', 'N/A')} seconds")
                logger.info(f"📊 File size: {result.get('file_size_bytes', 'N/A')} bytes")
                logger.info(f"🎵 Format: {result.get('format', 'N/A')}")
                return True
            else:
                logger.error(f"❌ Audio generation failed: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return False
                
    except Exception as e:
        logger.error(f"❌ Error in audio generation: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_direct_audio_generation())
    if success:
        logger.info("🎉 Direct audio generation test completed successfully!")
    else:
        logger.error("❌ Direct audio generation test failed!")

