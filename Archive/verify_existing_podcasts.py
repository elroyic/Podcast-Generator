"""Verify all episodes from today and check actual audio files."""
import os
import sys
from datetime import datetime, timedelta, timezone
from uuid import UUID

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shared.database import SessionLocal
from shared.models import Episode, EpisodeStatus

db = SessionLocal()

try:
    # Get all episodes from today
    utc_now = datetime.now(timezone.utc)
    today_start = utc_now - timedelta(hours=8)
    
    episodes = db.query(Episode).filter(
        Episode.created_at > today_start
    ).order_by(Episode.created_at.desc()).all()
    
    print("="*70)
    print(f"📻 ALL EPISODES FROM TODAY ({len(episodes)} total)")
    print("="*70)
    print()
    
    for episode in episodes:
        print(f"ID: {episode.id}")
        print(f"  Status: {episode.status}")
        print(f"  Created: {episode.created_at}")
        
        if episode.script:
            word_count = len(episode.script.split())
            print(f"  Script: {word_count} words (~{word_count/150:.1f} min)")
        else:
            print(f"  Script: None")
        
        # Check for actual audio file
        audio_path = f"./storage/episodes/{episode.id}/audio.mp3"
        if os.path.exists(audio_path):
            file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
            print(f"  ✅ Audio: EXISTS ({file_size_mb:.2f} MB)")
            
            # Try to get duration using mutagen or pydub
            try:
                from pydub import AudioSegment
                audio = AudioSegment.from_mp3(audio_path)
                duration_sec = len(audio) / 1000
                print(f"  🎵 ACTUAL Duration: {duration_sec:.1f}s ({duration_sec/60:.1f} minutes)")
            except:
                print(f"  ⚠️  Duration: Could not read")
        else:
            print(f"  ❌ Audio: NOT FOUND")
        
        print()
    
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()

