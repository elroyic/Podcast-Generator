## Missing Functionality vs. Docs (as of 2025-09-27)

Scope: Gaps between the documented behavior in Docs/Current and the actual implementation in the codebase and docker-compose.

### Reviewer Enhancements (Docs/Current/ReviewerEnhancement.md)
- Two-tier orchestration via separate `light-reviewer` and `heavy-reviewer` services: Reviewer service currently calls Ollama models directly and does not orchestrate the two external reviewer microservices for production routing.
- Worker scaling from Dashboard: `/api/reviewer/scale/light` only updates config; no actual container scaling is executed.
- Prometheus metrics: No Prometheus exporter/endpoint; metrics are kept in Redis and exposed as JSON, not Prom format.
- Queue-based ingestion: Redis list `reviewer:queue` is referenced in docs but not actively used to pull work; articles are sent directly via HTTP.
- Security on fingerprint store: No role-based restriction or read-only enforcement for Redis `reviewer:fingerprints` (docs specify Admin-only read).

### AI Overseer & Scheduler (Docs/Current/OverseerSchedulerUpdate.md)
- No-overlap guarantee per group: There is no explicit locking/concurrency guard to prevent overlapping episode generations for the same group.
- Cadence status visibility: No UI indicator for Daily/3-Day/Weekly mode or reason for shift; Dashboard surfaces are not implemented for cadence status.

### Presenter (Persona) and Editor Flow (Docs/Current/README_COMPLETE_SYSTEM.md, Workflow.md)
- Presenter persona features (1000-word briefs, 500-word feedback) are not integrated in the active pipeline; relevant endpoints exist only in presenter archives.
- Editor service is not invoked in the active episode generation flow; script editing/polish step is missing from `ai-overseer` main pipeline.

### Script Generation Ownership (Docs/Current/README_COMPLETE_SYSTEM.md)
- Docs state Writer generates scripts (Qwen3). Current pipeline uses `text-generation` service for scripts and Writer only for metadata. Misaligned responsibility and missing Writer-as-script-generator integration in the active path.

### Publishing & Local Hosting (Docs/Current/Local-Hosting.md)
- AI Overseer still attempts publishing with platform `"anchor"` and empty credentials; not wired to documented local platforms (`local_podcast_host`, `local_rss_feed`, `local_directory`).
- Audio file DB record is not created/synced in the generation flow. Presenter returns an audio path, but no `AudioFile` row is persisted, which breaks publishing assumptions.

### API Gateway Dashboard (Docs/Current/ReviewerEnhancement.md)
- Reviewer Dashboard scaling action: UI writes desired worker count to config but no process applies Docker scaling.
- Confidence histogram buckets in UI expect labels like `0.00-0.20`, while backend returns bucketed keys in a different format; visualization may not reflect real counts.

### Observability & Security (Docs/Current/Requirements.md)
- Prometheus/Grafana integration absent; no Prom-style metrics endpoints across services.
- AuthN/AuthZ (JWT/OAuth2) not implemented on admin/dashboard APIs; endpoints are unauthenticated.

### Scheduling & Workflow Constraints (Docs/Current/Requirements.md)
- “No two generations for the same group overlap” not enforced (no locks/semaphores/DB flags in active path).

### Testing & Tooling (Docs/Current/README_COMPLETE_SYSTEM.md)
- `test_complete_workflow.py` referenced in docs is not present; `/test-complete-workflow` endpoint exists only in an archived overseer module, not in the active service.

### Miscellaneous Alignment Issues
- VibeVoice real integration (HF `microsoft/VibeVoice-1.5B`) is not used in active presenter path; current presenter synthesizes MP3s via pydub (archives contain VibeVoice variants).
- Multi-presenter/voice sequencing is not implemented in active presenter path (single combined output only).
- Deduplication TTL/config: Implemented in News Feed via Redis, but AI Overseer env configuration for thresholds (e.g., `MIN_FEEDS_THRESHOLD`) is not surfaced in compose; defaults are relied upon.
- Workflow docs still mention “no more than 1 release per day”; Overseer implements adaptive cadence (daily/3-day/weekly). Documentation across files is inconsistent and needs consolidation.

---

If you want, we can convert each gap into actionable tickets (owner, acceptance criteria, estimate) and update the relevant Docs pages with “Current State” vs “Target State.”


