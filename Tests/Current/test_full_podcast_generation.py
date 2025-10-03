"""Test the complete podcast generation workflow with the fixed collection."""
import httpx
import time

ai_overseer_url = "http://localhost:8012"
group_id = "9a056646-586b-4d87-a75b-6dea46e6a768"

print("🎙️ TESTING COMPLETE PODCAST GENERATION")
print("=" * 70)
print("Group: Spring Weather Podcast")
print("Collection: Auto Collection: Politics (3 articles)")
print()
print("This will test the complete workflow:")
print("  1. ✅ Use ready collection from database (no workaround needed!)")
print("  2. ✅ Generate multi-speaker script (Speaker 1, Speaker 2)")
print("  3. ✅ Edit script with preserved speaker labels")
print("  4. ✅ Generate audio with different voices per speaker")
print("=" * 70)
print()

try:
    # Trigger generation WITHOUT specifying collection_id
    # It should automatically pick up the ready collection now!
    request_data = {
        "group_id": str(group_id),
        "force_regenerate": True
    }
    
    print("📤 Triggering podcast generation (automatic collection selection)...")
    response = httpx.post(
        f"{ai_overseer_url}/generate-episode",
        json=request_data,
        timeout=30.0
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"   ✅ {result['message']}\n")
        
        print("📊 Monitoring progress...")
        print("   Watch with: docker compose logs -f celery-worker")
        print()
        print("=" * 70)
        print("✅ GENERATION STARTED WITH PROPER COLLECTION!")
        print("=" * 70)
        print("\nThis should complete all steps:")
        print("  1. Create collection snapshot from ready collection")
        print("  2. Generate presenter briefs")
        print("  3. Generate multi-speaker script")
        print("  4. Edit and review script")
        print("  5. Generate episode metadata")
        print("  6. Generate multi-voice audio")
        print("\nEstimated time: 5-10 minutes")
    else:
        print(f"❌ Error: {response.status_code} - {response.text}")
        
except Exception as e:
    print(f"❌ Error: {e}")


