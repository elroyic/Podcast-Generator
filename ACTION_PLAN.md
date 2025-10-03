# Action Plan - Critical Fixes & Enhancements
**Branch Review Completion Date:** September 30, 2025  
**Priority:** Immediate Implementation Required

---

## 🔴 CRITICAL FIXES (Must Do Before Production)

### Fix 1: Integrate Editor Service
**Severity:** HIGH  
**Effort:** 2-3 hours  
**Files to Modify:**
- `/workspace/services/ai-overseer/app/services.py`

**Current Code (Line ~150-200):**
```python
# In EpisodeGenerationService.generate_episode()
async def generate_episode(self, group_id: UUID, db: Session):
    # ... collection ready ...
    
    # Generate script
    script = await self.text_generation_service.generate_script(
        collection_data, group
    )
    
    # Store script
    episode.script = script
    db.commit()
    
    # [MISSING: Editor review step]
    
    # Generate audio
    audio_result = await self.presenter_service.generate_audio(
        episode.id, script, presenter_ids
    )
```

**Required Fix:**
```python
# In EpisodeGenerationService.generate_episode()
async def generate_episode(self, group_id: UUID, db: Session):
    # ... collection ready ...
    
    # Generate script
    script = await self.text_generation_service.generate_script(
        collection_data, group
    )
    
    # Store script
    episode.script = script
    db.commit()
    
    # ✅ ADD EDITOR REVIEW HERE
    try:
        editor_result = await self.editor_service.review_script(
            script=script,
            collection_id=str(collection.id),
            group_id=str(group.id)
        )
        
        # Update script with editor's version
        episode.script = editor_result.get('edited_script', script)
        episode.editor_notes = editor_result.get('notes', '')
        db.commit()
        
        logger.info(f"Editor review completed for episode {episode.id}")
    except Exception as e:
        logger.warning(f"Editor review failed, using original script: {e}")
        # Continue with original script on editor failure
    
    # Generate audio with edited script
    audio_result = await self.presenter_service.generate_audio(
        episode.id, episode.script, presenter_ids
    )
```

**New Method to Add (ai-overseer/app/services.py):**
```python
class EditorService:
    """Service for script editing and review."""
    
    def __init__(self):
        self.editor_url = os.getenv("EDITOR_URL", "http://editor:8009")
    
    async def review_script(
        self,
        script: str,
        collection_id: str,
        group_id: str
    ) -> Dict[str, Any]:
        """Send script to editor service for review."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.editor_url}/review-script",
                json={
                    "script": script,
                    "collection_id": collection_id,
                    "group_id": group_id
                }
            )
            response.raise_for_status()
            return response.json()
```

**Database Migration (if needed):**
```python
# Add to Episode model in shared/models.py
editor_notes = Column(Text, nullable=True)
```

---

### Fix 2: Episode Generation Locking
**Severity:** HIGH  
**Effort:** 1-2 hours  
**Files to Modify:**
- `/workspace/services/ai-overseer/app/tasks.py`
- `/workspace/services/ai-overseer/main.py`

**Current Code:**
```python
# In ai-overseer/main.py
@app.post("/generate-episode")
async def generate_episode(request: GenerationRequest, db: Session = Depends(get_db)):
    # Check if group exists
    group = db.query(PodcastGroup).filter(...).first()
    
    # Queue the task (no lock)
    task = generate_episode_for_group.delay(str(request.group_id))
    
    return GenerationResponse(...)
```

**Required Fix:**
```python
# In ai-overseer/main.py
import redis

# Initialize Redis client
redis_client = redis.Redis.from_url(
    os.getenv("REDIS_URL", "redis://redis:6379/0"),
    decode_responses=True
)

@app.post("/generate-episode")
async def generate_episode(request: GenerationRequest, db: Session = Depends(get_db)):
    # Check if group exists
    group = db.query(PodcastGroup).filter(...).first()
    if not group:
        raise HTTPException(404, "Group not found")
    
    # ✅ CHECK FOR EXISTING LOCK
    lock_key = f"episode_generation_lock:{request.group_id}"
    
    # Try to acquire lock (NX = only if not exists, EX = expiry in seconds)
    lock_acquired = redis_client.set(
        lock_key, 
        "1", 
        nx=True,  # Only set if not exists
        ex=3600   # Expire in 1 hour
    )
    
    if not lock_acquired:
        # Check lock age
        ttl = redis_client.ttl(lock_key)
        raise HTTPException(
            status_code=409,
            detail=f"Episode generation already in progress for this group. Retry in {ttl} seconds."
        )
    
    try:
        # Queue the task
        task = generate_episode_for_group.delay(str(request.group_id))
        
        logger.info(f"Queued episode generation for group {request.group_id} (task: {task.id})")
        
        return GenerationResponse(
            episode_id=str(request.group_id),
            status="queued",
            message=f"Episode generation queued with task ID: {task.id}"
        )
    except Exception as e:
        # Release lock on error
        redis_client.delete(lock_key)
        raise
```

