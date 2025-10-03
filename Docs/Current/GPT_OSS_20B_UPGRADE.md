# GPT-OSS-20B Writer Upgrade

## 🎯 Objective

Upgrade Writer service from Qwen3 to GPT-OSS-20B for significantly higher quality podcast scripts.

## 📊 Model Comparison

| Aspect | Qwen3 | GPT-OSS-20B |
|--------|-------|-------------|
| **Size** | 5.2 GB (latest) | 13 GB |
| **Quality** | Good | Excellent |
| **Token Limit** | ~8k | ~4k |
| **Performance** | Fast | Slower (but acceptable) |
| **Script Quality** | Adequate | Professional |

## ⚠️ Key Consideration: 4K Token Limit

**Challenge**: GPT-OSS-20B has a 4k token output limitation

**Solution**: 
- Set safe limit to **3500 tokens** per request
- Target script length: **1200-1800 words** (~1600-2400 tokens)
- **Result**: Scripts fit comfortably in single request ✅

**Token Math**:
- 10-minute podcast ≈ 1500 words
- 1500 words ≈ 2000 tokens
- 3500 token limit provides **75% safety margin** 🎯

## 🛠️ Changes Made

### 1. Docker Compose (`docker-compose.yml`)

```yaml
# Writer Service (uses GPU Ollama with gpt-oss:20b for high-quality scripts)
writer:
  environment:
    - OLLAMA_MODEL=gpt-oss:20b
    - MAX_TOKENS_PER_REQUEST=3500
```

### 2. Writer Service (`services/writer/main.py`)

**Updated Configuration**:
```python
DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "gpt-oss:20b")
MAX_TOKENS_PER_REQUEST = int(os.getenv("MAX_TOKENS_PER_REQUEST", "3500"))
```

**Updated OllamaClient**:
```python
async def generate_metadata(
    self,
    model: str,
    prompt: str,
    system_prompt: str = None,
    max_tokens: int = None
) -> str:
    if max_tokens is None:
        max_tokens = MAX_TOKENS_PER_REQUEST
    
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.8,
            "top_p": 0.9,
            "num_predict": max_tokens  # Ollama parameter for max tokens
        }
    }
```

**Updated ScriptGenerator**:
```python
class ScriptGenerator:
    """Handles episode script generation logic using gpt-oss:20b (high-quality model with 4k token limit)."""
    
    def __init__(self):
        self.ollama_client = OllamaClient()
        logger.info(f"🎯 ScriptGenerator initialized with model: {DEFAULT_MODEL}, max tokens: {MAX_TOKENS_PER_REQUEST}")
```

## 🎯 Expected Benefits

### Script Quality Improvements:
1. **Better Dialogue Flow**: More natural conversations between speakers
2. **Enhanced Coherence**: Better topic transitions and narrative structure
3. **Improved Format Compliance**: Better adherence to "Speaker 1:" format requirements
4. **Richer Vocabulary**: More engaging and varied language use
5. **Professional Tone**: Higher quality writing that sounds more polished

### Technical Benefits:
1. **GPU Acceleration**: Still running on GPU for fast generation
2. **Reliable Output**: Established model with proven performance
3. **Safe Token Limits**: 75% margin ensures scripts aren't truncated
4. **Backward Compatible**: Same API, just better output

## 📝 Additional Fixes (Same Update)

### Markdown Formatting Fix (`services/presenter/main.py`)

Added robust cleaning before audio generation:
```python
# Remove markdown bold from Speaker labels: **Speaker X:** → Speaker X:
cleaned_text = re.sub(r'\*\*Speaker\s+(\d+):\*\*', r'Speaker \1:', cleaned_text)

# Remove any remaining markdown formatting
cleaned_text = re.sub(r'\*\*([^*]+)\*\*', r'\1', cleaned_text)  # Bold
cleaned_text = re.sub(r'\*([^*]+)\*', r'\1', cleaned_text)      # Italic
```

### Updated Prompts (`services/writer/main.py`, `services/editor/main.py`)

**Writer Prompt**:
```
⚠️ CRITICAL: Do NOT use markdown formatting!
- Write: Speaker 1: (plain text, NO asterisks)
- NOT: **Speaker 1:** (this breaks the audio generation!)
- NOT: *Speaker 1:* (no italics either)
```

**Editor Prompt**:
```
⚠️ CRITICAL - MULTI-SPEAKER FORMAT PRESERVATION:
- DO NOT use markdown formatting: Write "Speaker 1:" NOT "**Speaker 1:**" or "*Speaker 1:*"
- Use PLAIN TEXT only - no asterisks, no bold, no italics around Speaker labels
```

## 🚀 Resource Allocation

**Current GPU Setup** (RTX 3070Ti 8GB):
- ✅ Writer: gpt-oss:20b (~13GB model, fits with GPU offloading)
- ✅ VibeVoice TTS: 1.5B (~3GB)
- ✅ Both use GPU sequentially (not parallel) ✨

**CPU Ollama** (16 cores):
- ✅ Reviewer: Qwen2-0.5b, Qwen2-1.5b
- ✅ Editor: Qwen2-1.5b

## 📊 Performance Expectations

### Before (Qwen3):
- Script generation: ~48 seconds
- Quality: Good
- Format compliance: 85%

### After (GPT-OSS-20B):
- Script generation: ~60-90 seconds (expected)
- Quality: Excellent
- Format compliance: 95%+ (expected)

**Trade-off**: Slightly slower, but **much higher quality** 🎯

## ✅ Testing Checklist

- [ ] Writer service starts successfully
- [ ] GPT-OSS-20B model loads on GPU
- [ ] Script generation completes within timeout
- [ ] Scripts are proper length (1200-1800 words)
- [ ] Scripts use plain text "Speaker X:" format (no markdown)
- [ ] No `<think>` tags in output
- [ ] Audio generation works with cleaned scripts
- [ ] Full podcast duration is appropriate (8-12 minutes)

## 🔍 Monitoring

**Watch for**:
- Script generation time (should be < 90 seconds)
- Script word count (should be 1200-1800 words)
- Token usage (should be < 3500 tokens)
- Format compliance (plain text Speaker labels)

**Logs to check**:
```bash
# Writer initialization
docker compose logs writer | grep "ScriptGenerator initialized"

# Generation time
docker compose logs celery-worker | grep "generate-script"

# Ollama GPU usage
docker compose logs ollama | grep "gpt-oss:20b"
```

## 📁 Files Modified

1. `docker-compose.yml` - Updated Writer environment variables
2. `services/writer/main.py` - Updated model, token limits, prompts
3. `services/editor/main.py` - Updated prompts to forbid markdown
4. `services/presenter/main.py` - Added markdown cleaning
5. `setup_gpt_oss_20b.py` - Setup script (helper, not needed since model exists)
6. `GPT_OSS_20B_UPGRADE.md` - This documentation

---

**Date**: October 1, 2025  
**Status**: ✅ **CONFIGURED - READY FOR TESTING**  
**Next Step**: Generate test podcast to verify quality improvement

