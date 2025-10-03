#!/usr/bin/env python3
import sys
import os
sys.path.append('/app/shared')

from shared.database import get_db_session
from sqlalchemy import text

print("Running collection schema migration...")

db = get_db_session()
try:
    # Add episode_id column
    try:
        db.execute(text("""
            ALTER TABLE collections 
            ADD COLUMN IF NOT EXISTS episode_id UUID REFERENCES episodes(id)
        """))
        db.commit()
        print("✅ Added episode_id column")
    except Exception as e:
        print(f"ℹ️  episode_id column exists or error: {e}")
        db.rollback()
    
    # Add parent_collection_id column
    try:
        db.execute(text("""
            ALTER TABLE collections 
            ADD COLUMN IF NOT EXISTS parent_collection_id UUID REFERENCES collections(id)
        """))
        db.commit()
        print("✅ Added parent_collection_id column")
    except Exception as e:
        print(f"ℹ️  parent_collection_id column exists or error: {e}")
        db.rollback()
    
    print("🎉 Migration completed!")
    
finally:
    db.close()
