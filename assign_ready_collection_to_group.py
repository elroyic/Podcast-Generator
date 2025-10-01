"""Assign a ready collection from the database to Spring Weather Podcast group."""
import sys
import os
from uuid import UUID

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shared.database import SessionLocal
from shared.models import Collection, PodcastGroup

def main():
    db = SessionLocal()
    
    try:
        # Use the Politics collection with 3 articles
        ready_collection_id = UUID("f2cfb16b-d7df-4303-a370-be2727c47039")  # Auto Collection: Politics
        group_id = UUID("9a056646-586b-4d87-a75b-6dea46e6a768")  # Spring Weather Podcast
        
        print("🔧 ASSIGNING READY COLLECTION TO GROUP")
        print("=" * 70)
        
        # Get the ready collection
        print("\n1. Loading ready collection...")
        ready_collection = db.query(Collection).filter(Collection.id == ready_collection_id).first()
        
        if not ready_collection:
            print("   ❌ Collection not found!")
            return
        
        print(f"   ✅ Found: {ready_collection.name}")
        print(f"      Status: {ready_collection.status}")
        print(f"      Articles: {len(ready_collection.articles)}")
        for article in ready_collection.articles[:3]:  # Show first 3
            print(f"         - {article.title[:60]}...")
        
        # Get the group
        print("\n2. Loading group...")
        group = db.query(PodcastGroup).filter(PodcastGroup.id == group_id).first()
        
        if not group:
            print("   ❌ Group not found!")
            return
        
        print(f"   ✅ Found: {group.name}")
        print(f"      Current collections: {len(group.collections)}")
        
        # Check current assignment
        print("\n3. Checking current assignment...")
        if ready_collection in group.collections:
            print("   ℹ️  Collection already assigned to group")
        else:
            print("   ➕ Adding collection to group...")
            group.collections.append(ready_collection)
            db.commit()
            print("   ✅ Collection assigned!")
        
        # Verify
        print("\n4. Verifying assignment...")
        db.refresh(group)
        
        print(f"   Group: {group.name}")
        print(f"   Total collections: {len(group.collections)}")
        
        for i, col in enumerate(group.collections, 1):
            status_icon = {
                'ready': '✅',
                'building': '🔨',
                'expired': '💀'
            }.get(col.status, '❓')
            
            print(f"\n   Collection {i}: {status_icon}")
            print(f"      ID: {col.id}")
            print(f"      Name: {col.name}")
            print(f"      Status: {col.status}")
            print(f"      Articles: {len(col.articles)}")
        
        print("\n" + "=" * 70)
        print("✅ ASSIGNMENT COMPLETE!")
        print("=" * 70)
        print("\nNext steps:")
        print("1. Restart collections service to clear cache:")
        print("   docker compose restart collections ai-overseer")
        print("\n2. Verify active collection:")
        print("   curl http://localhost:8014/collections/group/9a056646-586b-4d87-a75b-6dea46e6a768/active")
        print("\n3. Generate podcast - should now use the ready collection!")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()


