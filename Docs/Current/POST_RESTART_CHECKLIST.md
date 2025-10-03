# Post-Restart Checklist

## After Restarting Docker Desktop

### 1. Verify All Services Are Running
```bash
cd "g:\AI Projects\Podcast Generator"
docker compose ps
```

Expected: All services should be "Up" and "healthy"

---

### 2. Check Ollama Health
```bash
curl http://localhost:11434/api/tags
```

Expected: Should return list of models (qwen3:latest)

If Ollama is slow or unresponsive:
```bash
docker compose restart ollama
```

---

### 3. Quick Collection Status Check
```bash
curl http://localhost:8014/collections/group/9a056646-586b-4d87-a75b-6dea46e6a768/active
```

Expected result should show:
- Collection with articles (not 0)
- Status: "ready" or "building" with content

If still showing empty collection (388d2882...):
- This is the database cleanup issue mentioned in summary
- Can work around by specifying `collection_id` in requests

---

### 4. Test Multi-Speaker Audio Generation (Quick Win!)
```bash
curl -X POST http://localhost:8004/generate-audio \
  -H "Content-Type: application/json" \
  -d "{\"episode_id\": \"test-multi\", \"script\": \"Speaker 1: Welcome to the show!\nSpeaker 2: Thanks for having me!\nSpeaker 1: Let's dive in!\"}"
```

Expected: Audio file generated with 2 different voices

Check result:
```bash
curl http://localhost:8004/episodes/test-multi/audio
```

---

### 5. Full Podcast Generation Test

Use a ready collection with the new multi-speaker workflow:

```python
# Save as test_final_podcast.py
import httpx

response = httpx.post(
    "http://localhost:8012/generate-episode",
    json={
        "group_id": "9a056646-586b-4d87-a75b-6dea46e6a768",
        "collection_id": "0869ad90-e824-423e-8d8d-8076802fd910",  # Government Shutdown collection
        "force_regenerate": True
    },
    timeout=30.0
)

print(response.json())
```

Then monitor:
```bash
docker compose logs -f celery-worker
```

---

### 6. If Issues Persist

#### Presenter Service Not Picking Up Changes:
```bash
docker cp services/presenter/main.py podcastgenerator-presenter-1:/app/main.py
docker compose restart presenter
```

#### Collections Service Cache Issue:
```bash
docker compose restart collections ai-overseer celery-worker
```

#### Complete Rebuild (Last Resort):
```bash
docker compose down
docker compose build --no-cache writer editor presenter
docker compose up -d
```

---

## Expected Outcome

After restart, you should be able to:

1. ✅ Generate multi-speaker scripts (Speaker 1, Speaker 2, etc.)
2. ✅ Edit scripts while preserving speaker labels
3. ✅ Generate audio with different voices per speaker
4. ✅ Complete end-to-end podcast generation from ready collection

---

## Known Pending Issue

**Empty Collection in Database:**
- Collection `388d2882-c037-4ad0-a542-300e04992105` (0 articles)
- Assigned to Spring Weather Podcast group
- Blocks automatic collection selection

**Workaround:** Always specify `collection_id` parameter

**Permanent Fix:** Database cleanup or collection expiration logic

---

## Quick Stats

**Files Modified:** 10  
**Services Updated:** 6  
**New Features:** Multi-speaker dialogue, Multi-voice synthesis  
**Bugs Fixed:** 3 (datetime comparison, group filtering, VibeVoice API)  

**Audio Generation Test:** ✅ SUCCESS (5-second clip with proper voice)

---

## Contact Info for Next Session

All changes documented in: `TODAYS_PROGRESS_SUMMARY.md`

Key files to check if changes didn't persist:
- services/writer/main.py
- services/editor/main.py  
- services/presenter/main.py
- docker-compose.yml (OLLAMA_KEEP_ALIVE=0)


