"""
Migration script to add episode_id and parent_collection_id to collections table.
Run this script to update the database schema for the collection snapshot feature.
"""
import sys
import os

# Add shared directory to path
sys.path.append('shared')

from shared.database import get_db_session, engine
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate_collections_table():
    """Add new fields to collections table for snapshot functionality."""
    db = get_db_session()
    
    try:
        logger.info("Starting collections table migration...")
        
        # Check if columns already exist
        check_episode_id = text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='collections' AND column_name='episode_id'
        """)
        
        check_parent = text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='collections' AND column_name='parent_collection_id'
        """)
        
        has_episode_id = db.execute(check_episode_id).fetchone() is not None
        has_parent = db.execute(check_parent).fetchone() is not None
        
        # Add episode_id column if it doesn't exist
        if not has_episode_id:
            logger.info("Adding episode_id column...")
            db.execute(text("""
                ALTER TABLE collections 
                ADD COLUMN episode_id UUID REFERENCES episodes(id)
            """))
            db.commit()
            logger.info("✅ Added episode_id column")
        else:
            logger.info("episode_id column already exists")
        
        # Add parent_collection_id column if it doesn't exist
        if not has_parent:
            logger.info("Adding parent_collection_id column...")
            db.execute(text("""
                ALTER TABLE collections 
                ADD COLUMN parent_collection_id UUID REFERENCES collections(id)
            """))
            db.commit()
            logger.info("✅ Added parent_collection_id column")
        else:
            logger.info("parent_collection_id column already exists")
        
        # Update status column comment to document new states
        logger.info("Updating status column documentation...")
        db.execute(text("""
            COMMENT ON COLUMN collections.status IS 
            'Collection status: building (actively collecting), ready (enough articles), snapshot (frozen for episode), used (episode generated), expired (too old)'
        """))
        db.commit()
        logger.info("✅ Updated status column documentation")
        
        logger.info("🎉 Migration completed successfully!")
        
        # Print summary
        result = db.execute(text("""
            SELECT 
                column_name, 
                data_type, 
                is_nullable
            FROM information_schema.columns 
            WHERE table_name='collections' 
            ORDER BY ordinal_position
        """))
        
        logger.info("\nCurrent collections table structure:")
        for row in result:
            logger.info(f"  - {row[0]}: {row[1]} ({'NULL' if row[2] == 'YES' else 'NOT NULL'})")
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    logger.info("=" * 70)
    logger.info("Collection Snapshot Schema Migration")
    logger.info("=" * 70)
    
    try:
        migrate_collections_table()
    except Exception as e:
        logger.error(f"Migration failed with error: {e}")
        sys.exit(1)
    
    logger.info("=" * 70)
    logger.info("Migration script completed")
    logger.info("=" * 70)

