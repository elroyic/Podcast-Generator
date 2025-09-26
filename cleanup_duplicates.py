#!/usr/bin/env python3
"""
Script to clean up duplicate presenters in the database.
"""
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from shared.models import Presenter

# Database connection
DATABASE_URL = "postgresql://podcast_user:podcast_pass@localhost:5432/podcast_ai"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def cleanup_duplicate_presenters():
    """Remove duplicate presenters, keeping only the first one of each name."""
    db = SessionLocal()
    
    try:
        # Get all presenters grouped by name
        presenters = db.query(Presenter).all()
        
        # Group by name
        name_groups = {}
        for presenter in presenters:
            if presenter.name not in name_groups:
                name_groups[presenter.name] = []
            name_groups[presenter.name].append(presenter)
        
        # Remove duplicates
        total_removed = 0
        for name, group in name_groups.items():
            if len(group) > 1:
                # Keep the first one, remove the rest
                keep_presenter = group[0]
                duplicates = group[1:]
                
                print(f"Found {len(duplicates)} duplicates for '{name}', keeping ID {keep_presenter.id}")
                
                for duplicate in duplicates:
                    print(f"  Removing duplicate ID {duplicate.id}")
                    db.delete(duplicate)
                    total_removed += 1
        
        db.commit()
        print(f"\nCleanup complete! Removed {total_removed} duplicate presenters.")
        
        # Show final counts
        final_presenters = db.query(Presenter).all()
        print(f"Total presenters remaining: {len(final_presenters)}")
        
        for name, group in name_groups.items():
            if len(group) > 1:
                remaining = db.query(Presenter).filter(Presenter.name == name).count()
                print(f"  {name}: {remaining} remaining")
        
    except Exception as e:
        print(f"Error during cleanup: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    cleanup_duplicate_presenters()