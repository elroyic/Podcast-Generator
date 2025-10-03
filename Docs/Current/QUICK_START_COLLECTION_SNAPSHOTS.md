# Quick Start: Collection Snapshots

## What Changed?

Collections are no longer growing indefinitely! When you generate a podcast, the system now:

1. **Takes a snapshot** of the current collection (freezes it)
2. **Names it** with the episode ID (e.g., "Episode abc12345 Snapshot")
3. **Uses the snapshot** for the podcast
4. **Creates a new empty collection** to gather articles for the next episode

## How to Use

### 1. Run the Migration (One Time)

Before using the new system, update your database schema:

```bash
python migrate_collections_schema.py
```

You should see:
```
✅ Added episode_id column
✅ Added parent_collection_id column
✅ Updated status column documentation
🎉 Migration completed successfully!
```

### 2. Generate Episodes (Same as Before)

The workflow is **automatic** - just generate episodes normally:

```bash
# Via API Gateway
curl -X POST http://localhost:8000/api/overseer/generate-episode \
  -H "Content-Type: application/json" \
  -d '{"group_id": "your-group-id"}'
```

Or trigger from the admin panel.

### 3. What Happens Automatically

Behind the scenes:

```
Step 1: Get active collection for your group
        └─> Has 5 articles

Step 2: Create episode record
        └─> Gets ID: xyz-789

Step 3: Create snapshot
        ├─> Name: "Episode xyz-789 Snapshot"
        ├─> Move 5 articles to snapshot
        └─> Create new empty collection

Step 4: Generate podcast from snapshot
        └─> Uses those 5 articles

Step 5: New articles go to new collection
        └─> Next episode will use these
```

## Verify It's Working

### Check Collection Stats

```bash
curl http://localhost:8014/collections/stats
```

You should see:
```json
{
  "total_collections": 10,
  "status_counts": {
    "building": 3,    ← Active collections gathering articles
    "snapshot": 5,    ← Frozen snapshots for episodes
    "ready": 2
  }
}
```

### View Your Group's Collections

```bash
curl http://localhost:8014/collections/group/{your-group-id}
```

You should see multiple collections:
- **Snapshots:** Named "Episode ... Snapshot", linked to episodes
- **Building:** One active collection gathering new articles

### Check Episode Has Snapshot

After generating an episode, check the database:

```sql
SELECT 
    e.id as episode_id,
    c.name as collection_name,
    c.status as collection_status,
    COUNT(a.id) as article_count
FROM episodes e
LEFT JOIN collections c ON c.episode_id = e.id
LEFT JOIN articles a ON a.collection_id = c.id
WHERE e.id = 'your-episode-id'
GROUP BY e.id, c.name, c.status;
```

Result:
```
episode_id    | collection_name           | status   | article_count
------------- | ------------------------- | -------- | -------------
xyz-789       | Episode xyz-789 Snapshot  | snapshot | 5
```

## Testing

Run the test suite to verify everything works:

```bash
python test_collection_snapshot_workflow.py
```

Expected output:
```
✅ Created snapshot collection: def-456
✅ 5 articles preserved in snapshot
✅ New building collection created: ghi-999
✅ New articles go to new collection: 1
✅ Original collection replaced successfully
🎉 COLLECTION SNAPSHOT WORKFLOW TEST PASSED!
```

## Common Scenarios

### Scenario 1: First Time Setup

**Before:** No collections exist for your group

**What happens:**
1. First article arrives
2. System creates building collection automatically
3. Articles accumulate (min 3 required)
4. You trigger episode generation
5. System creates snapshot + new building collection

**After:** You have 1 snapshot + 1 building collection

---

### Scenario 2: Regular Operation

**Before:** Group has 1 building collection with 8 articles

**Trigger:** Generate episode

**What happens:**
1. Snapshot created: "Episode abc123 Snapshot" (8 articles)
2. New collection created: "{Group Name} Collection" (0 articles)
3. Podcast generated from snapshot
4. New articles go to new collection

**After:** You have 1 snapshot (frozen) + 1 building collection (empty, ready to grow)

---

### Scenario 3: Multiple Episodes

**Before:** Generated 3 episodes already

