"""List all collections in the database."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shared.database import SessionLocal
from shared.models import Collection

def main():
    db = SessionLocal()
    
    try:
        print("📊 ALL COLLECTIONS IN DATABASE")
        print("=" * 80)
        
        collections = db.query(Collection).all()
        
        print(f"\nTotal collections: {len(collections)}\n")
        
        ready_collections = []
        
        for col in collections:
            status_icon = {
                'ready': '✅',
                'building': '🔨',
                'snapshot': '📸',
                'used': '✓',
                'expired': '💀'
            }.get(col.status, '❓')
            
            print(f"{status_icon} {col.status.upper()}")
            print(f"   ID: {col.id}")
            print(f"   Name: {col.name}")
            print(f"   Articles: {len(col.articles)}")
            print(f"   Groups: {len(col.podcast_groups)}")
            if col.podcast_groups:
                for group in col.podcast_groups:
                    print(f"      - {group.name}")
            print()
            
            if col.status == 'ready' and len(col.articles) > 0:
                ready_collections.append(col)
        
        print("=" * 80)
        print(f"\n✅ READY COLLECTIONS WITH ARTICLES: {len(ready_collections)}")
        
        if ready_collections:
            print("\nReady collections that can be used:")
            for col in ready_collections:
                print(f"   • {col.name}")
                print(f"     ID: {col.id}")
                print(f"     Articles: {len(col.articles)}")
                print(f"     Groups: {[g.name for g in col.podcast_groups]}")
                print()
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()


