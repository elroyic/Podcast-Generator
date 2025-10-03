"""
Generate Audio ONLY - Sequential Quality Mode
=============================================
All non-essential services are shut down.
Presenter has clean GPU state.
Let it take as long as needed!
"""

import requests
import time
import sys
sys.path.insert(0, '.')

from shared.database import SessionLocal
from shared.models import Episode

print("="*80)
print("🎤 AUDIO GENERATION - SEQUENTIAL MODE")
print("="*80)
print()

# Get script from database
db = SessionLocal()
try:
    episode = db.query(Episode).filter(
        Episode.id == "6f4ce57f-3c31-442c-9366-82ffac33e661"
    ).first()
    
    if not episode or not episode.script:
        print("❌ No script found!")
        sys.exit(1)
    
    script = episode.script
    word_count = len(script.split())
    
    print(f"📝 Script: {word_count} words")
    print(f"📦 Episode: {episode.id}")
    print()
finally:
    db.close()

# Wait for Presenter to fully load
print("⏳ Waiting for VibeVoice to load (60 seconds)...")
time.sleep(60)

# Check if Presenter is ready
print("🔍 Checking Presenter health...")
try:
    health = requests.get("http://localhost:8004/health", timeout=10)
    if health.status_code == 200:
        print("✅ Presenter is ready!")
    else:
        print(f"⚠️  Presenter health check: {health.status_code}")
except Exception as e:
    print(f"⚠️  Presenter may still be loading: {e}")

print()
print("="*80)
print("🚀 GENERATING AUDIO WITH ALL GPU RESOURCES")
print("="*80)
print()
print(f"Target: ~7 minutes of audio")
print(f"Strategy: NO TIMEOUT - let it run!")
print(f"Current setup: 8GB VRAM (tight but possible)")
print(f"New hardware: 96GB VRAM (will be fast!)")
print()
print("⏰ Starting generation... (may take 1-12 hours)")
print()

start_time = time.time()

try:
    response = requests.post(
        "http://localhost:8004/generate-audio",
        json={
            "episode_id": "6f4ce57f-3c31-442c-9366-82ffac33e661",
            "script": script,
            "presenter_ids": []
        },
        timeout=43200  # 12 HOURS - no rush!
    )
    
    elapsed = time.time() - start_time
    
    if response.status_code == 200:
        result = response.json()
        
        print()
        print("="*80)
        print("🎉 AUDIO GENERATION COMPLETE!")
        print("="*80)
        print(f"⏱️  Time: {elapsed/60:.1f} minutes")
        print(f"🎵 Duration: {result.get('duration_seconds')}s ({result.get('duration_seconds', 0)//60} minutes)")
        print(f"📁 URL: {result.get('audio_url')}")
        print(f"💾 Size: {result.get('file_size_bytes', 0) / (1024*1024):.2f} MB")
        print()
        print("✅ POC PODCAST READY FOR DEMONSTRATION!")
        print()
    else:
        print(f"❌ Generation failed: {response.status_code}")
        print(f"   Response: {response.text[:500]}")
        
except requests.exceptions.Timeout:
    print(f"⏱️  Still running after {(time.time() - start_time)/3600:.1f} hours")
    print("   Check logs: docker compose logs presenter -f")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print()
print("📊 Monitor in real-time:")
print("   docker compose logs presenter -f")

