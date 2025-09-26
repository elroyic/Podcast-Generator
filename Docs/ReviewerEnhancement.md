# Specification – Reviewer Enhancements
**Version:** 1.3  
**Author:** [Your Team]  
**Date:** 2025‑09‑26  

---

## 1. Overview  

The goal is to improve throughput and reliability of the **Review** stage in the podcast‑generation pipeline.  The changes fall into three categories:

| # | Category | Description |
|---|----------|-------------|
| 1️⃣ | **Deduplication** | Prevent identical RSS items from reaching the Reviewer. |
| 2️⃣ | **Two‑Tier Review Architecture** | LightReviewer (fast, low‑cost) → optional HeavyReviewer (high‑quality) based on confidence. |
| 3️⃣ | **Dashboard & Ops** | Add profiling stats, runtime configuration, and ability to scale two LightReviewer workers concurrently. |

All changes must be backward‑compatible with the existing workflow, configurable from the **Reviewer Dashboard**, and observable via the **Dashboard → Metrics** page.

---

## 2. Glossary  

| Term | Meaning |
|------|---------|
| **Feed** | A single RSS item (title, link, description, publish date, source). |
| **Fingerprint** | Deterministic hash (SHA‑256) derived from the feed’s URL + title + published date. |
| **Confidence** | Softmax probability score the LightReviewer returns for its *top* classification (topic/tag) – a value in **[0, 1]**. |
| **LightReviewer** | Model `Qwen‑2‑0.5B` served via vLLM (CPU‑friendly, ~0.2 s per feed). |
| **HeavyReviewer** | Model `Qwen3‑4B‑Thinking‑2507` served via vLLM (GPU‑or‑CPU, ~0.9 s per feed). |
| **AI Overseer** | Orchestrator that coordinates feed ingestion, deduplication, collection building, and scheduling. |
| **Reviewer Dashboard** | UI page under **/dashboard/reviewer** showing stats, configuration, and control buttons. |

---

## 3. Functional Requirements  

### 3.1 Deduplication (AI Overseer)

| FR‑ID | Requirement |
|-------|-------------|
| **FR‑DUP‑01** | When a new RSS item arrives, compute its *fingerprint* = `SHA256(source_url + "|" + title + "|" + published_iso)`. |
| **FR‑DUP‑02** | Store the fingerprint in a Redis **SET** named `reviewer:fingerprints`. TTL = **30 days** (configurable). |
| **FR‑DUP‑03** | If the fingerprint already exists, **drop** the item and log `duplicate_feed` with the feed id. |
| **FR‑DUP‑04** | Provide an API endpoint `GET /api/overseer/duplicates?since=ISO8601` that returns the count of duplicates filtered in the last 24 h (for metrics). |
| **FR‑DUP‑05** | Add a “Deduplication” toggle on the **AI Overseer Settings** page (enabled by default). When disabled, all feeds bypass the fingerprint check. |

### 3.2 Two‑Tier Review Flow

| FR‑ID | Requirement |
|-------|-------------|
| **FR‑TR‑01** | **LightReviewer Service** runs under the Docker service name `light-reviewer`. It exposes a JSON‑RPC endpoint `POST /review` that returns: `{ tags: [...], summary: "...", confidence: 0.xx }`. |
| **FR‑TR‑02** | **HeavyReviewer Service** runs under Docker name `heavy-reviewer`. Same request schema; outputs the same fields (tags, summary, confidence). |
| **FR‑TR‑03** | The **Reviewer Orchestrator** (a tiny Python wrapper) implements the following pipeline for each feed: <br>1. Submit to LightReviewer. <br>2. If `confidence >= CONF_THR` → store LightReviewer results directly. <br>3. If `confidence < CONF_THR` → forward the same feed to HeavyReviewer, store HeavyReviewer results (overwrites LightReviewer output). |
| **FR‑TR‑04** | `CONF_THR` (confidence threshold) is a **runtime configuration** stored in Redis key `reviewer:conf_threshold` (default 0.85). |
| **FR‑TR‑05** | The two‑tier flow must be **transactional** – a feed must be stored only once, with a `reviewer_type` flag (`light` or `heavy`). |
| **FR‑TR‑06** | Provide a **fallback**: if HeavyReviewer fails (timeout or error) after 3 retries, the system stores the LightReviewer output and marks `fallback: true`. |
| **FR‑TR‑07** | A **health‑check** endpoint `GET /health` for each reviewer returns `{status:"ok", model:"Qwen‑2‑0.5B", avg_latency_ms: xxx}` or `{model:"Qwen3‑4B‑Thinking‑2507", …}`. |

