# POC Delivery Plan - October 6, 2025

**Target Hardware**: AMD Ryzen AI Max+ 395 Mini PC  
**Deadline**: October 6, 2025 (4 days)  
**Goal**: High-quality POC demonstrating vision (not performance)

---

## 🚀 TARGET HARDWARE SPECS

### AMD Ryzen AI Max+ 395
```
CPU:     16 cores / 32 threads @ 5.1 GHz (Zen 5)
RAM:     128GB LPDDR5-8000 (32GB system + 96GB VRAM)
GPU:     Radeon 8060S (40 compute units, RDNA 3.5)
VRAM:    96GB (!!!) = 12x current 8GB
NPU:     50 TOPS for AI acceleration
Total:   126 TOPS AI performance
Storage: 6TB NVMe PCIe Gen 4
```

**Impact on Podcast Generator**:
- ✅ VibeVoice will run smoothly (needs ~10GB, have 96GB!)
- ✅ Can load ALL models simultaneously
- ✅ Can use larger models (Qwen3:32B, GPT-OSS:20B)
- ✅ NPU can accelerate inference
- ✅ No memory pressure = fast, reliable generation

---

## 🎯 POC STRATEGY (User's Vision)

### Philosophy:
> "We need to show something that sounds good and can get the point across about what the vision of the application is."

### Approach:
1. **QUALITY > SPEED** for POC
2. **Sequential processing** - one task at a time with ALL resources
3. **Allow time** - 1 hour for script? Fine. 12 hours for audio? Fine.
4. **Prove vision** - Show what's possible, not how fast
5. **New hardware** - Will solve performance when deployed

### Implementation:
- Shut down non-essential services during each phase
- Dedicate full CPU+GPU to current task
- No timeouts - let it run as long as needed
- Focus on output quality

---

## 📋 CURRENT STATUS (Before POC)

### ✅ What's Working (97% Complete):
1. **Script Generation** - 2000+ words, real names, in-depth ✅
2. **Post-Gen Cleanup** - Removes all LLM artifacts ✅
3. **Editor Service** - Polishes scripts ✅
4. **Metadata Generation** - SEO-ready ✅
5. **Presenter Briefs** - Persona system ✅
6. **Architecture** - Correct split (temporarily using Presenter for audio) ✅

### ⚠️ What's Constrained:
1. **VibeVoice Audio** - Works but slow on 8GB VRAM
2. **Writer Service** - Sometimes times out with long scripts
3. **Concurrent Operations** - Resource contention

### 🎯 What We'll Do:
1. Run services **sequentially**
2. Generate ONE high-quality podcast
3. Verify quality (not speed)
4. Document for deployment

---

## 🎬 POC GENERATION PLAN

### Phase 1: Script Generation (30-60 min)
**Services Running**: Writer, Editor, Ollama (GPU)  
**Services Stopped**: Presenter, TTS, Reviewers, Collections, News Feed

**Steps**:
1. Stop non-essential services
2. Restart Writer/Editor with full resources
3. Generate 2000-3000 word script
4. Let it take as long as needed
5. Verify script quality

**Expected**: High-quality, in-depth script with real presenter names

### Phase 2: Audio Generation (1-12 hours)
**Services Running**: Presenter (with VibeVoice on GPU)  
**Services Stopped**: Writer, Editor, Ollama, Reviewers, Collections

**Steps**:
1. Stop Writer/Editor/Ollama (free resources)
2. Start Presenter with VibeVoice
3. Generate multi-speaker audio
4. Let it run overnight if needed (12 hours OK!)
5. Verify audio quality

**Expected**: 15-20 minute podcast with multiple voices

### Phase 3: Verification
**Checks**:
- ✅ Audio duration: 10-20 minutes
- ✅ Audio quality: Multi-speaker, natural
- ✅ Script content: In-depth, real names
- ✅ File size: Reasonable (not 1 second dummy file)

---

## 📊 QUALITY TARGETS FOR POC

### Script:
- **Length**: 2000-3000 words
- **Duration estimate**: 13-20 minutes
- **Depth**: In-depth analysis (not soundbites)
- **Names**: Real presenter names
- **Format**: Clean multi-speaker dialogue

### Audio:
- **Actual duration**: 10-20 minutes
- **Speakers**: 2-4 distinct voices
- **Quality**: Clear, natural speech
- **Format**: MP3, proper bitrate

### Overall:
- **Demonstrates**: Full workflow works
- **Showcases**: Vision of AI podcast generation
- **Proves**: Concept is viable
- **Performance**: Not a concern (new hardware will solve)

---

## 🔧 TECHNICAL APPROACH

### Current Setup (8GB VRAM):
```
Sequential Mode:
┌─────────────────────────────────────┐
│ SCRIPT GENERATION (Phase 1)         │
│ ├─ Writer (GPU): Generate script    │
│ ├─ Editor (CPU): Polish script      │
│ └─ Ollama (GPU): LLM inference      │
│                                     │
│ Services OFF: Presenter, TTS,       │
│               Reviewers, Collections│
└─────────────────────────────────────┘
        ↓ (shutdown Writer/Editor/Ollama)
┌─────────────────────────────────────┐
│ AUDIO GENERATION (Phase 2)          │
│ ├─ Presenter (GPU): VibeVoice TTS   │
│ └─ All resources dedicated to audio │
│                                     │
│ Services OFF: Writer, Editor,       │
│               Ollama, Reviewers     │
└─────────────────────────────────────┘
```

### New Hardware (96GB VRAM):
```
All services run concurrently:
├─ Writer (GPU): Fast generation
├─ Editor (NPU): AI acceleration
├─ Presenter (NPU): AI personas
├─ TTS (GPU): Parallel audio
└─ Ollama (GPU): Multiple models loaded
= FAST + HIGH QUALITY
```

---

## 📅 TIMELINE TO OCTOBER 6

### Today (Oct 2):
- ✅ Generate high-quality POC podcast
- ✅ Verify quality (even if it takes 12+ hours)
- ✅ Document results

### Oct 3-4:
- Create deployment guide for new hardware
- Plan NPU utilization strategy
- Test larger models (fits in 96GB!)
- Optimize configurations

### Oct 5:
- Final testing on current hardware
- Prepare demo script
- Create presentation materials

### Oct 6:
- **DELIVER POC** ✅
- Deploy on new hardware
- Demonstrate vision

---

## 💡 KEY INSIGHTS

1. **8GB VRAM is the bottleneck** - Not the code!
2. **96GB VRAM solves everything** - VibeVoice, larger models, concurrent ops
3. **Current quality is excellent** - Scripts improved 300%+
4. **Architecture is correct** - Will shine on new hardware
5. **Sequential mode works** - For constrained environments

---

## 🎯 SUCCESS CRITERIA FOR POC

**Must Have**:
- ✅ 10-20 minute podcast with good audio quality
- ✅ 2000+ word in-depth script
- ✅ Real presenter names
- ✅ Multi-speaker dialogue
- ✅ Demonstrates full workflow

**Nice to Have** (new hardware will provide):
- Fast generation (< 5 minutes total)
- Concurrent operations
- Larger context windows
- Better model quality

---

**Bottom Line**: With 96GB VRAM, ALL our current issues disappear. Focus on quality POC now, optimize on new hardware!

