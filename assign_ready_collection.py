"""Find a ready collection and assign it to the group."""
import httpx
import json

group_id = "9a056646-586b-4d87-a75b-6dea46e6a768"
collections_url = "http://localhost:8014"

# Get all collections
print("🔍 Checking all collections...")
response = httpx.get(f"{collections_url}/collections")
all_collections = response.json()

print(f"Total collections: {len(all_collections)}\n")

# Find ready collections with articles
ready_collections = [
    c for c in all_collections 
    if c.get("status") == "ready" and len(c.get("items", [])) > 0
]

print(f"Found {len(ready_collections)} ready collections with articles:\n")
for c in ready_collections[:5]:  # Show first 5
    print(f"  ID: {c.get('collection_id')}")  # Fixed: use collection_id
    print(f"  Name: {c.get('name')}")
    print(f"  Articles: {len(c.get('items', []))}")
    print(f"  Status: {c.get('status')}")
    print()

if ready_collections:
    # Use the first ready collection
    collection_id = ready_collections[0].get('collection_id')  # Fixed: use collection_id
    print(f"✅ Assigning collection {collection_id} to group {group_id}...")
    
    # Assign to group
    response = httpx.post(
        f"{collections_url}/collections/{collection_id}/assign-group",
        json={"group_id": group_id}
    )
    
    if response.status_code == 200:
        print(f"✅ Successfully assigned!")
        print(f"\nReady to generate podcast with {len(ready_collections[0].get('items', []))} articles!")
    else:
        print(f"❌ Error: {response.status_code} - {response.text}")
else:
    print("❌ No ready collections found!")
    print("\n💡 The news-feed service might need to fetch fresh articles.")
    print("   Check: docker compose logs news-feed")

