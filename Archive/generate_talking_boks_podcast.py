"""Generate podcast for Talking Boks group."""
import requests
import json

# Talking Boks group ID
GROUP_ID = "fb58e9e8-d52b-497b-b6a0-0b97178ff233"

print("="*70)
print("🎙️ GENERATING PODCAST FOR TALKING BOKS")
print("="*70)
print()
print("Configuration:")
print(f"  📻 Group: Talking Boks")
print(f"  📦 Collection: Auto Collection: News (114 articles)")
print(f"  🎯 Writer: gpt-oss:20b (high-quality scripts)")
print(f"  💻 Editor: qwen2:1.5b (CPU)")
print(f"  🎤 TTS: VibeVoice-1.5B (GPU)")
print()
print("="*70)

# Generate episode
print("\n📤 Triggering podcast generation...")

try:
    response = requests.post(
        "http://localhost:8012/generate-episode",
        json={
            "group_id": GROUP_ID,
            "force_regenerate": False
        },
        timeout=10
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"   ✅ Episode generation queued!")
        print(f"   Task ID: {result.get('message', 'N/A').split('task ID: ')[-1]}")
        print()
        print("="*70)
        print("✅ GENERATION STARTED!")
        print("="*70)
        print()
        print("This will:")
        print("  1. Create snapshot from 114-article collection")
        print("  2. Generate high-quality script with gpt-oss:20b")
        print("  3. Edit and polish with qwen2:1.5b")
        print("  4. Generate metadata")
        print("  5. Create multi-voice audio with VibeVoice")
        print()
        print("Expected time: 5-10 minutes")
        print()
        print("📊 Monitor progress:")
        print("   docker compose logs -f celery-worker")
        print()
        print("📁 Check episode:")
        print("   http://localhost:8095/podcast/episodes")
        print("="*70)
    else:
        print(f"   ❌ Failed: {response.status_code}")
        print(f"   Error: {response.text}")

except Exception as e:
    print(f"   ❌ Error: {e}")
    print()
    print("Make sure services are running:")
    print("   docker compose ps")

