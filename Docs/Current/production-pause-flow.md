# Production Pause Flow Diagram

## System State: Normal Operation (No Production Active)

```
┌─────────────────────────────────────────────────────────────┐
│                     NORMAL OPERATION                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────┐         ┌──────────────────┐         │
│  │  News Feed       │         │  Reviewer        │         │
│  │  Service         │────────▶│  Service         │         │
│  │                  │         │  [ACTIVE ✓]      │         │
│  └──────────────────┘         └──────────────────┘         │
│          │                             │                    │
│          │                             │                    │
│          ▼                             ▼                    │
│  ┌──────────────────┐         ┌──────────────────┐         │
│  │  Articles        │         │  Redis Queue     │         │
│  │  in Database     │         │  Processing...   │         │
│  └──────────────────┘         └──────────────────┘         │
│          │                             │                    │
│          │                             ▼                    │
│          │                     ┌──────────────────┐         │
│          │                     │  Reviewed        │         │
│          │                     │  Articles        │         │
│          │                     └──────────────────┘         │
│          │                             │                    │
│          └─────────────────────────────┘                    │
│                                                             │
└─────────────────────────────────────────────────────────────┘

Redis: podcast:production:active = [NOT SET]
```

## System State: Production Active (Reviewer Paused)

```
┌─────────────────────────────────────────────────────────────┐
│              PRODUCTION ACTIVE - REVIEWER PAUSED            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │            PODCAST PRODUCTION PIPELINE               │  │
│  │                                                      │  │
│  │  Collection → Presenter → Writer → Editor → Voice   │  │
│  │                                                      │  │
│  │  [🎬 IN PROGRESS - PRIORITY RESOURCE ACCESS]        │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌──────────────────┐         ┌──────────────────┐         │
│  │  Reviewer        │         │  Redis Lock      │         │
│  │  Service         │◀────────│  SET ⏸️          │         │
│  │  [PAUSED ⏸️]     │         │                  │         │
│  └──────────────────┘         └──────────────────┘         │
│          │                                                  │
│          │                                                  │
│          ▼                                                  │
│  ┌──────────────────┐                                      │
│  │  Queue Worker    │                                      │
│  │  Sleeping...     │                                      │
│  │  (10 sec wait)   │                                      │
│  └──────────────────┘                                      │
│          │                                                  │
│          ▼                                                  │
│  ┌──────────────────┐                                      │
│  │  Articles        │                                      │
│  │  Queued          │                                      │
│  │  (Waiting...)    │                                      │
│  └──────────────────┘                                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘

Redis: podcast:production:active = {
  "group_id": "uuid",
  "episode_id": "uuid",
  "started_at": "2025-09-30T12:00:00Z"
}
```

## Complete Production Workflow Timeline

```
TIME  │  PRODUCTION STATE           │  REVIEWER STATE      │  REDIS LOCK
──────┼────────────────────────────┼─────────────────────┼──────────────
      │                            │                     │
  T0  │  Collection Ready          │  [ACTIVE]           │  [NOT SET]
      │  ↓                         │  Processing reviews │
      │                            │                     │
  T1  │  Episode Gen Starts        │  [ACTIVE]           │  [NOT SET]
      │  ↓                         │  Processing reviews │
      │  Create Episode Record     │                     │
      │  ↓                         │                     │
  T2  │  🔒 LOCK SET               │  [PAUSED] ⏸️        │  ✓ SET
      │  ↓                         │  Stopped processing │  TTL: 2hrs
      │  Generate Briefs           │  Queue builds up... │
      │  ↓                         │                     │
  T3  │  Generate Script           │  [PAUSED] ⏸️        │  ✓ SET
      │  ↓                         │  Waiting...         │
      │  Edit Script               │                     │
      │  ↓                         │                     │
  T4  │  Generate Metadata         │  [PAUSED] ⏸️        │  ✓ SET
      │  ↓                         │  Waiting...         │
      │  Generate Audio            │                     │
      │  ↓                         │                     │
  T5  │  Publish Episode           │  [PAUSED] ⏸️        │  ✓ SET
      │  ↓                         │  Waiting...         │
  T6  │  🔓 LOCK CLEARED           │  [ACTIVE] ✓         │  CLEARED
      │  Episode Complete          │  Resumed!           │
      │  ↓                         │  ↓                  │
  T7  │  Idle                      │  Processing queue   │  [NOT SET]
      │                            │  Catching up...     │
      │                            │                     │
```

## Production Lock Lifecycle

```
┌─────────────────────────────────────────────────────────────┐
│                    LOCK LIFECYCLE                           │
└─────────────────────────────────────────────────────────────┘

START: Episode Generation Triggered
  │
  ├──▶ Create Episode Record
  │    
  ├──▶ SET LOCK: podcast:production:active
  │    {
  │      "group_id": "xxx",
  │      "episode_id": "yyy",
  │      "started_at": "timestamp"
  │    }
  │    TTL: 7200 seconds (2 hours)
  │
  ├──▶ REVIEWER PAUSES
  │    • Queue worker checks lock
  │    • Sleeps 10 seconds
  │    • Repeats until lock cleared
  │
  ├──▶ PRODUCTION PIPELINE RUNS
  │    [Exclusive resource access]
  │
  ├──▶ PRODUCTION COMPLETES (Success)
  │    └─▶ CLEAR LOCK
  │        └─▶ REVIEWER RESUMES
  │
  └──▶ PRODUCTION FAILS (Error)
       └─▶ CLEAR LOCK (Exception Handler)
           └─▶ REVIEWER RESUMES

FALLBACK: TTL Expires (2 hours)
  └─▶ LOCK AUTO-CLEARED
      └─▶ REVIEWER RESUMES
```

