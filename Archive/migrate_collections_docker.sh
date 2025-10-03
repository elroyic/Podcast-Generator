#!/bin/bash
# Migration script to run inside Docker container
# This avoids Python version compatibility issues

set -e

echo "======================================================================="
echo "Collection Snapshot Schema Migration (Docker)"
echo "======================================================================="

# Run the SQL migration script via Docker
docker-compose exec -T postgres psql -U podcast_user -d podcast_ai << 'EOF'

-- Check if episode_id column exists, add if not
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='collections' AND column_name='episode_id'
    ) THEN
        ALTER TABLE collections 
        ADD COLUMN episode_id UUID REFERENCES episodes(id);
        
        RAISE NOTICE '✅ Added episode_id column to collections table';
    ELSE
        RAISE NOTICE 'ℹ️  episode_id column already exists';
    END IF;
END $$;

-- Check if parent_collection_id column exists, add if not
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='collections' AND column_name='parent_collection_id'
    ) THEN
        ALTER TABLE collections 
        ADD COLUMN parent_collection_id UUID REFERENCES collections(id);
        
        RAISE NOTICE '✅ Added parent_collection_id column to collections table';
    ELSE
        RAISE NOTICE 'ℹ️  parent_collection_id column already exists';
    END IF;
END $$;

-- Update status column comment
COMMENT ON COLUMN collections.status IS 'Collection status: building (actively collecting), ready (enough articles), snapshot (frozen for episode), used (episode generated), expired (too old)';

-- Show current table structure
\echo ''
\echo 'Current collections table structure:'
SELECT 
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name='collections' 
ORDER BY ordinal_position;

EOF

echo ""
echo "======================================================================="
echo "🎉 Migration completed successfully!"
echo "======================================================================="
echo ""
echo "Next steps:"
echo "1. Restart services: docker-compose restart collections ai-overseer"
echo "2. Test the workflow: python test_collection_snapshot_workflow.py"
echo ""
