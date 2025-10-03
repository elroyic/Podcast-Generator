-- Migration script to add episode_id and parent_collection_id to collections table
-- Run this against your PostgreSQL database

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

RAISE NOTICE '✅ Updated status column documentation';

-- Show current table structure
SELECT 
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name='collections' 
ORDER BY ordinal_position;

RAISE NOTICE '🎉 Migration completed successfully!';

