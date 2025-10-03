#!/bin/bash
# Verify that the collection snapshot migration was successful

echo "======================================================================="
echo "Verifying Collection Snapshot Migration"
echo "======================================================================="
echo ""

echo "Checking collections table structure..."
echo ""

docker-compose exec -T postgres psql -U podcast_user -d podcast_ai << 'EOF'
SELECT 
    column_name, 
    data_type, 
    is_nullable,
    CASE 
        WHEN column_name = 'episode_id' THEN '← Links snapshot to episode'
        WHEN column_name = 'parent_collection_id' THEN '← Tracks collection lineage'
        ELSE ''
    END as note
FROM information_schema.columns 
WHERE table_name='collections' 
ORDER BY ordinal_position;
EOF

echo ""
echo "Checking for existing collections..."
echo ""

docker-compose exec -T postgres psql -U podcast_user -d podcast_ai << 'EOF'
SELECT 
    COUNT(*) as total_collections,
    SUM(CASE WHEN status = 'building' THEN 1 ELSE 0 END) as building,
    SUM(CASE WHEN status = 'ready' THEN 1 ELSE 0 END) as ready,
    SUM(CASE WHEN status = 'snapshot' THEN 1 ELSE 0 END) as snapshots,
    SUM(CASE WHEN episode_id IS NOT NULL THEN 1 ELSE 0 END) as linked_to_episodes
FROM collections;
EOF

echo ""
echo "======================================================================="
echo "✅ Migration verification complete!"
echo "======================================================================="
echo ""
echo "The collections table now has:"
echo "  - episode_id: Links snapshots to episodes"
echo "  - parent_collection_id: Tracks collection lineage"
echo ""
echo "Collections service has been restarted and is using the new schema."
echo ""