**Celery Task Update:**
```python
# In ai-overseer/app/tasks.py
@celery.task(bind=True)
def generate_episode_for_group(self, group_id: str):
    lock_key = f"episode_generation_lock:{group_id}"
    
    try:
        # Generate episode
        result = episode_generation_service.generate_episode(...)
        
        # Success - release lock
        redis_client.delete(lock_key)
        
        return result
        
    except Exception as e:
        # Error - release lock
        redis_client.delete(lock_key)
        logger.error(f"Episode generation failed for group {group_id}: {e}")
        raise
```

---

### Fix 3: AudioFile DB Persistence
**Severity:** MEDIUM  
**Effort:** 1 hour  
**Files to Modify:**
- `/workspace/services/presenter/main.py`

**Current Code (Line ~200-250):**
```python
# In presenter/main.py
@app.post("/generate-audio")
async def generate_audio(request: AudioGenerationRequest, db: Session = Depends(get_db)):
    # ... generate audio ...
    
    # Save audio file
    audio_path = f"/app/storage/episodes/{episode_id}/audio.mp3"
    await save_audio_file(combined_audio, audio_path)
    
    # [MISSING: Create AudioFile DB record]
    
    return {
        "status": "success",
        "audio_url": audio_path,
        "episode_id": str(episode_id)
    }
```

**Required Fix:**
```python
# In presenter/main.py
from shared.models import AudioFile
import os

@app.post("/generate-audio")
async def generate_audio(request: AudioGenerationRequest, db: Session = Depends(get_db)):
    # ... generate audio ...
    
    # Save audio file
    audio_path = f"/app/storage/episodes/{episode_id}/audio.mp3"
    await save_audio_file(combined_audio, audio_path)
    
    # ✅ CREATE AUDIOFILE DB RECORD
    try:
        # Get file size
        file_size = os.path.getsize(audio_path)
        
        # Calculate duration (if pydub is available)
        duration_seconds = None
        try:
            from pydub import AudioSegment
            audio = AudioSegment.from_mp3(audio_path)
            duration_seconds = len(audio) / 1000.0  # Convert ms to seconds
        except Exception:
            logger.warning("Could not calculate audio duration")
        
        # Create AudioFile record
        audio_file = AudioFile(
            episode_id=episode_id,
            url=f"file://{audio_path}",  # Local file URL
            file_size=file_size,
            duration_seconds=duration_seconds,
            format="mp3",
            created_at=datetime.utcnow()
        )
        
        db.add(audio_file)
        db.commit()
        db.refresh(audio_file)
        
        logger.info(f"Created AudioFile record for episode {episode_id}")
        
        return {
            "status": "success",
            "audio_url": audio_path,
            "audio_file_id": str(audio_file.id),
            "episode_id": str(episode_id),
            "duration_seconds": duration_seconds
        }
        
    except Exception as e:
        logger.error(f"Failed to create AudioFile record: {e}")
        # Don't fail the request, but log the error
        return {
            "status": "success",
            "audio_url": audio_path,
            "episode_id": str(episode_id),
            "warning": f"AudioFile DB record not created: {str(e)}"
        }
```

---

## 🟡 HIGH PRIORITY ENHANCEMENTS (This Week)

### Enhancement 1: Collection Min Feeds Validation
**Effort:** 30 minutes  
**File:** `/workspace/services/ai-overseer/app/services.py`

