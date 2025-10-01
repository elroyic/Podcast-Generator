"""Check the generated episode details."""
import sys
import os
from uuid import UUID

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shared.database import SessionLocal
from shared.models import Episode

db = SessionLocal()

try:
    episode_id = UUID("01472396-a458-4ea9-a78d-105254f269e8")
    episode = db.query(Episode).filter(Episode.id == episode_id).first()
    
    if not episode:
        print("❌ Episode not found!")
        sys.exit(1)
    
    print("="*70)
    print("📻 GENERATED EPISODE DETAILS")
    print("="*70)
    print(f"Episode ID: {episode.id}")
    print(f"Status: {episode.status}")
    print()
    print("="*70)
    print("📝 SCRIPT PREVIEW (first 1000 characters)")
    print("="*70)
    script_preview = episode.script[:1000] if episode.script else "No script"
    print(script_preview)
    print()
    print("="*70)
    print("🎯 VALIDATION CHECKS")
    print("="*70)
    
    has_speakers = False
    has_think_tags = False
    speaker_count = 0
    
    if episode.script:
        has_speakers = "Speaker 1:" in episode.script or "Speaker 2:" in episode.script
        has_think_tags = "<think>" in episode.script
        
        # Count unique speakers
        for i in range(1, 5):
            if f"Speaker {i}:" in episode.script:
                speaker_count += 1
    
    print(f"✅ Has Speaker labels: {has_speakers}")
    print(f"✅ Speaker count: {speaker_count}")
    print(f"{'❌' if has_think_tags else '✅'} No <think> tags: {not has_think_tags}")
    print()
    print("="*70)
    print("🎉 SUMMARY")
    print("="*70)
    print("Dual Ollama Setup Performance:")
    print("  🎮 GPU Ollama: Writer (Qwen3) - Script generation")
    print("  💻 CPU Ollama: Editor (Qwen2-1.5b) - Script review")
    print("  🎮 GPU VibeVoice: Multi-speaker audio generation")
    print()
    print(f"Result: {'✅ SUCCESS!' if has_speakers and not has_think_tags else '⚠️ NEEDS REVIEW'}")
    print("="*70)
    
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()

