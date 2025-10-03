import httpx

response = httpx.get("http://localhost:8014/collections/group/9a056646-586b-4d87-a75b-6dea46e6a768/active")
data = response.json()

print(f"Collection: {data.get('name')}")
print(f"ID: {data.get('collection_id')}")
print(f"Status: {data.get('status')}")
print(f"Articles: {len(data.get('items', []))}")