**Collections:**
```
Snapshot 1: Episode aaa111 Snapshot (5 articles) → Episode 1
Snapshot 2: Episode bbb222 Snapshot (7 articles) → Episode 2  
Snapshot 3: Episode ccc333 Snapshot (6 articles) → Episode 3
Building 1: Tech News Collection (4 articles) → Next episode
```

**Trigger:** Generate 4th episode

**What happens:**
1. Snapshot 4 created from Building 1 (4 articles)
2. New Building 2 created (0 articles)
3. Episode 4 uses Snapshot 4

**After:**
```
Snapshot 1: Episode aaa111 Snapshot (5 articles) → Episode 1
Snapshot 2: Episode bbb222 Snapshot (7 articles) → Episode 2
Snapshot 3: Episode ccc333 Snapshot (6 articles) → Episode 3
Snapshot 4: Episode ddd444 Snapshot (4 articles) → Episode 4
Building 2: Tech News Collection (0 articles) → Next episode
```

## Troubleshooting

### Problem: "No active collection found"

**Cause:** Group has no building collection

**Fix:** System auto-creates one. If it doesn't:
```bash
curl -X GET http://localhost:8014/collections/group/{group-id}/active
```
This endpoint creates a building collection if none exists.

---

### Problem: New articles going to old collection

**Cause:** Collection service not restarted after migration

**Fix:**
```bash
docker-compose restart collections
```

---

### Problem: Snapshot has 0 articles

**Cause:** Building collection was empty when snapshot created

**Fix:** Ensure min 3 articles before generating episode:
```sql
SELECT COUNT(*) FROM articles 
WHERE collection_id = (
    SELECT id FROM collections 
    WHERE status = 'building' 
    AND id IN (
        SELECT collection_id FROM collection_group_assignment 
        WHERE group_id = 'your-group-id'
    )
);
```

---

### Problem: Old collections still growing

**Cause:** Using old episode generation code

**Fix:** Ensure you're using the updated AI Overseer service:
```bash
docker-compose restart ai-overseer
```

## Monitoring Dashboard

Add these queries to your monitoring:

### Active Collections Per Group

```sql
SELECT 
    pg.name as group_name,
    COUNT(DISTINCT c.id) as collection_count,
    SUM(CASE WHEN c.status = 'building' THEN 1 ELSE 0 END) as building,
    SUM(CASE WHEN c.status = 'snapshot' THEN 1 ELSE 0 END) as snapshots
FROM podcast_groups pg
LEFT JOIN collection_group_assignment cga ON cga.group_id = pg.id
LEFT JOIN collections c ON c.id = cga.collection_id
WHERE pg.status = 'active'
GROUP BY pg.name;
```

### Recent Snapshots

```sql
SELECT 
    c.name as snapshot_name,
    c.created_at,
    e.id as episode_id,
    COUNT(a.id) as article_count
FROM collections c
LEFT JOIN episodes e ON e.id = c.episode_id
LEFT JOIN articles a ON a.collection_id = c.id
WHERE c.status = 'snapshot'
GROUP BY c.id, c.name, c.created_at, e.id
ORDER BY c.created_at DESC
LIMIT 10;
```

### Articles Distribution

```sql
SELECT 
    c.status,
    COUNT(DISTINCT c.id) as collection_count,
    COUNT(a.id) as total_articles,
    AVG(article_count) as avg_per_collection
FROM collections c
LEFT JOIN (
    SELECT collection_id, COUNT(*) as article_count
    FROM articles
    GROUP BY collection_id
) a ON a.collection_id = c.id
GROUP BY c.status;
```

## Key Takeaways

✅ **Automatic:** Snapshots created automatically during episode generation
✅ **Named:** Snapshots named with episode ID for easy tracking
✅ **Frozen:** Snapshots never change after creation
✅ **Continuous:** New collection immediately ready for new articles
✅ **Traceable:** Each episode links to its snapshot
✅ **Clean:** Collections stay small and manageable

## Need Help?

📖 Full Documentation: `COLLECTION_SNAPSHOT_WORKFLOW.md`
🔧 Implementation Details: `COLLECTION_SNAPSHOT_IMPLEMENTATION.md`
🧪 Run Tests: `python test_collection_snapshot_workflow.py`
🗄️ Run Migration: `python migrate_collections_schema.py`

---

**You're all set!** Collections will now checkpoint automatically and stay a manageable size. 🎉

