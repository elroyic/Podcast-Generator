"""Fix the empty collection issue by updating the database directly."""
import sys
import os
from uuid import UUID

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shared.database import SessionLocal
from shared.models import Collection, PodcastGroup, collection_group_assignment
from sqlalchemy import select

def main():
    db = SessionLocal()
    
    try:
        empty_collection_id = UUID("388d2882-c037-4ad0-a542-300e04992105")
        ready_collection_id = UUID("0869ad90-e824-423e-8d8d-8076802fd910")
        group_id = UUID("9a056646-586b-4d87-a75b-6dea46e6a768")
        
        print("🔧 FIXING COLLECTION DATABASE ISSUE")
        print("=" * 70)
        
        # Step 1: Get the empty collection and mark it as expired
        print("\n1. Marking empty collection as expired...")
        empty_collection = db.query(Collection).filter(Collection.id == empty_collection_id).first()
        
        if empty_collection:
            print(f"   Found: {empty_collection.name}")
            print(f"   Status: {empty_collection.status}")
            print(f"   Articles: {len(empty_collection.articles)}")
            
            empty_collection.status = "expired"
            db.commit()
            print("   ✅ Marked as expired")
        else:
            print("   ⚠️  Empty collection not found in database")
        
        # Step 2: Get the ready collection
        print("\n2. Checking ready collection...")
        ready_collection = db.query(Collection).filter(Collection.id == ready_collection_id).first()
        
        if ready_collection:
            print(f"   Found: {ready_collection.name}")
            print(f"   Status: {ready_collection.status}")
            print(f"   Articles: {len(ready_collection.articles)}")
        else:
            print("   ❌ Ready collection not found in database!")
            return
        
        # Step 3: Get the group
        print("\n3. Checking group...")
        group = db.query(PodcastGroup).filter(PodcastGroup.id == group_id).first()
        
        if not group:
            print("   ❌ Group not found in database!")
            return
        
        print(f"   Found: {group.name}")
        print(f"   Current collections: {len(group.collections)}")
        
        # Step 4: Check if ready collection is already assigned to group
        print("\n4. Checking collection-group assignment...")
        is_assigned = ready_collection in group.collections
        
        if is_assigned:
            print("   ✅ Ready collection already assigned to group!")
        else:
            print("   ⚠️  Ready collection NOT assigned to group")
            print("   Assigning now...")
            
            # Add the relationship
            if ready_collection not in group.collections:
                group.collections.append(ready_collection)
            
            db.commit()
            print("   ✅ Ready collection assigned to group!")
        
        # Step 5: Remove empty collection from group if still assigned
        print("\n5. Removing empty collection from group...")
        if empty_collection and empty_collection in group.collections:
            group.collections.remove(empty_collection)
            db.commit()
            print("   ✅ Empty collection removed from group")
        else:
            print("   ✅ Empty collection already not in group")
        
        # Step 6: Verify final state
        print("\n6. Verifying final state...")
        db.refresh(group)
        
        print(f"   Group: {group.name}")
        print(f"   Total collections: {len(group.collections)}")
        
        for i, col in enumerate(group.collections, 1):
            print(f"   Collection {i}:")
            print(f"      ID: {col.id}")
            print(f"      Name: {col.name}")
            print(f"      Status: {col.status}")
            print(f"      Articles: {len(col.articles)}")
        
        print("\n" + "=" * 70)
        print("✅ DATABASE FIX COMPLETE!")
        print("=" * 70)
        print("\nNext steps:")
        print("1. Restart collections service: docker compose restart collections")
        print("2. Verify with: curl http://localhost:8014/collections/group/<group_id>/active")
        print("3. Test podcast generation!")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()


