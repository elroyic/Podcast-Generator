"""Generate podcast for Talking Boks using existing snapshot."""
import requests
import json

# Talking Boks group ID
GROUP_ID = "fb58e9e8-d52b-497b-b6a0-0b97178ff233"

# Snapshot collection with 114 articles
COLLECTION_ID = "30450852-3170-4e7a-aa0f-c3603e31aa6b"

print("="*70)
print("🎙️ GENERATING PODCAST FOR TALKING BOKS (WITH SNAPSHOT)")
print("="*70)
print()
print("Configuration:")
print(f"  📻 Group: Talking Boks")
print(f"  📦 Collection: Episode 81affce7 Snapshot (114 articles)")
print(f"  🎯 Writer: Qwen3 (GPU)")
print(f"  💻 Editor: Qwen2-1.5b (CPU)")
print(f"  🎤 TTS: VibeVoice-1.5B (GPU)")
print(f"  ⏱️  Timeouts: 180 seconds")
print()
print("="*70)

# Generate episode
print("\n📤 Triggering podcast generation with specific collection...")

try:
    response = requests.post(
        "http://localhost:8012/generate-episode",
        json={
            "group_id": GROUP_ID,
            "collection_id": COLLECTION_ID,
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
        print("  1. Use existing snapshot (no snapshot creation needed)")
        print("  2. Generate script with Qwen3 (GPU, ~50s)")
        print("  3. Edit with Qwen2-1.5b (CPU, ~60s)")
        print("  4. Generate metadata (GPU, ~50s)")
        print("  5. Create multi-voice audio with VibeVoice (GPU, ~50s)")
        print()
        print("Expected time: 3-5 minutes")
        print()
        print("📊 Monitor progress:")
        print("   docker compose logs -f celery-worker")
        print()
        print("="*70)
    else:
        print(f"   ❌ Failed: {response.status_code}")
        print(f"   Error: {response.text}")

except Exception as e:
    print(f"   ❌ Error: {e}")
    print()
    print("Make sure services are running:")
    print("   docker compose ps")

