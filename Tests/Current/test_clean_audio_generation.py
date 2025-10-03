"""Test audio generation with a CLEAN script (no think tags, plain Speaker labels)."""
import requests
from uuid import uuid4

# Create a clean test script
clean_script = """Speaker 1: Welcome to Talking Boks! I'm Sam General Insider, and this is a test of our audio generation system.

Speaker 2: And I'm Sam News Insider. Thanks for joining us today. We're testing if VibeVoice can properly generate audio when given a clean, properly formatted script.

Speaker 1: That's right. The key is making sure we use plain text Speaker labels, no markdown formatting, and definitely no think tags or XML elements.

Speaker 2: Exactly. This script is intentionally short, about three hundred words, just to verify that the basic audio generation pipeline works correctly.

Speaker 1: We've discovered that when scripts contain markdown asterisks like double asterisk Speaker one colon double asterisk, or when they include think tags with reasoning inside them, VibeVoice cannot parse those lines.

Speaker 2: Right, and that results in either very short audio files, just one second long, or complete failures. So this test uses perfectly clean formatting to establish a baseline.

Speaker 1: If this works, we'll know that VibeVoice itself is functioning properly, and the issue is purely with script cleaning and formatting from our language models.

Speaker 2: Let's wrap up this test. If you're hearing this as a properly voiced podcast with both of our voices, then we've successfully isolated the problem and can focus on fixing the script generation side.

Speaker 1: Thank you for listening to this technical test of Talking Boks. Stay tuned for our regular programming with much more in-depth content.

Speaker 2: We'll see you next time!"""

print("="*70)
print("🎤 TESTING CLEAN AUDIO GENERATION")
print("="*70)
print(f"Script length: {len(clean_script.split())} words")
print(f"Expected duration: ~{len(clean_script.split())/150:.1f} minutes")
print()

test_episode_id = str(uuid4())
print(f"Test Episode ID: {test_episode_id}")
print()
print("🔄 Sending to Presenter service...")

try:
    response = requests.post(
        "http://localhost:8015/generate-audio",
        json={
            "episode_id": test_episode_id,
            "script": clean_script,
            "duration_seconds": 120
        },
        timeout=300  # 5 minutes
    )
    
    if response.status_code == 200:
        result = response.json()
        print("✅ AUDIO GENERATED SUCCESSFULLY!")
        print(f"   URL: {result.get('audio_url')}")
        print(f"   Duration: {result.get('duration_seconds')}s (~{result.get('duration_seconds', 0)/60:.1f} minutes)")
        print(f"   File Size: {result.get('file_size_bytes', 0) / 1024:.0f} KB")
        print(f"   Format: {result.get('format')}")
        print()
        
        # Verify file actually exists
        import os
        audio_path = f"./storage/episodes/{test_episode_id}/audio.mp3"
        if os.path.exists(audio_path):
            file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
            print(f"✅ FILE VERIFIED: {audio_path}")
            print(f"   Actual size: {file_size_mb:.2f} MB")
            
            # Check actual duration
            from pydub import AudioSegment
            audio = AudioSegment.from_mp3(audio_path)
            actual_duration = len(audio) / 1000
            print(f"   🎵 ACTUAL Duration: {actual_duration:.1f}s ({actual_duration/60:.1f} minutes)")
            print()
            
            if actual_duration > 60:
                print("🎉 SUCCESS! VibeVoice is working with clean scripts!")
            else:
                print("⚠️  Audio too short - may indicate parsing issues")
        else:
            print(f"❌ File not found at expected location")
    else:
        print(f"❌ Request failed: {response.status_code}")
        print(f"   Error: {response.text}")
        
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

