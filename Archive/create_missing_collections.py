"""
Create collections for podcast groups that have feeds but no collections.
This fixes the issue where articles accumulate without being organized into collections.
"""
import sys
sys.path.append('shared')

from shared.database import get_db_session
from shared.models import PodcastGroup, Collection, Article, NewsFeed
from sqlalchemy import and_, func
from uuid import uuid4

def create_missing_collections():
    """Find groups with feeds but no collections and create collections for them."""
    db = get_db_session()
    
    try:
        print("=" * 70)
        print("Creating Missing Collections for Podcast Groups")
        print("=" * 70)
        print()
        
        # Find all active groups
        groups = db.query(PodcastGroup).filter(
            PodcastGroup.status == "active"
        ).all()
        
        created_count = 0
        
        for group in groups:
            # Check if group has any collections
            existing_collections = db.query(Collection).join(
                Collection.podcast_groups
            ).filter(
                PodcastGroup.id == group.id
            ).count()
            
            # Check if group has feeds
            feed_count = len(group.news_feeds)
            
            # Check if there are articles from this group's feeds
            article_count = 0
            if feed_count > 0:
                article_count = db.query(Article).filter(
                    Article.feed_id.in_([f.id for f in group.news_feeds])
                ).count()
            
            print(f"\nGroup: {group.name}")
            print(f"  Feeds: {feed_count}")
            print(f"  Articles: {article_count}")
            print(f"  Collections: {existing_collections}")
            
            # If group has feeds but no collection, create one
            if feed_count > 0 and existing_collections == 0:
                print(f"  ⚠️  Creating missing collection...")
                
                # Create building collection
                collection = Collection(
                    name=f"{group.name} Collection",
                    description=f"Active collection for {group.name}",
                    status="building"
                )
                db.add(collection)
                db.flush()
                
                # Assign to group
                collection.podcast_groups = [group]
                
                # Assign unassigned articles to this collection
                if article_count > 0:
                    # Get articles from this group's feeds that don't have a collection
                    unassigned_articles = db.query(Article).filter(
                        and_(
                            Article.feed_id.in_([f.id for f in group.news_feeds]),
                            Article.collection_id == None
                        )
                    ).all()
                    
                    assigned_count = 0
                    for article in unassigned_articles:
                        article.collection_id = collection.id
                        assigned_count += 1
                    
                    print(f"  ✅ Created collection: {collection.name}")
                    print(f"  ✅ Assigned {assigned_count} articles to collection")
                    
                    # Check if ready
                    if assigned_count >= 3:
                        collection.status = "ready"
                        print(f"  ✅ Collection marked as READY (has {assigned_count} articles)")
                else:
                    print(f"  ✅ Created collection: {collection.name}")
                    print(f"  ℹ️  No articles to assign yet")
                
                db.commit()
                created_count += 1
            elif existing_collections == 0:
                print(f"  ℹ️  No feeds assigned, skipping")
            else:
                print(f"  ✅ Already has {existing_collections} collection(s)")
        
        print()
        print("=" * 70)
        print(f"Summary: Created {created_count} new collection(s)")
        print("=" * 70)
        print()
        
        # Show final stats
        print("Final Collection Stats:")
        print()
        
        status_counts = db.query(
            Collection.status,
            func.count(Collection.id).label('count')
        ).group_by(Collection.status).all()
        
        for status, count in status_counts:
            print(f"  {status}: {count}")
        
        print()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    create_missing_collections()

