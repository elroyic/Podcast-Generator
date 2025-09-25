#!/usr/bin/env python3
"""
Test script to trigger episode generation through the proper API.
"""

import asyncio
import json
import logging
from uuid import uuid4
import httpx

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_episode_generation():
    """Test the integrated episode generation."""
    
    # Use the Spring Weather podcast group ID we created earlier
    group_id = "8b4fb371-611a-4e78-a72e-6f859f1dae78"
    
    request_data = {
        "group_id": group_id,
        "force_regenerate": False
    }
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            logger.info(f"🎬 Triggering episode generation for group {group_id}")
            
            response = await client.post(
                "http://localhost:8000/api/generate-episode",
                json=request_data
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info("✅ Episode generation triggered successfully!")
                logger.info(f"📋 Response: {json.dumps(result, indent=2)}")
                
                # Check if we got a task ID
                if "episode_id" in result:
                    episode_id = result["episode_id"]
                    logger.info(f"🎙️ Episode ID: {episode_id}")
                
                if "status" in result:
                    status = result["status"]
                    logger.info(f"📊 Status: {status}")
                
                return True
            else:
                logger.error(f"❌ Episode generation failed: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return False
                
    except Exception as e:
        logger.error(f"❌ Error triggering episode generation: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_episode_generation())
    if success:
        logger.info("🎉 Episode generation test completed!")
    else:
        logger.error("❌ Episode generation test failed!")
