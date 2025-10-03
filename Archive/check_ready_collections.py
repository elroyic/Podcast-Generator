import httpx
import json

# Check for ready collections
response = httpx.get("http://localhost:8014/collections")
collections = response.json()

ready_collections = [c for c in collections if c.get("status") == "ready"]

print(f"Found {len(ready_collections)} ready collection(s):\n")
for c in ready_collections:
    print(f"  ID: {c.get('id')}")
    print(f"  Name: {c.get('name')}")
    print(f"  Articles: {len(c.get('items', []))}")
    print(f"  Groups: {c.get('group_ids', [])}")
    print()

if ready_collections:
    print(f"Using first ready collection: {ready_collections[0].get('id')}")
else:
    print("No ready collections found - will create a new one automatically.")


