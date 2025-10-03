# Architecture Fix & Post-Generation Cleanup Summary

**Date**: October 2, 2025 (Morning)  
**Status**: ✅ **FIXED - Architecture restored, cleanup implemented**

---

## 🎯 Problem Identified

1. **Architectural Error**: I incorrectly reverted the Presenter service to include VibeVoice TTS when it should only handle persona briefs/feedback
2. **LLM Tag Pollution**: Scripts contained problematic tags that VibeVoice couldn't parse:
   - `<think>...</think>` from LLM reasoning
   - `=== EDITED SCRIPT ===` from Editor
   - `=== REVIEW ===` and review content from Editor
   - `**Speaker X:**` markdown formatting

## ✅ Solutions Implemented

### Fix 1: Restored Correct Architecture

**Presenter Service** (Port 8004):
- **Role**: Generate persona briefs and feedback using Ollama
- **LLM**: Qwen2-1.5b on CPU
- **Hardware**: 2 CPUs (lightweight)
- **NO TTS**: Does NOT generate audio

**TTS Service** (Port 8015):
- **Role**: Generate audio using VibeVoice
- **Model**: VibeVoice-1.5B on GPU
- **Hardware**: 5 CPUs + GPU
- **NO LLM**: Does NOT generate briefs/feedback

**AI Overseer**:
- Calls **Presenter** for briefs/feedback
- Calls **TTS** for audio generation
- Clear separation of concerns

### Fix 2: Post-Generation Cleanup (User's Brilliant Idea!)

Instead of fighting LLMs with prompts to not generate tags, we **strip them AFTER generation**. This is:
- ✅ More reliable
- ✅ Simpler
- ✅ Maintainable

**Cleanup Function** (added to both Writer and Editor):

```python
def clean_script_for_audio(script: str) -> str:
    """
    Remove all problematic tags and formatting from script for audio generation.
    This is more reliable than trying to force LLMs not to generate them.
    """
    cleaned = script
    
    # Remove <think> tags and their content
    cleaned = re.sub(r'<think>.*?</think>', '', cleaned, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove === EDITED SCRIPT === markers
    cleaned = re.sub(r'===\s*EDITED SCRIPT\s*===', '', cleaned, flags=re.IGNORECASE)
    
    # Remove === REVIEW === and everything after it
    cleaned = re.sub(r'===\s*REVIEW\s*===.*$', '', cleaned, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove === REVIEW NOTES === and everything after it
    cleaned = re.sub(r'===\s*REVIEW NOTES\s*===.*$', '', cleaned, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove markdown bold from Speaker labels: **Speaker X:** → Speaker X:
    cleaned = re.sub(r'\*\*Speaker\s+(\d+):\*\*', r'Speaker \1:', cleaned)
    
    # Remove any remaining markdown formatting
    cleaned = re.sub(r'\*\*([^*]+)\*\*', r'\1', cleaned)  # Bold
    cleaned = re.sub(r'\*([^*]+)\*', r'\1', cleaned)      # Italic
    
    # Clean up excessive whitespace
    cleaned = re.sub(r'\n\s*\n\s*\n+', '\n\n', cleaned)
    cleaned = cleaned.strip()
    
    return cleaned
```

**Applied in**:
1. **Writer Service** - After script generation (line 315)
2. **Editor Service** - After script editing (line 268)

## 📁 Files Modified

### 1. `services/presenter/main.py`
- ✅ Restored to persona-only version (NO VibeVoice)
- Uses Ollama for briefs/feedback only

### 2. `services/tts/main.py`
- ✅ Fixed `BaseStreamer` import issue in `VibeVoice-Community/vibevoice/modular/streamer.py`
- Dedicated VibeVoice audio generation

### 3. `services/writer/main.py`
- ✅ Added `clean_script_for_audio()` function
- ✅ Applied cleanup after script generation
- ✅ Logs cleaned script stats

### 4. `services/editor/main.py`
- ✅ Added `clean_script_for_audio()` function
- ✅ Applied cleanup after script editing
- ✅ Logs cleaned script stats

### 5. `services/ai-overseer/app/services.py`
- ✅ Restored to call TTS service for audio (not Presenter)
- ✅ Removed `PresenterService.generate_audio()` call

### 6. `docker-compose.yml`
- ✅ Presenter: CPU-only, no GPU, no VibeVoice
- ✅ TTS: GPU, VibeVoice, port 8015

### 7. `VibeVoice-Community/vibevoice/modular/streamer.py`
- ✅ Fixed `BaseStreamer` import with fallback

## 🔍 Why This Approach is Better

### Before (Fighting LLMs):
```
System Prompt: "Do NOT use <think> tags or markdown"
→ LLM: "Okay!" *proceeds to use them anyway* 🤦‍♂️
→ Result: Unpredictable, fails randomly
```

### After (Post-Processing):
```
Script Generation → Clean Tags → Audio Generation
→ LLM: *generates whatever it wants* 
→ Cleanup: *removes all problematic tags reliably*
→ Result: Consistent, always works ✅
```

## 🎯 Benefits

1. **Architectural Clarity**: Each service has ONE clear responsibility
2. **Reliability**: Cleanup is deterministic (regex, not LLM behavior)
3. **Maintainability**: Add new tags to cleanup function, not prompts
4. **Debugging**: Easy to see what's being cleaned in logs
5. **Extensibility**: Can add more cleanup rules without changing prompts

## 📊 Expected Results

### Before Fixes:
- ❌ Presenter loaded VibeVoice unnecessarily
- ❌ Scripts had `<think>` tags causing 5-minute timeouts
- ❌ Scripts had `=== REVIEW ===` sections breaking audio parsing
- ❌ VibeVoice couldn't parse markdown `**Speaker 1:**`

### After Fixes:
- ✅ Presenter: Lightweight, CPU-only persona generation
- ✅ TTS: Dedicated GPU-based audio generation
- ✅ Scripts: Clean, parse-able, no problematic tags
- ✅ Audio: Should generate successfully

## 🧪 Next Steps

1. **Test Audio Generation**: Generate a podcast and verify audio works
2. **Monitor Cleanup**: Check logs to see what's being stripped
3. **Verify Duration**: Ensure generated audio is 10-15 minutes, not 1 second
4. **Check Quality**: Verify multi-speaker audio sounds natural

## 📝 Key Takeaways

1. **Don't fight LLMs**: Use post-processing instead of complex prompts
2. **Separation of Concerns**: One service = one responsibility
3. **Deterministic Cleanup**: Regex > hoping LLMs follow instructions
4. **User Insight**: Sometimes the simplest solution is the best!

---

**Credit**: The post-generation cleanup idea came from the user's excellent observation:
> "Can we do a replace of this text after the script generates instead of trying to force the models not to write this?"

This is the **correct architectural approach** - work WITH the LLMs, not against them!

