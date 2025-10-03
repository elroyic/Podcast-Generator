# Collection Snapshot Workflow

## Problem Statement

Previously, collections would continue to grow indefinitely because:
1. Articles were added to collections marked as "building"
2. When ready, collections changed status to "ready" → "used"
3. Articles never left the collection
4. New articles kept being added to the same collection, making it too large for a single podcast

## Solution: Collection Snapshots

The new workflow implements a **checkpoint system** that:
- Creates a frozen snapshot when a collection is ready for an episode
- Names the snapshot with the Episode ID
- Moves all articles to the snapshot
- Creates a fresh collection for new articles
- Links the snapshot to the episode for tracking

## Architecture

### Database Schema Changes

**New fields added to `collections` table:**

```sql
-- Links snapshot to its episode
episode_id UUID REFERENCES episodes(id) NULL

-- Tracks collection lineage (snapshot → new collection)
parent_collection_id UUID REFERENCES collections(id) NULL
```

**New collection statuses:**
- `building` - Actively collecting articles
- `ready` - Has enough articles for a podcast
- `snapshot` - Frozen snapshot linked to an episode
- `used` - Episode has been generated (deprecated, use snapshot instead)
- `expired` - Too old to use

### Workflow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                 COLLECTION SNAPSHOT WORKFLOW                     │
└─────────────────────────────────────────────────────────────────┘

Step 1: Articles accumulate in building collection
┌──────────────────────┐
│ Building Collection  │
│ ID: abc-123          │
│ Status: building     │
│ Articles: [A1, A2,   │
│            A3, A4,   │
│            A5]       │
└──────────────────────┘

Step 2: Episode generation triggered
         ↓
┌──────────────────────┐
│ Create Episode       │
│ ID: xyz-789          │
└──────────────────────┘

Step 3: Snapshot created and articles moved
         ↓
┌──────────────────────┐     ┌──────────────────────┐
│ Snapshot Collection  │     │ New Building         │
│ ID: def-456          │     │ Collection           │
│ Status: snapshot     │     │ ID: ghi-999          │
│ Episode ID: xyz-789  │     │ Status: building     │
│ Parent: abc-123      │     │ Articles: []         │
│ Articles: [A1, A2,   │     │ Parent: def-456      │
│            A3, A4,   │     │                      │
│            A5]       │     │                      │
└──────────────────────┘     └──────────────────────┘
         ↓                            ↓
    Used for podcast          Collects new articles
    (frozen, preserved)        (active, growing)
```

## API Changes

### Collections Service

**New Endpoints:**

1. **Create Snapshot**
   ```http
   POST /collections/{collection_id}/snapshot?episode_id={episode_id}
   ```
   
   Response:
   ```json
   {
     "message": "Collection snapshot created successfully",
     "snapshot_id": "def-456",
     "original_collection_id": "abc-123",
     "episode_id": "xyz-789"
   }
   ```

2. **Get Active Collection for Group**
   ```http
   GET /collections/group/{group_id}/active
   ```
   
   Response: Returns the active building collection for the group, creates one if none exists.

### AI Overseer Changes

**Updated Episode Generation:**

The `generate_complete_episode` method now:

1. Gets the active building collection for the group
2. Creates an episode record (to get an ID)
3. Creates a snapshot of the collection linked to the episode
4. Moves all articles to the snapshot
5. Creates a new building collection for future articles
6. Uses the snapshot for script generation
7. New articles go to the new building collection

## Implementation Details

### Collection Manager Methods

**`create_collection_snapshot(collection_id, episode_id, db)`**
- Creates a frozen snapshot of a collection
- Moves articles from original to snapshot
- Creates new building collection with same settings
- Deletes original empty collection
- Updates in-memory cache
- Returns snapshot ID

**`get_active_collection_for_group(group_id, db)`**
- Finds or creates the active building collection for a group
- Ensures each group always has exactly one building collection
- Automatically creates collections when needed

**`_load_collection_into_memory(db_collection, db)`**
- Loads a collection from database into memory cache
- Converts articles to CollectionItems
- Used for synchronization

## Migration

### Running the Migration

```bash
python migrate_collections_schema.py
```

This adds:
- `episode_id` column to collections table
- `parent_collection_id` column to collections table
- Documentation for status values

### Backward Compatibility

✅ **Fully backward compatible**
- New columns are nullable
- Existing collections continue to work
- Old workflow still supported (manual collection selection)
- Automatic migration of existing collections to new format

## Testing

### Run the Test Suite

```bash
python test_collection_snapshot_workflow.py
```

This test:
1. ✅ Creates test podcast group, feed, and collection
2. ✅ Adds articles to collection
3. ✅ Creates snapshot with episode ID
4. ✅ Verifies articles moved to snapshot
5. ✅ Verifies new collection created
6. ✅ Tests isolation (new articles go to new collection)
7. ✅ Verifies snapshot stays frozen

## Benefits

### 1. **Controlled Collection Size**
- Collections are limited to one episode's worth of content
- No more infinitely growing collections
- Predictable podcast length

### 2. **Episode Traceability**
- Each episode has a linked collection snapshot
- Can see exactly which articles were used
- Audit trail for content

### 3. **Continuous Collection**
- New articles immediately go to new collection
- No interruption in article gathering
- Automatic collection management

### 4. **Clean Separation**
- Snapshots are frozen and preserved
- Building collections are active and growing
- No confusion about collection state

### 5. **Automatic Management**
- No manual intervention needed
- Collections automatically created
- Snapshots automatically named

## Usage Examples

### Example 1: Automatic Workflow

```python
# AI Overseer automatically handles snapshots
response = await generate_episode_for_group(group_id)

