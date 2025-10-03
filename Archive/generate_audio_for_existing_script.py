"""Generate audio for the existing 1633-word script."""
import requests
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shared.database import SessionLocal
from shared.models import Episode
from uuid import UUID

db = SessionLocal()

try:
    # Get the episode with the good script (1633 words)
    episode_id = UUID("458390d4-2abf-4323-bf72-81020ee0d78c")
    episode = db.query(Episode).filter(Episode.id == episode_id).first()
    
    if not episode or not episode.script:
        print("❌ Episode or script not found!")
        sys.exit(1)
    
    word_count = len(episode.script.split())
    print(f"📝 Script: {word_count} words (~{word_count/150:.1f} minutes)")
    print(f"📻 Episode: {episode.id}")
    print(f"🎯 Status: {episode.status}")
    print()
    
    # Call Presenter directly to generate audio
    print("🎤 Generating audio via Presenter service...")
    response = requests.post(
        "http://localhost:8004/generate-audio",
        json={
            "episode_id": str(episode.id),
            "script": episode.script,
            "presenter_ids": []
        },
        timeout=180
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Audio generated!")
        print(f"   URL: {result.get('audio_url')}")
        print(f"   Duration: {result.get('duration_seconds')}s (~{result.get('duration_seconds', 0)//60} minutes)")
        print(f"   File Size: {result.get('file_size_bytes', 0) // 1024} KB")
        print(f"   Format: {result.get('format')}")
    else:
        print(f"❌ Failed: {response.status_code}")
        print(f"   Error: {response.text}")
        
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()

