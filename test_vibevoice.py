#!/usr/bin/env python3
"""
Test script for VibeVoice service
"""

import requests
import json
from uuid import uuid4

def test_vibevoice_service():
    """Test the VibeVoice service directly."""
    
    url = "http://localhost:8004/generate-audio"
    
    # Test data with proper UUIDs
    test_data = {
        "episode_id": str(uuid4()),
        "script": "Hello, this is a test of the VibeVoice service. Can you hear me clearly?",
        "presenter_ids": [str(uuid4())],
        "voice_settings": {}
    }
    
    try:
        print("Testing VibeVoice service...")
        print(f"URL: {url}")
        print(f"Data: {json.dumps(test_data, indent=2)}")
        
        response = requests.post(url, json=test_data, timeout=60)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ VibeVoice service working!")
            print(f"Audio URL: {result.get('audio_url')}")
            print(f"File size: {result.get('file_size_bytes')} bytes")
            print(f"Duration: {result.get('duration_seconds')} seconds")
        else:
            print("❌ VibeVoice service failed!")
            
    except Exception as e:
        print(f"❌ Error testing VibeVoice service: {e}")

if __name__ == "__main__":
    test_vibevoice_service()
