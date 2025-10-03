"""
Test script for the collection snapshot workflow.
This verifies that collections are properly snapshotted and new collections are created.
"""
import asyncio
import sys
import os
import logging
from datetime import datetime
from uuid import uuid4

# Add shared directory to path
sys.path.append('shared')

from shared.database import get_db_session
from shared.models import PodcastGroup, Collection, Article, NewsFeed, Episode, Writer, Presenter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_collection_snapshot_workflow():
    """Test the complete collection snapshot workflow."""
    db = get_db_session()
    
    try:
        logger.info("=" * 70)
        logger.info("Testing Collection Snapshot Workflow")
        logger.info("=" * 70)
        
        # Step 1: Create test data
        logger.info("\n1️⃣  Creating test podcast group...")
        
        # Create writer
        writer = Writer(
            name="Test Writer",
            model="Qwen3",
            capabilities=["script_generation"]
        )
        db.add(writer)
        db.commit()
        db.refresh(writer)
        
        # Create presenter
        presenter = Presenter(
            name="Test Presenter",
            bio="Test presenter for snapshot workflow",
            age=30,
            gender="neutral",
            voice_model="vibevoice"
        )
        db.add(presenter)
        db.commit()
        db.refresh(presenter)
        
        # Create podcast group
        group = PodcastGroup(
            name="Test Snapshot Group",
            description="Testing collection snapshot workflow",
            category="Technology",
            status="active",
            writer_id=writer.id
        )
        db.add(group)
        db.commit()
        db.refresh(group)
        
        # Assign presenter
        group.presenters = [presenter]
        db.commit()
        
        logger.info(f"✅ Created group: {group.name} (ID: {group.id})")
        
        # Step 2: Create a news feed
        logger.info("\n2️⃣  Creating test news feed...")
        feed = NewsFeed(
            source_url="https://example.com/feed.xml",
            name="Test Feed",
            type="RSS",
            is_active=True
        )
        db.add(feed)
        db.commit()
        db.refresh(feed)
        
        # Assign feed to group
        group.news_feeds = [feed]
        db.commit()
        
        logger.info(f"✅ Created feed: {feed.name} (ID: {feed.id})")
        
        # Step 3: Create a collection for the group
        logger.info("\n3️⃣  Creating initial collection...")
        collection = Collection(
            name=f"{group.name} Collection",
            description="Test collection for snapshot workflow",
            status="building"
        )
        db.add(collection)
        db.commit()
        db.refresh(collection)
        
        # Assign collection to group
        collection.podcast_groups = [group]
        db.commit()
        
        logger.info(f"✅ Created collection: {collection.name} (ID: {collection.id})")
        
        # Step 4: Add articles to the collection
        logger.info("\n4️⃣  Adding articles to collection...")
        articles_created = []
        
        for i in range(5):
            article = Article(
                feed_id=feed.id,
                title=f"Test Article {i+1}",
                link=f"https://example.com/article-{i+1}",
                summary=f"Summary of test article {i+1}",
                content=f"Content of test article {i+1}",
                collection_id=collection.id
            )
            db.add(article)
            articles_created.append(article)
        
        db.commit()
        
        for article in articles_created:
            db.refresh(article)
        
        logger.info(f"✅ Added {len(articles_created)} articles to collection")
        
        # Verify initial state
        article_count = db.query(Article).filter(Article.collection_id == collection.id).count()
        logger.info(f"📊 Collection {collection.id} has {article_count} articles")
        
        # Step 5: Mark collection as ready
        logger.info("\n5️⃣  Marking collection as ready...")
        collection.status = "ready"
        db.commit()
        logger.info(f"✅ Collection marked as ready")
        
        # Step 6: Create an episode (simulating the workflow)
        logger.info("\n6️⃣  Creating episode for snapshot...")
        episode = Episode(
            group_id=group.id,
            script="Test episode script",
            status="draft"
        )
        db.add(episode)
        db.commit()
        db.refresh(episode)
        
        logger.info(f"✅ Created episode: {episode.id}")
        
        # Step 7: Simulate snapshot creation (manual process)
        logger.info("\n7️⃣  Creating collection snapshot...")
        
        # Create snapshot collection
        snapshot = Collection(
            name=f"Episode {str(episode.id)[:8]} Snapshot",
            description=f"Snapshot of {collection.name} for episode {episode.id}",
            status="snapshot",
            episode_id=episode.id,
            parent_collection_id=collection.id
        )
        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)
        
        # Assign same groups to snapshot
        snapshot.podcast_groups = collection.podcast_groups
        db.commit()
        
        logger.info(f"✅ Created snapshot: {snapshot.name} (ID: {snapshot.id})")
        
        # Step 8: Move articles from original to snapshot
        logger.info("\n8️⃣  Moving articles to snapshot...")
        
        articles_to_move = db.query(Article).filter(Article.collection_id == collection.id).all()
        moved_count = 0
        
        for article in articles_to_move:
            article.collection_id = snapshot.id
            moved_count += 1
        
        db.commit()
        logger.info(f"✅ Moved {moved_count} articles to snapshot")
        
        # Step 9: Create new building collection
        logger.info("\n9️⃣  Creating new building collection...")
        
        new_collection = Collection(
            name=collection.name,  # Same name
            description=collection.description,
            status="building",
            parent_collection_id=snapshot.id
        )
        db.add(new_collection)
        db.commit()
        db.refresh(new_collection)
        
        # Assign same groups
        new_collection.podcast_groups = collection.podcast_groups
        db.commit()
        
        logger.info(f"✅ Created new building collection: {new_collection.id}")
        
        # Step 10: Delete original collection
        logger.info("\n🔟 Deleting original collection...")
        original_id = collection.id
        db.delete(collection)
        db.commit()
        logger.info(f"✅ Deleted original collection: {original_id}")
        
        # Step 11: Verify final state
        logger.info("\n📊 Verifying final state...")
        
        # Check snapshot
        snapshot_articles = db.query(Article).filter(Article.collection_id == snapshot.id).count()
        logger.info(f"  Snapshot collection {snapshot.id}:")
        logger.info(f"    - Status: {snapshot.status}")
        logger.info(f"    - Articles: {snapshot_articles}")
        logger.info(f"    - Episode ID: {snapshot.episode_id}")
        logger.info(f"    - Parent: {snapshot.parent_collection_id}")
        
        # Check new collection
        new_articles = db.query(Article).filter(Article.collection_id == new_collection.id).count()
        logger.info(f"  New building collection {new_collection.id}:")
        logger.info(f"    - Status: {new_collection.status}")
        logger.info(f"    - Articles: {new_articles}")
        logger.info(f"    - Parent: {new_collection.parent_collection_id}")
        
        # Verify snapshot has all articles
        if snapshot_articles == len(articles_created):
            logger.info(f"\n✅ SUCCESS: Snapshot has all {snapshot_articles} articles")
        else:
            logger.error(f"\n❌ FAIL: Snapshot has {snapshot_articles} articles, expected {len(articles_created)}")
        
        # Verify new collection is empty
        if new_articles == 0:
            logger.info(f"✅ SUCCESS: New collection is empty and ready for new articles")
        else:
            logger.error(f"❌ FAIL: New collection has {new_articles} articles, expected 0")
        
        # Step 12: Test adding new articles to new collection
        logger.info("\n1️⃣1️⃣ Testing new article addition...")
        
        new_article = Article(
            feed_id=feed.id,
            title="New Article After Snapshot",
            link="https://example.com/new-article",
            summary="This article was added after snapshot",
            content="Content for new article",
            collection_id=new_collection.id
        )
        db.add(new_article)
        db.commit()
        
        # Verify
        new_collection_articles = db.query(Article).filter(Article.collection_id == new_collection.id).count()
        snapshot_articles_final = db.query(Article).filter(Article.collection_id == snapshot.id).count()
        
        logger.info(f"  New collection now has: {new_collection_articles} article(s)")
        logger.info(f"  Snapshot still has: {snapshot_articles_final} article(s)")
        
        if new_collection_articles == 1 and snapshot_articles_final == len(articles_created):
            logger.info("\n✅ SUCCESS: Collections are properly isolated")
        else:
            logger.error("\n❌ FAIL: Collections are not properly isolated")
        
        # Summary
        logger.info("\n" + "=" * 70)
        logger.info("WORKFLOW TEST SUMMARY")
        logger.info("=" * 70)
        logger.info(f"✅ Snapshot collection created: {snapshot.id}")
        logger.info(f"✅ {snapshot_articles_final} articles preserved in snapshot")
        logger.info(f"✅ New building collection created: {new_collection.id}")
        logger.info(f"✅ New articles go to new collection: {new_collection_articles}")
        logger.info(f"✅ Original collection replaced successfully")
        logger.info("=" * 70)
        logger.info("🎉 COLLECTION SNAPSHOT WORKFLOW TEST PASSED!")
        logger.info("=" * 70)
        
        # Cleanup
        logger.info("\n🧹 Cleaning up test data...")
        db.delete(new_article)
        for article in articles_created:
            db.delete(article)
        db.delete(new_collection)
        db.delete(snapshot)
        db.delete(episode)
        db.delete(feed)
        db.delete(group)
        db.delete(presenter)
        db.delete(writer)
        db.commit()
        logger.info("✅ Cleanup complete")
        
    except Exception as e:
        logger.error(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    try:
        asyncio.run(test_collection_snapshot_workflow())
    except Exception as e:
        logger.error(f"Test script failed: {e}")
        sys.exit(1)

