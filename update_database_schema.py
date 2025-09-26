#!/usr/bin/env python3
"""
Database schema update script to add missing reviewer enhancement columns.
"""
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Database connection
DATABASE_URL = "postgresql://podcast_user:podcast_pass@localhost:5432/podcast_ai"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def update_database_schema():
    """Add missing columns to the articles table."""
    db = SessionLocal()
    
    try:
        # Check if columns already exist
        result = db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'articles' 
            AND column_name IN ('fingerprint', 'reviewer_type', 'review_tags', 'review_summary', 'confidence', 'processed_at', 'review_metadata')
        """))
        existing_columns = [row[0] for row in result.fetchall()]
        
        print(f"Existing reviewer columns: {existing_columns}")
        
        # Add missing columns
        columns_to_add = [
            ("fingerprint", "VARCHAR(128)"),
            ("reviewer_type", "VARCHAR(10)"),
            ("review_tags", "TEXT[]"),
            ("review_summary", "TEXT"),
            ("confidence", "FLOAT"),
            ("processed_at", "TIMESTAMP WITH TIME ZONE"),
            ("review_metadata", "JSONB")
        ]
        
        for column_name, column_type in columns_to_add:
            if column_name not in existing_columns:
                print(f"Adding column: {column_name} ({column_type})")
                db.execute(text(f"ALTER TABLE articles ADD COLUMN {column_name} {column_type}"))
            else:
                print(f"Column {column_name} already exists, skipping")
        
        # Check if collection_id column exists in articles table
        result = db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'articles' 
            AND column_name = 'collection_id'
        """))
        
        if not result.fetchone():
            print("Adding column: collection_id (UUID)")
            db.execute(text("ALTER TABLE articles ADD COLUMN collection_id UUID REFERENCES collections(id)"))
        else:
            print("Column collection_id already exists, skipping")
        
        # Check if collections table exists
        result = db.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name = 'collections'
        """))
        
        if not result.fetchone():
            print("Creating collections table...")
            db.execute(text("""
                CREATE TABLE collections (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    group_id UUID REFERENCES podcast_groups(id),
                    status VARCHAR(20) DEFAULT 'processing',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE
                )
            """))
        else:
            print("Collections table already exists, skipping")
        
        db.commit()
        print("Database schema update completed successfully!")
        
        # Verify the changes
        print("\nVerifying articles table structure:")
        result = db.execute(text("\\d articles"))
        print("Articles table updated successfully!")
        
    except Exception as e:
        print(f"Error updating database schema: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    update_database_schema()
