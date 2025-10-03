# Reviewer Service Production Pause Implementation

## Summary

Implemented automatic pausing of the Reviewer Service when a collection is being processed through the podcast production pipeline (Presenter → Writer → Editor → Voice) to prevent resource bottlenecks and ensure podcast production has priority access to system resources.

## Problem Statement

The Reviewer Service was running continuously and potentially consuming significant resources, which could bottleneck the application when podcast production was active. This led to:
- Resource contention between review processing and podcast production
- Slower podcast generation times
- Inefficient use of CPU, memory, and LLM model resources

## Solution

Implemented a Redis-based production lock mechanism that:
1. Automatically pauses the Reviewer Service when podcast production starts
2. Resumes the Reviewer Service when podcast production completes
3. Provides manual pause/resume controls for admin override
4. Includes safety measures (TTL) to prevent stuck locks

## Files Modified

### 1. `services/ai-overseer/app/services.py`

**Changes:**
- Added Redis client to `EpisodeGenerationService.__init__()`
- Added `_set_production_active()` method to set production lock
- Added `_clear_production_lock()` method to clear production lock
- Modified `generate_complete_episode()` to:
  - Set production lock when episode generation starts (after creating episode record)
  - Clear production lock when generation completes successfully
  - Clear production lock on error in exception handler

**Code Additions:**
```python
# Redis for production lock
self.redis = redis.Redis.from_url(REDIS_URL, decode_responses=True)

def _set_production_active(self, group_id: UUID, episode_id: UUID):
    """Set production lock to pause reviewer service during podcast production."""
    lock_key = "podcast:production:active"
    lock_value = json.dumps({
        "group_id": str(group_id),
        "episode_id": str(episode_id),
        "started_at": datetime.utcnow().isoformat()
    })
    # Set lock with 2 hour TTL as safety measure
    self.redis.set(lock_key, lock_value, ex=2 * 3600)
    logger.info(f"🔒 Production lock activated - Reviewer Service paused for group {group_id}")

def _clear_production_lock(self):
    """Clear production lock to resume reviewer service."""
    lock_key = "podcast:production:active"
    self.redis.delete(lock_key)
    logger.info("🔓 Production lock cleared - Reviewer Service resumed")
```

### 2. `services/reviewer/main.py`

**Changes:**
- Modified `queue_worker()` function to check production lock before processing reviews
- Added pause logic: sleeps for 10 seconds when production is active
- Added three new API endpoints:
  - `GET /production/status` - Check if production is active
  - `POST /production/pause` - Manually pause reviews (admin)
  - `POST /production/resume` - Manually resume reviews (admin)
- Modified `GET /queue/worker/status` to include production status

**Code Additions:**
```python
# In queue_worker() function:
# Check if podcast production is active - if so, pause reviews
production_lock_key = "podcast:production:active"
if r.exists(production_lock_key):
    production_info = r.get(production_lock_key)
    logger.info(f"⏸️ Reviewer paused - Podcast production active: {production_info}")
    time.sleep(10)  # Wait 10 seconds before checking again
    continue
```

### 3. `services/ai-overseer/app/tasks.py`

**Changes:**
- Modified `send_articles_to_reviewer()` task to check production lock before dispatching reviews
- Added early return when production is active
- Added logging for skipped dispatches

**Code Additions:**
```python
# Check if podcast production is active - if so, skip review dispatch
import redis
redis_client = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"), decode_responses=True)
production_lock_key = "podcast:production:active"

if redis_client.exists(production_lock_key):
    production_info = redis_client.get(production_lock_key)
    logger.info(f"⏸️ Skipping review dispatch - Podcast production active: {production_info}")
    return
```

## Documentation Created

### 1. `Docs/Current/Reviewer-Production-Pause.md`
Comprehensive documentation covering:
- Overview and how it works
- Implementation details
- API endpoints
- Resource management benefits
- Production workflow timeline
- Monitoring and troubleshooting
- Configuration
- Future enhancements

### 2. `test_production_pause.py`
Test script to verify the implementation:
- Tests production status checking
- Tests manual pause/resume controls
- Tests queue worker status
- Simulates production workflow
- Verifies automatic pause/resume behavior

## API Endpoints Added

### Check Production Status
```bash
GET http://reviewer:8008/production/status
```

### Manual Pause (Admin)
```bash
POST http://reviewer:8008/production/pause
```

### Manual Resume (Admin)
```bash
POST http://reviewer:8008/production/resume
```

