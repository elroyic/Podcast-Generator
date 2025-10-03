"""Assign the Tags collection (4 articles) to Spring Weather Podcast."""
import sys
import os
from uuid import UUID

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shared.database import SessionLocal
from shared.models import Collection, PodcastGroup

db = SessionLocal()

try:
    collection_id = UUID("8c9ecf09-93f5-45ff-9b8a-bf61ca63535c")
    group_id = UUID("9a056646-586b-4d87-a75b-6dea46e6a768")
    
    collection = db.query(Collection).filter(Collection.id == collection_id).first()
    group = db.query(PodcastGroup).filter(PodcastGroup.id == group_id).first()
    
    print(f"Collection: {collection.name} ({len(collection.articles)} articles)")
    print(f"Group: {group.name}")
    
    # Clear ALL old collections from this group first
    print("\nRemoving old collections from group...")
    for old_col in list(group.collections):
        if old_col.status in ["building", "expired"] and len(old_col.articles) == 0:
            group.collections.remove(old_col)
            print(f"  Removed: {old_col.name} ({old_col.status})")
    
    # Add the new ready collection
    if collection not in group.collections:
        group.collections.append(collection)
        print(f"\n✅ Assigned {collection.name} to {group.name}")
    
    db.commit()
    print("\n" + "="*60)
    print("✅ DONE! Restart collections and try again.")
    
except Exception as e:
    print(f"❌ ERROR: {e}")
    db.rollback()
finally:
    db.close()