### 3.3 Reviewer Dashboard Enhancements

| FR‑ID | Requirement |
|-------|-------------|
| **FR‑DB‑01** | Add a **“Profiling Stats”** section that shows real‑time aggregates (last 5 min, last 1 h): <br>• Total feeds processed (light / heavy) <br>• Average latency (ms) per reviewer <br>• Success / error rate <br>• Confidence distribution histogram (0‑1 bucketed at 0.05) |
| **FR‑DB‑02** | Add **Configuration Controls**: <br>• Slider / input for **Confidence Threshold** (0.00‑1.00, step 0.01). <br>• Toggle for **Enable HeavyReviewer** (on/off). <br>• Dropdown to select **LightReviewer Model** (future‑proof – currently only Qwen‑2‑0.5B). <br>• Dropdown to select **HeavyReviewer Model** (currently only Qwen3‑4B‑Thinking‑2507). |
| **FR‑DB‑03** | Add **Worker Management**: <br>• “Scale LightReviewer Workers” numeric input (min 1, max 4). <br>• “Restart LightReviewer Workers” button (issues a Docker Compose `scale` command). |
| **FR‑DB‑04** | Show **Current Queue Length** (Redis list `reviewer:queue`) and **Back‑pressure indicator** (red when > 50). |
| **FR‑DB‑05** | Persist any configuration change to Redis keys: <br>`reviewer:conf_threshold`, `reviewer:light_model`, `reviewer:heavy_model`, `reviewer:light_workers`. |
| **FR‑DB‑06** | When a configuration change is made, display a non‑blocking toast: “Configuration saved – changes will apply to new feeds within 30 s”. |

---

## 4. Non‑Functional Requirements  

| NFR‑ID | Requirement |
|--------|-------------|
| **NFR‑PERF‑01** | LightReviewer average latency ≤ 250 ms per feed (CPU‑only). |
| **NFR‑PERF‑02** | HeavyReviewer average latency ≤ 1 200 ms per feed (GPU preferred; CPU fallback must not exceed 2 s). |
| **NFR‑SCAL‑01** | System must support **2 concurrent LightReviewer workers** out‑of‑the‑box; scaling beyond 2 should be possible via the Dashboard (max 4). |
| **NFR‑RES‑01** | Memory usage per LightReviewer container ≤ 4 GiB. HeavyReviewer ≤ 12 GiB. |
| **NFR‑REL‑01** | Zero‑downtime rollout: new containers are started, health‑checked, then traffic is switched (Blue‑Green style). |
| **NFR‑MON‑01** | All new metrics (latency, queue length, duplicate count) must be exported to Prometheus with the prefix `reviewer_`. |
| **NFR‑SEC‑01** | Fingerprint store (`reviewer:fingerprints`) is write‑only for the Overseer; only Admin role may read via API. |
| **NFR‑AV‑01** | All Docker images must be signed and scanned for CVEs (using Trivy). |

---

## 5. Architecture & Data Flow  

### 5.1 Updated Component Diagram (textual)

