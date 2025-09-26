## PodCast AI Application – Requirements (LLM Prompt)

### 1. Purpose
Create an automated system that produces complete podcast episodes (≈ 60‑80 min) for a set of **Podcast Groups**.  The system must:
* Gather topical news from RSS/MCP feeds.  
* Generate full episode scripts (title, description, tags, etc.).  
* Convert scripts to spoken audio using a designated voice model.  
* Publish the finished episodes to podcast‑hosting platforms.  

All major functions are implemented as independent services that communicate through well‑defined APIs.

---

### 2. High‑Level Architecture  

| Service | Core Responsibility | Key Interactions |
|---------|---------------------|------------------|
| **News‑Feed Service** | Pull and normalise RSS/MCP feeds → topic pool. | Provides feeds to **AI Overseer**. |
| **AI Overseer** | Central orchestrator; creates & manages **Podcast Groups** and assigns resources. | Calls **News‑Feed**, **Text‑Generation**, **Writer**, **Presenter** services. |
| **Podcast‑Group Service** | Stores metadata for each group (name, category, language, etc.). | Queried/updated by **AI Overseer**. |
| **Writer Service** | Generates episode‑level metadata (title, description, tags, etc.). | Consumes text from **AI Pod Text Generation**; outputs to **Presenter**. |
| **AI Pod Text Generation** | Produces the full episode script (60‑80 min). | Input: assigned news items; Output: raw script for **Writer**. |
| **Presenter Service** | Turns the final script into audio using the VibeVoice‑1.5B model. | Receives completed script from **Writer**. |
| **Publishing Service** | Uploads the final audio + metadata to podcast‑hosting platforms. | Called after **Presenter** finishes. |

All services expose REST/GraphQL endpoints (or message‑queue topics) and store state in a shared database (e.g., PostgreSQL) and a blob store for audio files.

---

### 3. Data Model  

#### 3.1 Podcast Group
| Field | Type | Description |
|-------|------|-------------|
| **id** | UUID | Primary key |
| **name** | string | Human‑readable podcast name |
| **description** | text | Brief overview |
| **category** / **subcategory** | string | Classification |
| **language** | ISO‑639‑1 code |
| **country** | ISO‑3166‑1 alpha‑2 |
| **tags** | array[string] |
| **keywords** | array[string] |
| **presenters** | array[Presenter‑id] (1‑4) |
| **writer** | Writer‑id |
| **schedule** | cron‑like expression (e.g., “every Monday 09:00 UTC”) |
| **status** | enum {active, paused, archived} |

#### 3.2 Presenter (AI Agent)
| Field | Type | Description |
|-------|------|-------------|
| **id** | UUID |
| **name** | string |
| **bio** | text |
| **age** | integer (optional) |
| **gender** | string |
| **demographics** | json |
| **biases** | json (topic‑specific bias weighting) |
| **specialties** | array[string] |
| **expertise** | array[string] |
| **interests** | array[string] |
| **location** | {country, city} |
| **voice_model** | fixed = `microsoft/VibeVoice‑1.5B` (URL for reference) |

#### 3.3 Writer (AI Agent)
| Field | Type | Description |
|-------|------|-------------|
| **id** | UUID |
| **model** | fixed = `Ollama` (running locally) |
| **capabilities** | list of metadata fields it can generate (title, description, tags, …) |

#### 3.4 News Feed
| Field | Type | Description |
|-------|------|-------------|
| **id** | UUID |
| **source_url** | string |
| **type** | enum {RSS, MCP} |
| **last_fetched** | datetime |
| **articles** | array[Article] (title, link, summary, publish_date) |

#### 3.5 Episode (Generated)
| Field | Type | Description |
|-------|------|-------------|
| **id** | UUID |
| **group_id** | PodcastGroup‑id |
| **script** | text |
| **metadata** | {title, description, tags, keywords, category, subcategory, language, country} |
| **audio_url** | string (blob storage) |
| **created_at** | datetime |
| **status** | enum {draft, voiced, published} |

---

### 4. Functional Requirements  

1. **Create / Manage Podcast Groups**  
   * UI or API to add a new group, set schedule, assign presenters, writer, and news‑feed sources.  
   * Ability to edit or deactivate groups.

2. **News‑Feed Integration**  
   * Periodically poll each registered RSS/MCP source.  
   * Normalise articles and store them for later selection.  
   * Expose “available topics” endpoint for the overseer.

3. **AI Overseer Logic**  
   * On each schedule tick, for every **active** Podcast Group:  
     a. Select a relevant subset of news items (topic matching, bias weighting).  
     b. Trigger **AI Pod Text Generation** with selected items.  
     c. Pass generated script to **Writer** for metadata creation.  
     d. Send completed script + metadata to **Presenter**.  
     e. When audio is ready, call **Publishing Service**.  
   * Provide admin endpoints to:  
     - Create/delete groups, feeds, presenters, writers.  
     - Re‑assign resources between groups.  
     - Manually trigger a generation run.

