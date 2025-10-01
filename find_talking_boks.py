"""Find Talking Boks group and ready collections."""
import sys
import os
from uuid import UUID

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shared.database import SessionLocal
from shared.models import PodcastGroup, Collection

db = SessionLocal()

try:
    # Find Talking Boks group
    groups = db.query(PodcastGroup).all()
    
    print("="*70)
    print("📻 AVAILABLE PODCAST GROUPS")
    print("="*70)
    for group in groups:
        print(f"\n{group.name}")
        print(f"  ID: {group.id}")
        print(f"  Category: {group.category}")
        print(f"  Schedule: {group.schedule}")
    
    talking_boks = db.query(PodcastGroup).filter(
        PodcastGroup.name.ilike('%talking%boks%')
    ).first()
    
    if not talking_boks:
        print("\n❌ Talking Boks group not found!")
        print("\nSearching for similar names...")
        for group in groups:
            if 'bok' in group.name.lower() or 'talk' in group.name.lower():
                print(f"  Found: {group.name}")
    else:
        print("\n" + "="*70)
        print("✅ FOUND TALKING BOKS GROUP")
        print("="*70)
        print(f"Name: {talking_boks.name}")
        print(f"ID: {talking_boks.id}")
        print(f"Category: {talking_boks.category}")
        print(f"Current collections: {len(talking_boks.collections)}")
    
    # Find ready collections
    print("\n" + "="*70)
    print("📚 READY COLLECTIONS WITH ARTICLES")
    print("="*70)
    
    ready_collections = db.query(Collection).filter(
        Collection.status == 'ready'
    ).all()
    
    collections_with_articles = []
    for col in ready_collections:
        article_count = len(col.articles)
        if article_count > 0:
            collections_with_articles.append((col, article_count))
    
    # Sort by article count descending
    collections_with_articles.sort(key=lambda x: x[1], reverse=True)
    
    if not collections_with_articles:
        print("❌ No ready collections with articles found!")
    else:
        print(f"\nFound {len(collections_with_articles)} ready collections:\n")
        for col, count in collections_with_articles:
            groups_str = ', '.join([g.name for g in col.podcast_groups]) if col.podcast_groups else "Unassigned"
            print(f"📦 {col.name}")
            print(f"   ID: {col.id}")
            print(f"   Articles: {count}")
            print(f"   Groups: {groups_str}")
            print()
        
        # Show the best candidate
        best_col, best_count = collections_with_articles[0]
        print("="*70)
        print("🎯 RECOMMENDED COLLECTION")
        print("="*70)
        print(f"Name: {best_col.name}")
        print(f"ID: {best_col.id}")
        print(f"Articles: {best_count}")
        print(f"Current groups: {[g.name for g in best_col.podcast_groups]}")
        
        if talking_boks:
            print("\n" + "="*70)
            print("📋 ASSIGNMENT PLAN")
            print("="*70)
            print(f"✅ Assign: {best_col.name}")
            print(f"✅ To: {talking_boks.name}")
            print(f"✅ Articles: {best_count}")
    
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()

