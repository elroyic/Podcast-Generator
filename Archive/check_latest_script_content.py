"""Check the latest script to see what's in it."""
import sys
import os
from uuid import UUID

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shared.database import SessionLocal
from shared.models import Episode

db = SessionLocal()

try:
    episode_id = UUID("5e8e3466-50e0-4ec1-a4d4-adc19a1e7fa9")
    episode = db.query(Episode).filter(Episode.id == episode_id).first()
    
    if not episode or not episode.script:
        print("❌ Episode or script not found!")
        sys.exit(1)
    
    print(f"📝 Script for Episode {episode.id}")
    print(f"   Words: {len(episode.script.split())}")
    print("="*70)
    
    # Show first 2000 characters to see structure
    print(episode.script[:2000])
    print("\n... (truncated)")
    print("="*70)
    
    # Check for problematic patterns
    issues = []
    if '<think>' in episode.script or '</think>' in episode.script:
        issues.append("❌ Contains <think> tags")
    if '===' in episode.script:
        issues.append("❌ Contains === markers")
    if '**Speaker' in episode.script:
        issues.append("❌ Contains markdown **Speaker")
    
    # Count lines that don't start with "Speaker X:"
    lines = [l.strip() for l in episode.script.split('\n') if l.strip()]
    non_speaker_lines = [l for l in lines if not l.startswith('Speaker ')]
    
    if non_speaker_lines:
        print(f"\n⚠️  Found {len(non_speaker_lines)} non-Speaker lines:")
        for line in non_speaker_lines[:10]:
            print(f"   - {line[:100]}")
    
    if issues:
        print(f"\n❌ Issues found:")
        for issue in issues:
            print(f"   {issue}")
    else:
        print(f"\n✅ No obvious issues found!")
        
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()

