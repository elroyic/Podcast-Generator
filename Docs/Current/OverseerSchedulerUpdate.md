# Enhancement Proposal: Adaptive Cadence for Overseer & Scheduler

## Objective

Eliminate artificial bottlenecks caused by the current "one podcast per day" hard cap by introducing adaptive cadence scheduling. This approach ensures podcasts remain timely, relevant, and high-quality, while avoiding skipped or low-content episodes during periods of light news flow.

---

## Enhancements to Overseer & Scheduler

### 1. Adaptive Cadence Logic

- **Daily Mode (Default):**
  - Release one podcast per day if at least **N** feeds (e.g., 3+) are available in a complete collection.
- **Fallback Modes:**
  - **Every 3rd Day:** If the daily threshold is unmet for two consecutive days, bundle feeds into a 3-day digest.
  - **Weekly Digest:** If news flow remains light, escalate to a weekly round-up.
- **Dynamic Rule:**
  - Overseer evaluates content readiness each cycle.
  - If the threshold is unmet, roll forward to the next cadence bucket.
  - If the threshold is met, release immediately, respecting cadence rules.

### 2. Removal of Bottleneck

- Replace the "one release per day" bottleneck with conditional cadence enforcement.
- Multiple collections can be queued, but only the most relevant is selected for release based on:
  - **Freshness of feeds**
  - **Completeness of collection**
  - **Priority tags** (e.g., breaking news > evergreen topics)

### 3. Scheduling Flexibility

- Overseer maintains release slots for Daily, 3-Day, and Weekly cadences.
- If multiple collections qualify, Overseer selects the highest-ranked one for that slot.
- Remaining collections roll forward automatically.

---

## Dashboard Enhancements

### 1. Cadence Status Indicator

- Display the current mode: Daily / 3-Day / Weekly.
- Show countdown to the next scheduled release.
- Highlight the reason for any cadence shift (e.g., "Insufficient feeds for Daily → shifted to 3-Day Digest").

### 2. Collection Readiness View

- Show all active collections with:
  - Feed count
  - Completeness status (Ready / Incomplete)
  - Age of oldest feed
  - Priority tags

### 3. Bottleneck Transparency

- Replace "Bottleneck" warnings with "Cadence Adjustment" notifications.
- Example:  
  > "Daily release skipped — insufficient feeds. Next release scheduled in 2 days (3-Day Digest)."

### 4. Historical Analytics

- Track release frequency by cadence type.
- Show percentage of Daily vs 3-Day vs Weekly releases over time.
- Provide a trendline of average feeds per collection to help tune thresholds.

---

## Expected Outcomes

- **No artificial backlog:** Multiple collections won’t pile up waiting for a daily slot.
- **Relevance preserved:** Episodes are only released when content is strong enough.
- **Transparency improved:** Dashboard clearly shows why cadence shifted.
- **Scalability:** System adapts naturally to both high-volume and low-volume news cycles.