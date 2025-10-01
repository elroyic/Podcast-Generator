-- Create collections for podcast groups that have feeds but no collections
-- This fixes the issue where articles accumulate without being organized

DO $$
DECLARE
    group_record RECORD;
    new_collection_id UUID;
    articles_assigned INTEGER;
BEGIN
    -- Loop through all active groups
    FOR group_record IN 
        SELECT 
            pg.id as group_id,
            pg.name as group_name,
            COUNT(DISTINCT nfa.feed_id) as feed_count,
            COUNT(DISTINCT cga.collection_id) as collection_count
        FROM podcast_groups pg
        LEFT JOIN news_feed_assignment nfa ON nfa.group_id = pg.id
        LEFT JOIN collection_group_assignment cga ON cga.group_id = pg.id
        WHERE pg.status = 'ACTIVE'
        GROUP BY pg.id, pg.name
        HAVING COUNT(DISTINCT nfa.feed_id) > 0 
           AND COUNT(DISTINCT cga.collection_id) = 0
    LOOP
        RAISE NOTICE '';
        RAISE NOTICE 'Group: %', group_record.group_name;
        RAISE NOTICE '  Feeds: %', group_record.feed_count;
        RAISE NOTICE '  Creating building collection...';
        
        -- Generate new UUID for collection
        new_collection_id := gen_random_uuid();
        
        -- Create new collection
        INSERT INTO collections (id, name, description, status, created_at, updated_at)
        VALUES (
            new_collection_id,
            group_record.group_name || ' Collection',
            'Active collection for ' || group_record.group_name,
            'building',
            NOW(),
            NOW()
        );
        
        -- Link collection to group
        INSERT INTO collection_group_assignment (collection_id, group_id)
        VALUES (new_collection_id, group_record.group_id);
        
        RAISE NOTICE '  ✅ Created collection: % Collection', group_record.group_name;
        
        -- Assign unassigned articles from this group's feeds to the collection
        WITH updated AS (
            UPDATE articles a
            SET collection_id = new_collection_id
            WHERE a.feed_id IN (
                SELECT feed_id 
                FROM news_feed_assignment 
                WHERE group_id = group_record.group_id
            )
            AND a.collection_id IS NULL
            RETURNING a.id
        )
        SELECT COUNT(*) INTO articles_assigned FROM updated;
        
        RAISE NOTICE '  ✅ Assigned % articles to collection', articles_assigned;
        
        -- If collection has enough articles, mark as ready
        IF articles_assigned >= 3 THEN
            UPDATE collections 
            SET status = 'ready', updated_at = NOW()
            WHERE id = new_collection_id;
            
            RAISE NOTICE '  ✅ Collection marked as READY (has % articles)', articles_assigned;
        END IF;
        
    END LOOP;
    
    RAISE NOTICE '';
    RAISE NOTICE '=======================================================================';
    RAISE NOTICE 'Collection creation complete!';
    RAISE NOTICE '=======================================================================';
    
END $$;

