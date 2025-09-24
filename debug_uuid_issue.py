#!/usr/bin/env python3
"""
Debug the UUID serialization issue.
"""

import asyncio
import json
import logging
from uuid import uuid4
import httpx

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def debug_uuid_issue():
    """Debug the UUID serialization issue."""
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Create a simple request with a UUID
            group_id = str(uuid4())
            episode_request = {
                "group_id": group_id,  # Already a string
                "force_regenerate": False
            }
            
            logger.info(f"Request data: {json.dumps(episode_request, indent=2)}")
            
            # Try to send the request
            response = await client.post(
                "http://localhost:8000/api/generate-episode",
                json=episode_request
            )
            
            logger.info(f"Response status: {response.status_code}")
            logger.info(f"Response: {response.text}")
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Error: {e}")
            return False

if __name__ == "__main__":
    success = asyncio.run(debug_uuid_issue())
    if success:
        logger.info("✅ Debug test successful!")
    else:
        logger.error("❌ Debug test failed!")

