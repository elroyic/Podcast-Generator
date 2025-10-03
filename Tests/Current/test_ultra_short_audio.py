"""Test with ultra-short script to see if generation completes."""
import requests
from uuid import uuid4

# Ultra-short test script (50 words)
ultra_short_script = """Speaker 1: Welcome to our test podcast.

Speaker 2: Thanks for having me.

Speaker 1: Today we're testing audio generation with a very short script of exactly fifty words to see if the system can complete without timing out.

Speaker 2: Let's see how it goes.

Speaker 1: Thank you for listening."""

print("="*70)
print("🎤 ULTRA-SHORT AUDIO TEST (50 words)")
print("="*70)
print(f"Script length: {len(ultra_short_script.split())} words")
print()

test_episode_id = str(uuid4())
print(f"Test Episode ID: {test_episode_id}")
print("🔄 Sending to TTS service (timeout: 120s)...")
print()

try:
    response = requests.post(
        "http://localhost:8015/generate-audio",
        json={
            "episode_id": test_episode_id,
            "script": ultra_short_script,
            "duration_seconds": 30
        },
        timeout=120  # 2 minutes
    )
    
    if response.status_code == 200:
        result = response.json()
        print("✅ AUDIO GENERATED SUCCESSFULLY!")
        print(f"   URL: {result.get('audio_url')}")
        print(f"   Duration: {result.get('duration_seconds')}s")
        print(f"   File Size: {result.get('file_size_bytes', 0) / 1024:.0f} KB")
        
        # Verify file
        import os
        audio_path = f"./storage/episodes/{test_episode_id}/audio.mp3"
        if os.path.exists(audio_path):
            file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
            print(f"✅ FILE VERIFIED: {file_size_mb:.2f} MB")
            
            from pydub import AudioSegment
            audio = AudioSegment.from_mp3(audio_path)
            actual_duration = len(audio) / 1000
            print(f"🎵 ACTUAL Duration: {actual_duration:.1f}s")
            
            if actual_duration > 10:
                print("\n🎉 SUCCESS! VibeVoice is generating audio!")
            else:
                print("\n⚠️  Audio very short - may indicate issues")
        else:
            print(f"❌ File not found at expected location")
    else:
        print(f"❌ Request failed: {response.status_code}")
        print(f"   Error: {response.text}")
        
except requests.exceptions.Timeout:
    print("❌ TIMEOUT after 120 seconds - still hanging")
    print("   Checking logs for clues...")
except Exception as e:
    print(f"❌ ERROR: {e}")

