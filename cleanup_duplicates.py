#!/usr/bin/env python3
"""
Cleanup script to remove duplicate podcast groups and keep only the most recent ones.
"""

import requests
import json
from collections import defaultdict
from datetime import datetime

def cleanup_duplicates():
    """Remove duplicate podcast groups, keeping only the most recent ones."""
    
    base_url = "http://localhost:8000"
    session = requests.Session()
    
    print("🧹 Starting cleanup of duplicate podcast groups...")
    
    # Get all podcast groups
    response = session.get(f"{base_url}/api/podcast-groups")
    if response.status_code != 200:
        print(f"❌ Failed to get podcast groups: {response.status_code}")
        return
    
    groups = response.json()
    print(f"📊 Found {len(groups)} total podcast groups")
    
    # Group by name to find duplicates
    groups_by_name = defaultdict(list)
    for group in groups:
        groups_by_name[group['name']].append(group)
    
    # Find duplicates and keep only the most recent
    groups_to_delete = []
    groups_to_keep = []
    
    for name, group_list in groups_by_name.items():
        if len(group_list) > 1:
            print(f"🔄 Found {len(group_list)} duplicates for '{name}'")
            
            # Sort by created_at (most recent first)
            group_list.sort(key=lambda x: x['created_at'], reverse=True)
            
            # Keep the most recent one
            keep_group = group_list[0]
            groups_to_keep.append(keep_group)
            
            # Mark the rest for deletion
            for group in group_list[1:]:
                groups_to_delete.append(group)
                print(f"  🗑️  Marking for deletion: {group['id']} (created: {group['created_at']})")
            
            print(f"  ✅ Keeping: {keep_group['id']} (created: {keep_group['created_at']})")
        else:
            # No duplicates, keep the single group
            groups_to_keep.append(group_list[0])
    
    print(f"\n📋 Cleanup Summary:")
    print(f"  - Total groups: {len(groups)}")
    print(f"  - Groups to keep: {len(groups_to_keep)}")
    print(f"  - Groups to delete: {len(groups_to_delete)}")
    
    if not groups_to_delete:
        print("✅ No duplicates found. Database is clean!")
        return
    
    # Delete duplicate groups
    deleted_count = 0
    for group in groups_to_delete:
        try:
            delete_response = session.delete(f"{base_url}/api/podcast-groups/{group['id']}")
            if delete_response.status_code == 200:
                deleted_count += 1
                print(f"✅ Deleted: {group['name']} ({group['id']})")
            else:
                print(f"❌ Failed to delete {group['name']}: {delete_response.status_code}")
        except Exception as e:
            print(f"❌ Error deleting {group['name']}: {e}")
    
    print(f"\n🎉 Cleanup completed!")
    print(f"  - Successfully deleted: {deleted_count} duplicate groups")
    print(f"  - Remaining groups: {len(groups) - deleted_count}")
    
    # Verify final state
    final_response = session.get(f"{base_url}/api/podcast-groups")
    if final_response.status_code == 200:
        final_groups = final_response.json()
        print(f"  - Final count: {len(final_groups)} groups")
        
        # Show remaining groups
        print(f"\n📋 Remaining Podcast Groups:")
        for group in final_groups:
            print(f"  - {group['name']} (ID: {group['id'][:8]}...)")

if __name__ == "__main__":
    cleanup_duplicates()