```python
# In EpisodeGenerationService.generate_episode()
MIN_FEEDS_REQUIRED = int(os.getenv("MIN_FEEDS_PER_COLLECTION", "3"))

# Before sending to Writer
article_count = len(collection.articles)
if article_count < MIN_FEEDS_REQUIRED:
    logger.warning(
        f"Collection {collection.id} has only {article_count} articles "
        f"(minimum: {MIN_FEEDS_REQUIRED}). Skipping episode generation."
    )
    
    # Update episode status to skipped
    episode.status = EpisodeStatus.SKIPPED
    episode.skip_reason = f"Insufficient articles: {article_count}/{MIN_FEEDS_REQUIRED}"
    db.commit()
    
    raise HTTPException(
        400, 
        f"Collection must have at least {MIN_FEEDS_REQUIRED} articles"
    )
```

---

### Enhancement 2: Deploy Prometheus + Grafana
**Effort:** 2-3 hours  
**Files to Create/Modify:**
- `/workspace/docker-compose.yml` (add services)
- `/workspace/prometheus.yml` (config)
- `/workspace/grafana-dashboards/` (dashboards)

**Add to docker-compose.yml:**
```yaml
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
    depends_on:
      - reviewer

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana-dashboards:/etc/grafana/provisioning/dashboards
    depends_on:
      - prometheus

volumes:
  # ... existing volumes ...
  prometheus_data:
  grafana_data:
```

**Create prometheus.yml:**
```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'reviewer'
    static_configs:
      - targets: ['reviewer:8013']
    metrics_path: '/metrics/prometheus'
  
  # Add other services as they implement metrics endpoints
```

---

### Enhancement 3: End-to-End Workflow Test
**Effort:** 3-4 hours  
**File to Create:** `/workspace/tests/test_complete_workflow.py`

```python
"""
Complete end-to-end workflow test.
Tests: RSS → Review → Collection → Script → [Editor] → Audio → Publish
"""
import asyncio
import httpx
import pytest
from uuid import uuid4

BASE_URL = "http://localhost:8000"

@pytest.mark.asyncio
async def test_complete_workflow():
    """Test complete podcast generation workflow."""
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        # Step 1: Create a news feed
        feed_response = await client.post(
            f"{BASE_URL}/api/news-feeds",
            json={
                "name": "Test Feed",
                "source_url": "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
                "is_active": True
            }
        )
        assert feed_response.status_code == 200
        feed_id = feed_response.json()["id"]
        
        # Step 2: Refresh feed to get articles
        refresh_response = await client.post(
            f"{BASE_URL}/api/news-feed/refresh/{feed_id}"
        )
        assert refresh_response.status_code == 200
        assert refresh_response.json()["entries_processed"] > 0
        
        # Step 3: Send articles to reviewer
        review_response = await client.post(
            f"{BASE_URL}/api/news-feed/send-to-reviewer"
        )
        assert review_response.status_code == 200
        
        # Wait for reviews to process
        await asyncio.sleep(10)
        
        # Step 4: Create podcast group
        group_response = await client.post(
            f"{BASE_URL}/api/podcast-groups",
            json={
                "name": "Test Group",
                "category": "Technology",
                "language": "en",
                "schedule": "daily",
                "presenter_ids": [],  # Will need to create presenters
                "writer_id": None,  # Will need to create writer
                "news_feed_ids": [feed_id]
            }
        )
        assert group_response.status_code == 200
        group_id = group_response.json()["id"]
        
        # Step 5: Generate episode
        episode_response = await client.post(
            f"{BASE_URL}/api/generate-episode",
            json={"group_id": group_id}
        )
        assert episode_response.status_code == 200
        
        # Step 6: Wait for generation to complete
        await asyncio.sleep(120)  # 2 minutes
        
        # Step 7: Verify episode exists
        episodes_response = await client.get(
            f"{BASE_URL}/api/episodes?group_id={group_id}"
        )
        assert episodes_response.status_code == 200
        episodes = episodes_response.json()
        assert len(episodes) > 0
        
        # Step 8: Verify audio file exists
        episode = episodes[0]
        audio_check = await client.head(
            f"{BASE_URL}/api/episodes/{episode['id']}/download"
        )
        assert audio_check.status_code == 200
        
        print("✅ Complete workflow test PASSED")

if __name__ == "__main__":
    asyncio.run(test_complete_workflow())
```

---

## 🟢 MEDIUM PRIORITY (This Month)

### 1. Cadence Status UI Indicators
**File:** `/workspace/services/api-gateway/templates/dashboard.html`