```
[RSS Sources] → (Fetcher) → [AI Overseer] 
       │
       ├─► Deduplication (Redis SET)
       │       (drop duplicates)
       ▼
   Queue: reviewer:queue (Redis LIST)
       │
       ├─► LightReviewer Service (vLLM, Qwen‑2‑0.5B)  (2 workers)
       │        │
       │        ├─► confidence >= 0.85 ? ──► Store result (flag: light)
       │        │
       │        └─► confidence < 0.85 ──► HeavyReviewer Service (vLLM, Qwen3‑4B‑Thinking‑2507)
       │                               │
       │                               └─► Store result (flag: heavy, overwrite light)
       ▼
   Persistent Store (PostgreSQL)
       │
   → Collections → Presenter → Writer → Editor → VibeVoice → Podcast
```

### 5.2 Service Definitions (Docker‑Compose snippet)

```yaml
services:
  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
    command: ["redis-server", "--save", "60", "1"]

  light-reviewer:
    image: ghcr.io/vllm/vllm:latest
    deploy:
      resources:
        limits:
          cpus: "2"
          memory: "4G"
    environment:
      - MODEL_NAME=Qwen2-0.5B
      - PORT=8000
    ports: ["8001:8000"]
    depends_on: [redis]

  heavy-reviewer:
    image: ghcr.io/vllm/vllm:latest
    deploy:
      resources:
        limits:
          cpus: "4"
          memory: "12G"
    environment:
      - MODEL_NAME=Qwen3-4B-Thinking-2507
      - PORT=8000
    ports: ["8002:8000"]
    depends_on: [redis]

  reviewer-orchestrator:
    build: ./reviewer_orchestrator
    environment:
      - REDIS_URL=redis://redis:6379
      - LIGHT_REVIEWER_URL=http://light-reviewer:8000
      - HEAVY_REVIEWER_URL=http://heavy-reviewer:8000
    depends_on: [light-reviewer, heavy-reviewer]

  ai-overseer:
    build: ./ai_overseer
    environment:
      - REDIS_URL=redis://redis:6379
      - DEDUP_TTL=2592000   # 30 days
    depends_on: [redis, reviewer-orchestrator]
```

*Scaling the LightReviewer workers*: `docker compose up --scale light-reviewer=2` (exposed via Dashboard API).

---

## 6. API Contracts  

### 6.1 Reviewer Service (`/review`)

**Request** (JSON)

```json
{
  "feed_id": "string",
  "title": "string",
  "url": "string",
  "content": "string",
  "published": "2025-09-26T12:34:56Z"
}
```

**Response – LightReviewer**

```json
{
  "tags": ["Finance", "Markets"],
  "summary": "The S&P 500 rose 0.8% ...",
  "confidence": 0.73,
  "model": "Qwen2-0.5B"
}
```

**Response – HeavyReviewer**

Same shape, but `confidence` is *not* used for routing (the heavy model is assumed high‑quality). `model` field = `"Qwen3-4B-Thinking-2507"`.

### 6.2 Overseer Deduplication Endpoint

`GET /api/overseer/duplicates?since=2025-09-25T00:00:00Z`

**Response**

```json
{
  "since": "2025-09-25T00:00:00Z",
  "duplicate_count": 124,
  "unique_processed": 782
}
```

### 6.3 Reviewer Dashboard Config API

| Method | Path | Body | Description |
|--------|------|------|-------------|
| `GET` | `/api/reviewer/config` | — | Returns JSON with current config (`conf_threshold`, `light_workers`, `heavy_enabled`, model names). |
| `PUT` | `/api/reviewer/config` | `{ "conf_threshold":0.88, "light_workers":3, "heavy_enabled":true }` | Persists changes to Redis and triggers scaling actions. |
| `GET` | `/api/reviewer/metrics` | — | Returns profiling aggregates for the UI (latency, queue length, confidence histogram). |
| `POST` | `/api/reviewer/scale/light` | `{ "workers":2 }` | Wrapper that calls `docker compose up --scale light-reviewer=2`. |

All endpoints are protected by JWT‑based admin role (same auth used for other dashboard pages).

---

