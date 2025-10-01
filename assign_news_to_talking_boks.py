"""Assign News collection to Talking Boks and generate podcast."""
import sys
import os
from uuid import UUID

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shared.database import SessionLocal
from shared.models import Collection, PodcastGroup

db = SessionLocal()

try:
    collection_id = UUID("37f99f01-ef5c-4807-af90-63fa90794097")
    group_id = UUID("fb58e9e8-d52b-497b-b6a0-0b97178ff233")
    
    collection = db.query(Collection).filter(Collection.id == collection_id).first()
    group = db.query(PodcastGroup).filter(PodcastGroup.id == group_id).first()
    
    if not collection:
        print(f"❌ Collection not found!")
        sys.exit(1)
    
    if not group:
        print(f"❌ Group not found!")
        sys.exit(1)
    
    print("="*70)
    print("📦 ASSIGNING COLLECTION TO TALKING BOKS")
    print("="*70)
    print(f"Collection: {collection.name} ({len(collection.articles)} articles)")
    print(f"Group: {group.name}")
    print()
    
    # Clear any old building collections from this group
    print("Cleaning up old collections...")
    for old_col in list(group.collections):
        if old_col.status in ["building", "expired"] and len(old_col.articles) == 0:
            group.collections.remove(old_col)
            print(f"  Removed: {old_col.name} ({old_col.status})")
    
    # Add the news collection (can be shared across groups)
    if collection not in group.collections:
        group.collections.append(collection)
        print(f"\n✅ Assigned {collection.name} to {group.name}")
    else:
        print(f"\n✅ {collection.name} already assigned to {group.name}")
    
    db.commit()
    
    print("\n" + "="*70)
    print("✅ ASSIGNMENT COMPLETE!")
    print("="*70)
    print(f"Group: {group.name}")
    print(f"Collection: {collection.name}")
    print(f"Articles: {len(collection.articles)}")
    print(f"Status: {collection.status}")
    print()
    print("📊 Collection is now shared between:")
    for g in collection.podcast_groups:
        print(f"  - {g.name}")
    
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    db.rollback()
finally:
    db.close()