## Reviewer Queue Worker Decision Flow

```
┌─────────────────────────────────────────────────────────────┐
│              QUEUE WORKER PROCESSING LOOP                   │
└─────────────────────────────────────────────────────────────┘

START: Queue Worker Running
  │
  ├──▶ Check: podcast:production:active exists?
  │    │
  │    ├─▶ YES: Production Active
  │    │   │
  │    │   ├─▶ Log: "⏸️ Reviewer paused"
  │    │   │
  │    │   ├─▶ Sleep 10 seconds
  │    │   │
  │    │   └─▶ LOOP (check again)
  │    │
  │    └─▶ NO: Production Inactive
  │        │
  │        ├─▶ Check queue for articles
  │        │   │
  │        │   ├─▶ Queue Empty
  │        │   │   └─▶ Wait 5 seconds
  │        │   │       └─▶ LOOP
  │        │   │
  │        │   └─▶ Article Found
  │        │       │
  │        │       ├─▶ Process Review
  │        │       │   │
  │        │       │   ├─▶ Light Reviewer
  │        │       │   │
  │        │       │   ├─▶ Heavy Reviewer (if needed)
  │        │       │   │
  │        │       │   └─▶ Save to Database
  │        │       │
  │        │       └─▶ LOOP (next article)
  │        │
  │        └─▶ LOOP
```

## Resource Allocation Comparison

### BEFORE: Resource Contention

```
┌────────────────────────────────────────────────────┐
│              SYSTEM RESOURCES (100%)               │
├────────────────────────────────────────────────────┤
│                                                    │
│  Reviewer Service:     ████████ (40%)             │
│                                                    │
│  Production Pipeline:  ██████ (30%)               │
│                                                    │
│  Other Services:       █████ (25%)                │
│                                                    │
│  Available:            █ (5%)                     │
│                                                    │
└────────────────────────────────────────────────────┘

⚠️ PROBLEMS:
  • Resource contention
  • Slower production
  • Unpredictable performance
```

### AFTER: Production Priority

```
┌────────────────────────────────────────────────────┐
│         DURING PRODUCTION (Reviewer Paused)        │
├────────────────────────────────────────────────────┤
│                                                    │
│  Reviewer Service:     ⏸️ (0% - PAUSED)           │
│                                                    │
│  Production Pipeline:  ████████████████ (70%)     │
│                                                    │
│  Other Services:       █████ (25%)                │
│                                                    │
│  Available:            █ (5%)                     │
│                                                    │
└────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────┐
│         NORMAL OPERATION (No Production)           │
├────────────────────────────────────────────────────┤
│                                                    │
│  Reviewer Service:     ████████████ (50%)         │
│                                                    │
│  Production Pipeline:  (0% - IDLE)                │
│                                                    │
│  Other Services:       ██████████ (40%)           │
│                                                    │
│  Available:            ██ (10%)                   │
│                                                    │
└────────────────────────────────────────────────────┘

✅ BENEFITS:
  • No resource contention
  • Faster production (70% vs 30%)
  • Predictable performance
  • Better resource utilization
```

## Manual Control Flow

```
┌─────────────────────────────────────────────────────────────┐
│                  ADMIN MANUAL CONTROLS                      │
└─────────────────────────────────────────────────────────────┘

CHECK STATUS:
  GET /production/status
    ↓
  Returns:
    • production_active: true/false
    • production_info: {...}
    • reviewer_paused: true/false
    • message: "Status description"

MANUAL PAUSE:
  POST /production/pause
    ↓
  Sets Lock:
    {
      "manual_pause": true,
      "paused_at": "timestamp",
      "reason": "Manual admin override"
    }
    TTL: 24 hours
    ↓
  Reviewer → [PAUSED]

MANUAL RESUME:
  POST /production/resume
    ↓
  Deletes Lock
    ↓
  Reviewer → [ACTIVE]

GET WORKER STATUS:
  GET /queue/worker/status
    ↓
  Returns:
    • worker_running: true/false
    • production_active: true/false
    • paused: true/false
    • production_info: {...}
```

## Monitoring Dashboard View

```
┌─────────────────────────────────────────────────────────────┐
│               REVIEWER SERVICE STATUS                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Service Status:        ✓ Running                          │
│  Worker Status:         ✓ Active                           │
│  Production Active:     ⏸️ YES (Episode xyz in progress)   │
│  Reviewer State:        ⏸️ PAUSED                          │
│  Queue Length:          47 articles                        │
│  Estimated Resume:      ~5 minutes                         │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  Production Info:                                          │
│    Group ID:     abc-123-def-456                           │
│    Episode ID:   xyz-789-ghi-012                           │
│    Started At:   2025-09-30 12:34:56 UTC                   │
│    Duration:     3m 45s                                    │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  Recent Activity:                                          │
│    12:34:56 - 🔒 Production lock activated                 │
│    12:34:57 - ⏸️ Reviewer paused                           │
│    12:35:07 - ⏸️ Reviewer paused (waiting...)              │
│    12:35:17 - ⏸️ Reviewer paused (waiting...)              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```