# Behind the scenes:
# 1. Gets active building collection for group
# 2. Creates episode record
# 3. Creates snapshot with episode ID
# 4. Moves articles to snapshot
# 5. Creates new building collection
# 6. Generates podcast from snapshot
```

### Example 2: Manual Snapshot Creation

```python
import httpx

# Create snapshot manually
response = await httpx.post(
    f"http://collections:8014/collections/{collection_id}/snapshot",
    params={"episode_id": episode_id}
)

snapshot_id = response.json()["snapshot_id"]
# Use snapshot_id for episode generation
```

### Example 3: Check Active Collection

```python
# Get current building collection for a group
response = await httpx.get(
    f"http://collections:8014/collections/group/{group_id}/active"
)

collection = response.json()
print(f"Active collection: {collection['collection_id']}")
print(f"Articles: {len(collection['items'])}")
print(f"Status: {collection['status']}")
```

## Monitoring

### Collection Statistics

```http
GET /collections/stats
```

Response:
```json
{
  "total_collections": 25,
  "status_counts": {
    "building": 5,
    "snapshot": 15,
    "ready": 3,
    "expired": 2
  },
  "min_feeds_required": 3,
  "collection_ttl_hours": 24
}
```

### Check Collection Lineage

```python
# Find all snapshots for a group
snapshots = db.query(Collection).filter(
    Collection.status == "snapshot"
).join(
    collection_group_assignment
).filter(
    collection_group_assignment.c.group_id == group_id
).all()

for snapshot in snapshots:
    print(f"Snapshot: {snapshot.name}")
    print(f"  Episode: {snapshot.episode_id}")
    print(f"  Articles: {len(snapshot.articles)}")
    print(f"  Created: {snapshot.created_at}")
```

## Troubleshooting

### Issue: No active collection found

**Symptom:** Error "No active collection found for group"

**Solution:**
```python
# Manually create building collection
collection = Collection(
    name=f"{group.name} Collection",
    description=f"Active collection for {group.name}",
    status="building"
)
db.add(collection)
collection.podcast_groups = [group]
db.commit()
```

### Issue: Snapshot creation fails

**Symptom:** "Failed to create collection snapshot"

**Causes:**
1. Collection has no articles
2. Database constraint violation
3. Episode ID doesn't exist

**Debug:**
```python
# Check collection has articles
articles = db.query(Article).filter(
    Article.collection_id == collection_id
).count()
print(f"Articles in collection: {articles}")

# Verify episode exists
episode = db.query(Episode).filter(
    Episode.id == episode_id
).first()
print(f"Episode exists: {episode is not None}")
```

### Issue: Articles in wrong collection

**Symptom:** New articles going to snapshot instead of building collection

**Solution:** Verify collection status
```python
collection = db.query(Collection).filter(
    Collection.id == collection_id
).first()

if collection.status != "building":
    # Fix: Create new building collection
    new_collection = create_building_collection(group_id)
    # Update article assignment logic
```

## Configuration

### Environment Variables

```bash
# Minimum articles required for a collection
MIN_FEEDS_PER_COLLECTION=3

# Collection time-to-live (hours)
COLLECTION_TTL_HOURS=24

# Collections service URL
COLLECTIONS_URL=http://collections:8014
```

## Future Enhancements

### Planned Features

1. **Automatic Cleanup**
   - Archive old snapshots after 30 days
   - Compress snapshot data for storage efficiency

2. **Collection Templates**
   - Pre-configured collection settings by category
   - Auto-tag collections based on content

3. **Smart Grouping**
   - AI-based article clustering
   - Topic-based collection splitting

4. **Analytics**
   - Collection size trends
   - Article-to-episode conversion rates
   - Optimal collection size recommendations

## Summary

The Collection Snapshot Workflow solves the growing collection problem by:

✅ Creating checkpoints when collections are ready
✅ Freezing snapshots for episode generation  
✅ Automatically creating new collections for future articles
✅ Linking snapshots to episodes for traceability
✅ Preventing collections from growing indefinitely

**Result:** Each podcast uses a fixed set of articles, and new articles automatically go to a fresh collection for the next episode.

