# Reviewer Service Production Pause Feature

## Overview

The Reviewer Service now automatically pauses when a podcast collection is being processed through the production pipeline to prevent resource bottlenecks and ensure podcast production has priority access to system resources.

## How It Works

### Automatic Pause During Production

When a collection is ready and begins the podcast production workflow:
1. **Collection Ready** → **Presenter** → **Writer** → **Editor** → **Voice** → **Publishing**

The Reviewer Service automatically pauses at the start and resumes when production completes.

### Implementation Details

#### 1. Production Lock Mechanism

A Redis key `podcast:production:active` is used to signal when podcast production is in progress:

```json
{
  "group_id": "uuid",
  "episode_id": "uuid",
  "started_at": "2025-09-30T12:00:00Z"
}
```

- **TTL**: 2 hours (safety measure to prevent indefinite locks)
- **Set**: When episode generation starts (after creating episode record)
- **Cleared**: When episode generation completes or errors

#### 2. Modified Components

**A. Episode Generation Service** (`services/ai-overseer/app/services.py`)
- Sets production lock when episode generation starts
- Clears production lock when generation completes or fails
- Logs: `🔒 Production lock activated - Reviewer Service paused`
- Logs: `🔓 Production lock cleared - Reviewer Service resumed`

**B. Reviewer Service Queue Worker** (`services/reviewer/main.py`)
- Checks production lock before processing each review
- Sleeps for 10 seconds when production is active
- Logs: `⏸️ Reviewer paused - Podcast production active`
- Resumes automatically when lock is cleared

**C. Review Dispatch Task** (`services/ai-overseer/app/tasks.py`)
- Checks production lock before dispatching new articles for review
- Skips dispatch when production is active
- Logs: `⏸️ Skipping review dispatch - Podcast production active`

## API Endpoints

### Check Production Status

```bash
GET http://reviewer:8008/production/status
```

**Response:**
```json
{
  "production_active": true,
  "production_info": {
    "group_id": "uuid",
    "episode_id": "uuid",
    "started_at": "2025-09-30T12:00:00Z"
  },
  "reviewer_paused": true,
  "message": "Reviewer Service is PAUSED during podcast production"
}
```

### Manual Pause (Admin Override)

```bash
POST http://reviewer:8008/production/pause
```

**Response:**
```json
{
  "status": "paused",
  "message": "Reviewer Service has been manually paused",
  "lock_info": {
    "manual_pause": true,
    "paused_at": "2025-09-30T12:00:00Z",
    "reason": "Manual admin override"
  }
}
```

### Manual Resume (Admin Override)

```bash
POST http://reviewer:8008/production/resume
```

**Response:**
```json
{
  "status": "active",
  "message": "Reviewer Service has been manually resumed"
}
```

### Check Queue Worker Status

```bash
GET http://reviewer:8008/queue/worker/status
```

**Response:**
```json
{
  "status": "running",
  "worker_running": true,
  "thread_alive": true,
  "production_active": true,
  "production_info": {...},
  "paused": true
}
```

## Resource Management Benefits

### Before Implementation
- Reviewer Service ran continuously, consuming resources
- Potential bottlenecks when both production and review were active
- Competition for CPU, memory, and LLM model resources
- Slower podcast production times

### After Implementation
- ✅ Reviewer Service automatically pauses during production
- ✅ Podcast production has priority access to all resources
- ✅ Faster podcast generation (no resource contention)
- ✅ Reviews queue up and process when production completes
- ✅ Automatic safety timeout (2 hours) prevents stuck locks
- ✅ Manual override controls for admin needs

## Production Workflow Timeline

```
1. Collection becomes ready
   ↓
2. Episode generation starts
   → Production lock SET (Reviewer PAUSED) 🔒
   ↓
3. Production pipeline executes:
   - Create episode record
   - Generate presenter briefs
   - Generate script (Writer/Text-Gen)
   - Generate presenter feedback
   - Edit script (Editor)
   - Generate metadata
   - Generate audio (Voice/TTS)
   - Publish episode
   ↓
4. Episode generation completes
   → Production lock CLEARED (Reviewer RESUMED) 🔓
   ↓
5. Reviewer Service resumes processing queued articles
```

## Monitoring

### Logs to Watch

**Episode Generation:**
```
🔒 Production lock activated - Reviewer Service paused for group {group_id}
[... production workflow ...]
🔓 Production lock cleared - Reviewer Service resumed
```

**Reviewer Service:**
```
⏸️ Reviewer paused - Podcast production active: {...}
[... waits 10 seconds ...]
⏸️ Reviewer paused - Podcast production active: {...}
[... production completes ...]
Processing queue item for feed {feed_id}
```

**Review Dispatch:**
```
⏸️ Skipping review dispatch - Podcast production active: {...}
```

### Health Check

The `/queue/worker/status` endpoint now includes production status:
- `production_active`: Boolean indicating if production is running
- `production_info`: Details about the current production run
- `paused`: Boolean indicating if reviewer is paused

## Configuration

No environment variables are needed. The feature works automatically using:
- **Redis URL**: `REDIS_URL` (already configured)
- **Lock TTL**: 2 hours (hardcoded safety measure)
- **Pause check interval**: 10 seconds (hardcoded in queue worker)

## Troubleshooting

### Reviewer Stuck Paused

If the reviewer remains paused after production should have completed:

1. **Check production status:**
   ```bash
   curl http://localhost:8008/production/status
   ```

2. **Manually resume if needed:**
   ```bash
   curl -X POST http://localhost:8008/production/resume
   ```

3. **Check Redis directly:**
   ```bash
   redis-cli
   > GET podcast:production:active
   > DEL podcast:production:active  # Force clear if stuck
   ```

### Production Lock Not Clearing

If episode generation fails and doesn't clear the lock:
- The 2-hour TTL will automatically clear it
- Or manually clear using the resume endpoint above

### Performance Issues

If you still experience resource contention:
- Check if multiple episode generations are running simultaneously
- Review Docker resource allocations
- Consider adjusting the pause check interval (currently 10 seconds)

## Future Enhancements

Potential improvements:
- [ ] Configurable pause check interval
- [ ] Metrics on pause duration and frequency
- [ ] Admin dashboard showing production/review status
- [ ] Priority queue for urgent reviews during production
- [ ] Multiple production lock levels (by group_id)
- [ ] Graceful resume with rate limiting

## Related Documentation

- [Reviewer Service Enhancement](./ReviewerEnhancement.md)
- [Missing Functionality](./Missing-Functionality.md)
- [Workflow Status](../../WORKFLOW_STATUS.md)