4. **AI Pod Text Generation**  
   * Input: list of news article summaries + group metadata.  
   * Output: full episode script (≈ 60‑80 min reading time) plus optional outlines.  
   * Runs on the same machine as the **Writer** (both use the local Ollama model).

5. **Writer Service**  
   * Consumes raw script, generates episode‑level metadata (title, description, tags, etc.).  
   * Uses the same Ollama model; may fine‑tune prompts per group.

6. **Presenter Service**  
   * Receives final script and metadata.  
   * Calls the **VibeVoice‑1.5B** model to synthesize spoken audio for each presenter in turn (or blended).  
   * Saves the resulting audio file to blob storage and returns a URL.

7. **Publishing Service**  
   * Supports at least two major hosting platforms (e.g., Anchor, Libsyn) via their APIs.  
   * Uploads audio file + metadata, handles authentication, and records the public episode URL.

8. **Scheduling**  
   * Configurable cron‑style schedule per Podcast Group.  
   * System must guarantee that no two generations for the same group overlap.

9. **Observability & Errors**  
   * Log every step (feed fetch, script generation, voice synthesis, publishing).  
   * Expose health‑check endpoints and metrics (processed episodes, failures, latency).  
   * Retry logic for transient failures (e.g., network, API rate limits).

---

### 5. Non‑Functional Requirements  

| Requirement | Target |
|-------------|--------|
| **Scalability** | Horizontal scaling of the **AI Pod Text Generation** and **Presenter** services; queue‑based work distribution. |
| **Reliability** | 99.5 % uptime for the orchestrator; automatic retries; dead‑letter queues for failed jobs. |
| **Performance** | End‑to‑end episode generation ≤ 30 min after schedule trigger (excluding publishing latency). |
| **Security** | API authentication (JWT/OAuth2); secrets stored in vault; least‑privilege IAM for external publishing APIs. |
| **Data Privacy** | No personally identifiable data stored beyond presenter bios; comply with GDPR for EU‑based podcasts. |
| **Maintainability** | Micro‑service codebase, documented OpenAPI specs, unit & integration tests, CI/CD pipelines. |
| **Extensibility** | Plug‑in architecture for additional voice models, new publishing platforms, or alternative news sources. |

---

### 6. User Stories (for quick reference)

| ID | As a … | I want … | So that … |
|----|--------|----------|-----------|
| US‑01 | **Admin** | to create a new Podcast Group with its own schedule and presenters | each group can produce its own themed episodes automatically |
| US‑02 | **Admin** | to add or remove RSS/MCP feeds for a group | the content stays relevant to the group’s topic |
| US‑03 | **System** | to automatically generate a 60‑80 min script from the day’s news | listeners receive fresh, timely episodes |
| US‑04 | **System** | to synthesize the script using VibeVoice‑1.5B | the episode sounds natural and consistent |
| US‑05 | **Admin** | to manually trigger a generation run for any group | I can test changes or produce a special edition on demand |
| US‑06 | **System** | to publish the finished episode to the configured hosting service | the podcast appears on all listeners’ platforms without manual steps |

---

### 7. API Sketch (OpenAPI‑style snippets)

```yaml
# Podcast Group
/podcast-groups:
  get:
    summary: List all groups
  post:
    summary: Create a new group
    requestBody:
      required: true
      content:
        application/json:
          schema: { $ref: '#/components/schemas/PodcastGroup' }

# News Feed
/feeds:
  get:  { summary: List feeds }
  post: { summary: Register new RSS/MCP feed }

# Overseer actions
/overseer/run:
  post:
    summary: Trigger immediate generation for a specific group
    parameters:
      - name: groupId
        in: query
        required: true
        schema: { type: string, format: uuid }

# Publishing
/publish/{episodeId}:
  post:
    summary: Upload episode to external host
```

(Full schema definitions omitted for brevity; expand as needed.)

---

### 8. Deliverables for the LLM Prompt  

- **Cleaned‑up requirements document** (this file).  
- **Entity‑relationship diagram** (based on Section 3).  
- **Sequence diagram** for a typical generation run (Overseer → TextGen → Writer → Presenter → Publishing).  
- **OpenAPI skeleton** (Section 7).  
- **Sample prompts** for the Ollama model (script generation, metadata creation).  

These artifacts can be fed to an LLM to:

1. Generate the micro‑service code stubs.  
2. Produce detailed design documents (deployment, CI/CD).  
3. Write unit/integration tests for each service.  

--- 