## 7. UI – Reviewer Dashboard (text description)

The page is split into three vertical panels:

1. **Top Bar** – “Reviewer Settings” button opens a modal with the *Configuration Controls* (confidence threshold slider, heavy‑reviewer toggle, model selectors, worker count). Saves via `/api/reviewer/config`.

2. **Middle Section – Profiling Stats**  
   - **Cards** (row of 4):  
     - **Feeds Processed**: `Light 1,845 | Heavy 312` (live count).  
     - **Avg Latency**: `Light 180 ms | Heavy 960 ms`.  
     - **Confidence Histogram** – simple textual bucket display: `0‑0.2: 5% | 0.2‑0.4: 12% … 0.8‑1.0: 38%`.  
     - **Queue Length**: `78 (⚠️ high)` – color changes based on thresholds.  
   - **Refresh** button (polls `/api/reviewer/metrics` every 15 s).

3. **Bottom Section – Actions Log** (scrollable textarea) showing timestamps for:  
   - “Feed #12345 sent to LightReviewer”.  
   - “Confidence 0.71 → forwarding to HeavyReviewer”.  
   - “HeavyReviewer result stored (feed #12345)”.  
   - “Duplicate filtered (feed #11998)”.  

A **“Restart Workers”** button at the very bottom triggers a graceful restart of both reviewer services (calls Docker API via backend).

---

## 8. Data Persistence  

| Table / Key | Columns / Fields | Owner |
|-------------|------------------|-------|
| `feeds` (PostgreSQL) | `id PK`, `title`, `url`, `published`, `fingerprint`, `reviewer_type ('light'|'heavy')`, `tags JSONB`, `summary TEXT`, `confidence FLOAT`, `processed_at TIMESTAMP` | Reviewer Orchestrator |
| Redis SET `reviewer:fingerprints` | SHA‑256 hash values (TTL configurable) | AI Overseer |
| Redis LIST `reviewer:queue` | Feed JSON payloads awaiting review | AI Overseer → Reviewer Orchestrator |
| Redis HASH `reviewer:config` | `conf_threshold`, `light_model`, `heavy_model`, `light_workers`, `heavy_enabled` | Reviewer Dashboard (reads/writes) |

---

## 9. Acceptance Criteria  

| # | Test | Expected Result |
|---|------|-----------------|
| **AC‑01** | Push 100 distinct feeds + 20 exact duplicates through the Overseer. | 100 feeds processed, 20 logs show `duplicate_feed`. No duplicate rows in `feeds` table. |
| **AC‑02** | Set confidence threshold to 0.90. Feed a batch where LightReviewer returns confidence 0.73, 0.86, 0.94. | Only the 0.73 feed is forwarded to HeavyReviewer; final stored rows have `reviewer_type='heavy'` for that feed, `light` for the others. |
| **AC‑03** | Enable “HeavyReviewer” toggle off. | All feeds are stored as `light` regardless of confidence; HeavyReviewer containers stay idle. |
| **AC‑04** | Scale LightReviewer workers to 2 via Dashboard. | Redis queue consumption rate roughly doubles; UI reflects “Workers: 2”. |
| **AC‑05** | Simulate HeavyReviewer latency 2 s (artificial sleep). Verify orchestrator still stores result within 5 s total (including fallback). | System logs “fallback: false”, total latency ≈ 2 s; no timeout error. |
| **AC‑06** | Load test: 500 feeds/minute for 5 min. Verify: < 5% feeds are dropped due to queue overflow, all profiling metrics stay within thresholds, no duplicate entry appears. |
| **AC‑07** | Verify Prometheus metrics: `reviewer_light_latency_seconds`, `reviewer_heavy_latency_seconds`, `reviewer_queue_length`, `reviewer_duplicate_total`. | Metrics scraped and visible in Grafana dashboard. |
| **AC‑08** | UI – Change confidence threshold and worker count, then submit a new feed. Confirm that the new settings apply (feed routed according to new threshold). | Immediate effect without service restart. |

---

## 10. Testing Strategy  

1. **Unit Tests** – Python modules for:
   - Fingerprint generation (`test_fingerprint.py`).  
   - Threshold logic (`test_confidence_routing.py`).  
   - Config read/write (`test_config_redis.py`).  

2. **Integration Tests** (Docker Compose):
   - Spin up full stack, push a synthetic feed batch, assert DB rows and logs (using `pytest-docker`).  
   - Simulate duplicate feed (same fingerprint) – verify drop.  

3. **Load / Stress Tests**:
   - Use `locust` or `k6` to generate 500 feeds/minute.  
   - Capture latency, queue growth, error rates.  

4. **UI Tests**:
   - Selenium (or Playwright) to interact with Reviewer Dashboard: change threshold, scale workers, verify API calls made.  

5. **Security Review**:
   - Ensure the Admin JWT cannot be forged.  
   - Verify Redis SET cannot be read from the public network.  

---

## 11. Migration / Roll‑out Plan  

| Phase | Action |
|-------|--------|
| **0 – Prep** | Add new Redis keys, update `docker-compose.yml` with `light-reviewer` and `heavy-reviewer`. |
| **1 – Deploy LightReviewer** | Start `light-reviewer` (2 replicas). Verify health endpoint, feed a few items, ensure DB rows have `reviewer_type='light'`. |
| **2 – Enable Deduplication** | Turn on `dedup_enabled` flag, monitor duplicate logs in staging. |
| **3 – Deploy HeavyReviewer** | Add `heavy-reviewer` service, set `heavy_enabled=true` in config. |
| **4 – Activate Two‑Tier Routing** | Set `conf_threshold=0.85`. Run a mixed batch to confirm heavy routing. |
| **5 – Dashboard Release** | Push new Reviewer Dashboard UI, enable admin access, run UI acceptance tests. |
| **6 – Scale Workers** | Use Dashboard to increase LightReviewer workers to 2; verify queue consumption rises. |
| **7 – Production Cut‑over** | Switch DNS / load‑balancer to the new stack, keep old services running for 24 h as fallback. |
| **8 – Monitoring** | Observe Prometheus alerts for latency, queue length, duplicate count. Adjust `conf_threshold` if heavy reviewer overloads. |
| **9 – Documentation** | Update README, architecture diagram (textual), and operational runbooks. |

Rollback: stop `heavy-reviewer`, set `heavy_enabled=false`, keep LightReviewer running – system continues with lower quality but still functional.

---

## 12. Open Issues & Future Enhancements  

| ID | Issue | Proposed Solution |
|----|-------|--------------------|
| **UI‑001** | Visual histogram for confidence currently textual. | Add a canvas‑based bar chart in a later UI iteration. |
| **CONFIG‑002** | Model version upgrades should be hot‑swappable. | Store model name in Redis; reviewer containers read on start‑up; implement rolling restart via Dashboard. |
| **SCALING‑003** | Auto‑scale based on queue length (beyond manual button). | Future work: integrate with Kubernetes HPA or Docker Swarm auto‑scale scripts. |
| **SEC‑004** | Fingerprint TTL may need per‑source customization. | Add a `source_ttl` map in config; adjust `expire` command per source when adding fingerprint. |

---

## 13. References  

* **vLLM Documentation** – https://docs.vllm.ai/en/latest/  
* **Qwen‑2‑0.5B Model Card** – https://huggingface.co/Qwen/Qwen2-0.5B  
* **Qwen3‑4B‑Thinking‑2507 Model Card** – https://huggingface.co/Qwen/Qwen3-4B-Thinking-2507  
* **Redis SET & TTL** – https://redis.io/docs/data-types/sets/  
* **Prometheus Naming Conventions** – https://prometheus.io/docs/practices/naming/  

---  

**End of Specification**.  



Feel free to ask for any clarification or for a more detailed implementation plan for a particular component.