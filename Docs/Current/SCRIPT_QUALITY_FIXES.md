# Script Quality Fixes - Based on User Feedback

## 🎯 Issues Identified

### Issue 1: Generic Speaker Names
**Problem**: Scripts had `[Name]` placeholders  
**Example**: `Speaker 1: Hi, I'm [Name]...`  
**Should Be**: `Speaker 1: Hi, I'm Sam General Insider...`

### Issue 2: Scripts Too Short (Soundbites, Not Podcasts)
**Problem**: Only **566 words** = **3.8 minutes**  
**Target Was**: 1200-1800 words (8-12 minutes)  
**Actual Need**: 2000-3000 words (15-20 minutes) for depth

**User Feedback**:
> "The scripts are really short... More like it's producing a sound bite not a podcast"

## ✅ Fixes Implemented

### Fix 1: Inject Actual Presenter Names

**Updated `services/writer/main.py`**:

1. Import Presenter model:
```python
from shared.models import PodcastGroup, Episode, EpisodeMetadata, Presenter
```

2. Fetch presenter names from database:
```python
# Get presenter names if not provided
if not presenter_names and podcast_group.presenters:
    presenter_names = [p.name for p in podcast_group.presenters[:4]]
    logger.info(f"Using presenters: {presenter_names}")
```

3. Pass to prompt:
```python
PRESENTERS (use these names when speakers introduce themselves):
- Speaker 1: Sam General Insider
- Speaker 2: [Second Presenter Name]
```

4. Instruction to use names:
```
1. Create an engaging opening where speakers introduce themselves by name
...
- Speakers should introduce themselves with their actual names (see PRESENTERS list above)
```

### Fix 2: Dramatically Increase Script Length

**Before**:
```
7. Aim for 8-12 minutes of content (1200-1800 words)
```

**After**:
```
7. **TARGET: 15-20 minutes of content (2000-3000 words) - DO NOT make it shorter!**
```

**Also Increased Token Limit**:
- Before: 3500 tokens
- After: **5000 tokens**
- Reason: 3000 words ≈ 4000 tokens, need headroom

**Added Depth Requirements**:
```
⚠️ DEPTH REQUIREMENTS:
- Each article should get 150-300 words of discussion
- Provide context, implications, and analysis
- Include expert perspectives and insights
- Connect topics to broader themes
- Don't just state facts - discuss what they mean
```

**Updated Structure**:
```
- Opening: 150-250 words (was 100-150)
- Main Content: 1600-2400 words (was 900-1400)  
- Closing: 200-300 words (was 100-200)
```

**Specific Instructions for Depth**:
```
2. **COVER ALL ARTICLES IN DEPTH** - don't just summarize, provide analysis
...
  * Cover each article with meaningful discussion (not just headlines)
  * Don't rush - give each topic the time it deserves
  * Aim for 200-400 words per major topic
```

## 📊 Expected Results

### Before Fixes:
- **Word Count**: 566 words
- **Duration**: 3.8 minutes
- **Depth**: Surface level (soundbite)
- **Names**: Generic placeholders `[Name]`
- **Quality**: ⚠️ Insufficient

### After Fixes:
- **Word Count**: 2000-3000 words (target)
- **Duration**: 15-20 minutes
- **Depth**: In-depth analysis with context
- **Names**: Actual presenter names (e.g., "Sam General Insider")
- **Quality**: ✅ Professional podcast

## 🔧 Technical Changes

### Files Modified:

1. **`services/writer/main.py`**:
   - Added Presenter model import
   - Updated `generate_episode_script()` to fetch presenter names
   - Modified `create_script_content_prompt()` to accept and use presenter names
   - Increased target length from 1200-1800 to 2000-3000 words
   - Added depth requirements and detailed instructions
   - Increased max tokens from 3500 to 5000

2. **`docker-compose.yml`**:
   - Updated Writer: `MAX_TOKENS_PER_REQUEST=5000`

## 🎭 Presenter Name Integration

The system will now:
1. Query the database for presenters assigned to the podcast group
2. Extract their names (up to 4 presenters)
3. Map them to Speaker 1, 2, 3, 4
4. Include in the prompt so LLM uses real names
5. Speakers introduce themselves by name in the script

**Example**:
```
PRESENTERS:
- Speaker 1: Sam General Insider
- Speaker 2: Alex Tech Reporter

Script Output:
Speaker 1: Welcome to Talking Boks! I'm Sam General Insider.
Speaker 2: And I'm Alex Tech Reporter. Great to be here!
```

## 📈 Length Enforcement

Multiple strategies to ensure length:

1. **Explicit Target**: "2000-3000 words - DO NOT make it shorter!"
2. **Per-Article Depth**: "150-300 words per article"
3. **Per-Topic Depth**: "200-400 words per major topic"
4. **Structure Breakdown**: 
   - Opening: 150-250 words
   - Main: 1600-2400 words
   - Closing: 200-300 words
5. **Token Headroom**: 5000 tokens allows full 3000-word scripts

## ⚠️ Additional Improvements Needed

### Still To Fix:
1. **Editor Service**: Should also preserve length, not shorten
2. **Quality Validation**: Add script length checker
3. **Fallback Scripts**: Also need to be longer (currently very short)
4. **Token Monitoring**: Log actual vs. target word counts

### TTS Service:
- Currently unhealthy (transformers compatibility issue)
- Need to fix `BaseStreamer` import issue
- Lower priority than script quality

## 🧪 Testing Plan

1. Generate new podcast with Talking Boks
2. Check script word count (should be 2000-3000)
3. Verify presenter names are used (not `[Name]`)
4. Confirm in-depth coverage of articles
5. Validate 15-20 minute estimated duration

---

**Date**: October 1, 2025  
**Status**: ✅ **FIXES IMPLEMENTED - READY FOR TESTING**  
**Next**: Generate test podcast to verify improvements

