"""Delete the empty building collection so the ready collection can be used."""
import httpx

collections_url = "http://localhost:8014"
empty_collection_id = "388d2882-c037-4ad0-a542-300e04992105"
ready_collection_id = "0869ad90-e824-423e-8d8d-8076802fd910"  # Government Shutdown collection
group_id = "9a056646-586b-4d87-a75b-6dea46e6a768"

print("🔧 FIXING EMPTY COLLECTION ISSUE")
print("=" * 70)
print(f"Empty Collection: {empty_collection_id}")
print(f"Ready Collection: {ready_collection_id}")
print()

# Step 1: Mark the empty collection as "expired" instead of "building"
print("1. Marking empty collection as expired...")
try:
    response = httpx.put(
        f"{collections_url}/collections/{empty_collection_id}",
        json={"status": "expired"},
        timeout=10.0
    )
    if response.status_code == 200:
        print("   ✅ Empty collection marked as expired")
    else:
        print(f"   ⚠️  Could not update: {response.status_code} - {response.text}")
except Exception as e:
    print(f"   ⚠️  Error: {e}")

# Step 2: Assign the ready collection to the group
print("\n2. Assigning ready collection to group...")
try:
    response = httpx.post(
        f"{collections_url}/collections/{ready_collection_id}/assign-group",
        json={"group_id": group_id},
        timeout=10.0
    )
    if response.status_code == 200:
        print("   ✅ Ready collection assigned to group!")
    else:
        print(f"   ⚠️  Could not assign: {response.status_code} - {response.text}")
except Exception as e:
    print(f"   ⚠️  Error: {e}")

# Step 3: Verify the active collection
print("\n3. Verifying active collection...")
try:
    response = httpx.get(
        f"{collections_url}/collections/group/{group_id}/active",
        timeout=10.0
    )
    if response.status_code == 200:
        data = response.json()
        print(f"   Collection ID: {data.get('collection_id')}")
        print(f"   Name: {data.get('name')}")
        print(f"   Status: {data.get('status')}")
        print(f"   Articles: {len(data.get('items', []))}")
        
        if data.get('collection_id') == ready_collection_id:
            print("\n   ✅ SUCCESS! Ready collection is now active!")
        else:
            print(f"\n   ⚠️  Still using collection: {data.get('collection_id')}")
    else:
        print(f"   ❌ Error: {response.status_code}")
except Exception as e:
    print(f"   ❌ Error: {e}")

print("\n" + "=" * 70)
print("✅ Fix attempt complete!")
print("=" * 70)


