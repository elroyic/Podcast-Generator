"""Assign the AI News Podcast Collection to Spring Weather Podcast group."""
import sys
import os
from uuid import UUID

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shared.database import SessionLocal
from shared.models import Collection, PodcastGroup

def main():
    db = SessionLocal()
    
    try:
        # Use the AI News collection with 710 articles
        collection_id = UUID("f9982657-140c-4500-bb28-f0fbe30a4da9")
        group_id = UUID("9a056646-586b-4d87-a75b-6dea46e6a768")
        
        print("🔧 ASSIGNING AI NEWS COLLECTION")
        print("=" * 70)
        
        collection = db.query(Collection).filter(Collection.id == collection_id).first()
        group = db.query(PodcastGroup).filter(PodcastGroup.id == group_id).first()
        
        if not collection or not group:
            print("❌ Collection or group not found!")
            return
        
        print(f"Collection: {collection.name}")
        print(f"Articles: {len(collection.articles)}")
        print(f"Group: {group.name}")
        
        # Add to group if not already
        if collection not in group.collections:
            group.collections.append(collection)
            db.commit()
            print("✅ Collection assigned!")
        else:
            print("✅ Already assigned!")
        
        # Remove the empty building collection
        empty_id = UUID("19bf73ff-7c78-426c-a344-5f97e0962b9d")
        empty = db.query(Collection).filter(Collection.id == empty_id).first()
        if empty and empty in group.collections:
            empty.status = "expired"
            db.commit()
            print("✅ Expired empty collection!")
        
        print("\n" + "=" * 70)
        print("✅ READY! Restart collections service and try again.")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()