Add to dashboard:
```html
<div class="cadence-status">
    <h3>Podcast Group Cadence Status</h3>
    <div id="cadence-list">
        <!-- Populated via JS -->
    </div>
</div>

<script>
async function loadCadenceStatus() {
    const response = await fetch('/api/cadence/status');
    const data = await response.json();
    
    const listEl = document.getElementById('cadence-list');
    listEl.innerHTML = data.groups.map(g => `
        <div class="cadence-item">
            <span>${g.name}</span>
            <span class="badge ${g.cadence}">${g.cadence}</span>
            ${g.skip_reason ? `<span class="skip-reason">${g.skip_reason}</span>` : ''}
        </div>
    `).join('');
}

setInterval(loadCadenceStatus, 60000);  // Refresh every minute
loadCadenceStatus();
</script>
```

---

### 2. Presenter Brief Generation
**File:** `/workspace/services/ai-overseer/app/services.py`

```python
async def generate_presenter_briefs(
    self,
    collection: Collection,
    presenters: List[Presenter]
) -> Dict[str, str]:
    """Generate 1000-word briefs for each presenter."""
    
    briefs = {}
    
    for presenter in presenters:
        # Create prompt for presenter brief
        prompt = f"""
        You are {presenter.name}, a podcast presenter with this persona:
        {presenter.persona}
        
        Review this collection of articles and provide a 1000-word brief 
        on your perspective and key points to discuss:
        
        Articles:
        {self._format_collection_for_brief(collection)}
        
        Brief (1000 words):
        """
        
        # Call LLM to generate brief
        brief = await self.text_generation_service.generate_text(
            prompt=prompt,
            max_tokens=1200
        )
        
        briefs[str(presenter.id)] = brief
    
    return briefs
```

---

## 🔵 LOW PRIORITY (Future Releases)

### 1. External Publishing Platforms
- Anchor.fm API integration
- Libsyn API integration
- Spotify for Podcasters API

### 2. OAuth2 Authentication
- Replace JWT with OAuth2
- Add Google/GitHub auth providers
- Multi-user support

### 3. Auto-scaling
- Queue length monitoring
- Automatic worker scaling
- Load balancing

### 4. Multi-voice Sequencing
- Presenter turn-taking
- Voice interruptions
- Conversational flow

---

## Implementation Checklist

### Phase 1: Critical Fixes (Week 1)
- [ ] Integrate Editor service in workflow
- [ ] Add episode generation locking
- [ ] Fix AudioFile DB persistence
- [ ] Add collection min feeds validation
- [ ] Test all fixes end-to-end

### Phase 2: Monitoring (Week 2)
- [ ] Deploy Prometheus
- [ ] Deploy Grafana
- [ ] Create dashboards
- [ ] Set up alerting

### Phase 3: Testing (Week 3)
- [ ] Create end-to-end test suite
- [ ] Run load tests (500 feeds/min)
- [ ] Performance benchmarking
- [ ] Security audit

### Phase 4: Production Readiness (Week 4)
- [ ] Documentation updates
- [ ] Deployment guide
- [ ] Rollback procedures
- [ ] Monitoring runbooks

---

## Success Criteria

### Critical Fixes Complete ✅
- [x] No placeholder code in services
- [ ] Editor integrated in workflow
- [ ] Episode locking prevents duplicates
- [ ] AudioFile records created
- [ ] All tests pass

### Production Ready ✅
- [ ] Prometheus/Grafana deployed
- [ ] End-to-end test passes
- [ ] Load test passes (500 feeds/min)
- [ ] Security audit complete
- [ ] Documentation updated

### Performance Targets ✅
- [x] Light reviewer: ≤250ms
- [x] Heavy reviewer: ≤1200ms
- [ ] Episode generation: <3 minutes
- [ ] 99.9% uptime

---

## Contact & Support

**Review Completed By:** AI Assistant  
**Date:** September 30, 2025  
**Next Review:** After Phase 1 completion

**For Questions:**
- Check `/workspace/IMPLEMENTATION_REVIEW_COMPLETE.md` for details
- See `/workspace/WORKFLOW_STATUS.md` for current state
- Refer to `/workspace/REVIEW_SUMMARY.md` for quick reference

---

**Status:** Ready for implementation 🚀