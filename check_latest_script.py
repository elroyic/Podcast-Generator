"""Check the latest generated script quality."""
import sys
import os
from uuid import UUID

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shared.database import SessionLocal
from shared.models import Episode
from datetime import datetime, timedelta

db = SessionLocal()

try:
    # Get most recent episode
    recent_episodes = db.query(Episode).filter(
        Episode.created_at > datetime.utcnow() - timedelta(hours=2)
    ).order_by(Episode.created_at.desc()).limit(3).all()
    
    if not recent_episodes:
        print("❌ No recent episodes found!")
        sys.exit(1)
    
    for i, episode in enumerate(recent_episodes):
        print("="*70)
        print(f"📻 EPISODE {i+1}: {episode.id}")
        print("="*70)
        print(f"Status: {episode.status}")
        print(f"Created: {episode.created_at}")
        
        if episode.script:
            word_count = len(episode.script.split())
            est_minutes = word_count / 150
            
            # Count speakers
            speaker_count = 0
            for j in range(1, 5):
                if f"Speaker {j}:" in episode.script:
                    speaker_count += 1
            
            # Check for presenter names
            has_presenter_names = "Sam" in episode.script or "Insider" in episode.script
            
            print(f"\n📊 Script Stats:")
            print(f"  Words: {word_count}")
            print(f"  Est. Duration: {est_minutes:.1f} minutes")
            print(f"  Speakers: {speaker_count}")
            print(f"  Has Presenter Names: {has_presenter_names}")
            
            # Show first 500 chars
            print(f"\n📝 Script Preview:")
            print("-"*70)
            preview = episode.script[:800]
            # Clean <think> tags for display
            import re
            preview = re.sub(r'<think>.*?</think>', '[THINK TAG REMOVED]', preview, flags=re.DOTALL)
            print(preview)
            if len(episode.script) > 800:
                print("\n... (truncated)")
            print("-"*70)
        else:
            print("\n❌ No script found!")
        print()
    
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()