### Enhanced Worker Status
```bash
GET http://reviewer:8008/queue/worker/status
```
Now includes:
- `production_active`: Boolean
- `production_info`: Object with production details
- `paused`: Boolean indicating if reviewer is paused

## How It Works

### Production Flow

1. **Collection Ready** → Episode generation triggered
2. **Episode Record Created** → Production lock SET 🔒
3. **Production Pipeline Executes:**
   - Generate presenter briefs
   - Generate script (Writer/Text-Gen)
   - Generate presenter feedback
   - Edit script (Editor)
   - Generate metadata
   - Generate audio (Voice/TTS)
   - Publish episode
4. **Production Complete** → Production lock CLEARED 🔓
5. **Reviewer Service** → Resumes processing queued articles

### Reviewer Behavior During Production

- **Queue Worker**: Checks lock every iteration, sleeps 10 seconds if production is active
- **Review Dispatch**: Skips dispatching new articles when production is active
- **Existing Queue**: Articles remain queued and process when production completes

## Safety Measures

1. **TTL (Time To Live)**: Production lock expires after 2 hours automatically
2. **Manual Override**: Admin can manually pause/resume regardless of production state
3. **Error Handling**: Production lock is cleared even if episode generation fails
4. **Logging**: Clear logging of pause/resume events for monitoring

## Benefits

### Resource Management
✅ Podcast production gets exclusive access to resources during generation  
✅ No resource contention between production and review  
✅ Faster podcast generation times  
✅ More efficient use of CPU, memory, and LLM models  

### Operational
✅ Automatic pause/resume (no manual intervention needed)  
✅ Manual override controls for admin needs  
✅ Clear logging for monitoring and troubleshooting  
✅ Safety timeout prevents stuck locks  

### User Experience
✅ Faster podcast production  
✅ Reliable, predictable behavior  
✅ Reviews queue up and process later (nothing lost)  
✅ Transparent status via API endpoints  

## Testing

Run the test script to verify the implementation:

```bash
# Make sure services are running
docker-compose up -d reviewer ai-overseer

# Run test script
python test_production_pause.py
```

Expected output:
- ✅ Production status can be checked
- ✅ Reviews can be manually paused
- ✅ Reviews can be manually resumed
- ✅ Lock state is properly managed in Redis
- ✅ Simulated production workflow works correctly

## Monitoring

### Key Log Messages

**Episode Generation Service:**
```
🔒 Production lock activated - Reviewer Service paused for group {group_id}
🔓 Production lock cleared - Reviewer Service resumed
```

**Reviewer Service:**
```
⏸️ Reviewer paused - Podcast production active: {...}
```

**Review Dispatch Task:**
```
⏸️ Skipping review dispatch - Podcast production active: {...}
```

### Health Check

Check reviewer status at any time:
```bash
curl http://localhost:8008/production/status
```

## Troubleshooting

### Reviewer Stuck Paused

1. Check production status:
   ```bash
   curl http://localhost:8008/production/status
   ```

2. Manually resume if needed:
   ```bash
   curl -X POST http://localhost:8008/production/resume
   ```

3. Check Redis directly:
   ```bash
   redis-cli
   > GET podcast:production:active
   > DEL podcast:production:active  # Force clear if stuck
   ```

### Lock Not Clearing After Error

The 2-hour TTL will automatically clear stuck locks, or use manual resume endpoint.

## Future Enhancements

Potential improvements:
- [ ] Configurable pause check interval
- [ ] Metrics on pause duration and frequency
- [ ] Admin dashboard showing production/review status
- [ ] Priority queue for urgent reviews during production
- [ ] Multiple production lock levels (by group_id)
- [ ] Graceful resume with rate limiting

## Deployment Notes

### No Configuration Changes Required
- Uses existing `REDIS_URL` environment variable
- No new dependencies needed
- No database schema changes

### Backward Compatibility
- ✅ Fully backward compatible
- ✅ Existing review functionality unchanged
- ✅ Only adds pause behavior during production
- ✅ Manual endpoints are optional (for admin use)

### Rolling Deployment
Safe to deploy without downtime:
1. Deploy updated Reviewer Service
2. Deploy updated AI Overseer Service
3. Monitor logs for pause/resume events
4. Test with manual pause/resume endpoints

## Conclusion

This implementation successfully addresses the resource bottleneck concern by ensuring that podcast production has exclusive access to system resources during the critical production pipeline. The automatic pause/resume mechanism is transparent, reliable, and includes safety measures and manual overrides for complete control.

The solution is production-ready, fully documented, and includes comprehensive testing capabilities.
