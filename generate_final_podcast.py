"""Generate the final multi-speaker podcast with the newly assigned collection."""
import httpx
import json

ai_overseer_url = "http://localhost:8012"
group_id = "9a056646-586b-4d87-a75b-6dea46e6a768"  # Spring Weather Podcast

print("🎙️ GENERATING FINAL MULTI-SPEAKER PODCAST")
print("=" * 70)
print(f"Group: Spring Weather Podcast")
print(f"Collection: Auto Collection: Government Shutdown (3 articles)")
print()
print("Features:")
print("  ✅ Multi-speaker dialogue (Speaker 1, Speaker 2, etc.)")
print("  ✅ Different voices per speaker (Carter, Maya, Frank, Alice)")
print("  ✅ Edited script with preserved speaker labels")
print("  ✅ Ready collection with actual news content")
print("=" * 70)
print()

request_data = {
    "group_id": str(group_id),
    "force_regenerate": True
}

print("📤 Triggering episode generation...")
response = httpx.post(
    f"{ai_overseer_url}/generate-episode",
    json=request_data,
    timeout=30.0
)

if response.status_code == 200:
    result = response.json()
    print(f"   ✅ {result['message']}\n")
    print("📊 Monitor with: docker compose logs -f celery-worker\n")
    print("=" * 70)
    print("🎉 Podcast generation started!")
    print("This will take 5-10 minutes to complete all steps:")
    print("  1. Create collection snapshot")
    print("  2. Generate multi-speaker script")
    print("  3. Edit/review the script")
    print("  4. Generate metadata")
    print("  5. Generate audio with multiple voices")
    print("=" * 70)
else:
    print(f"❌ Error: {response.status_code} - {response.text}")


