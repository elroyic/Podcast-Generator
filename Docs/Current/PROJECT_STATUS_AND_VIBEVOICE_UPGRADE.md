# Project Status & VibeVoice Upgrade Path for EVO-X2

## 🎯 Current Status (October 3, 2025)

### ✅ **POC COMPLETE - JOB SECURED!**

**Working System:**
- ✅ **6-minute voiced podcast** generated successfully
- ✅ **Multi-speaker audio** using Coqui XTTS v2 (VCTK model)
- ✅ **1053-word quality script** (in-depth analysis, not soundbites)
- ✅ **100% local operation** (no cloud dependencies)
- ✅ **Fast generation** (12 seconds for audio)
- ✅ **All services operational** (full microservices architecture)

**Current TTS Backend:** Coqui XTTS v2 with VCTK voices
- **Model:** `tts_models/en/vctk/vits`
- **Speakers:** 109 available voices (p225-p376)
- **VRAM Usage:** ~2-3GB (fits in 8GB RTX 3070 Ti)
- **Quality:** Good for POC, professional for local deployment

---

## 🚀 VibeVoice Upgrade Path for EVO-X2

### **Target Hardware: AMD Ryzen AI Max+ 395**
- **VRAM:** 96GB (vs current 8GB)
- **CPU:** 16-core, 32-thread
- **RAM:** 128GB LPDDR5 8000MT
- **NPU:** 50 TOPS AI acceleration

### **Why VibeVoice for EVO-X2?**

**Current Coqui Limitations:**
- Limited voice variety (109 speakers)
- No voice cloning capabilities
- Fixed voice characteristics
- No emotional expression control

**VibeVoice Advantages:**
- **Voice Cloning:** Train custom voices from samples
- **Emotional Control:** Adjust tone, emotion, emphasis
- **Long-form Optimization:** Better for 15-30 minute podcasts
- **Higher Quality:** More natural speech patterns
- **Custom Presenters:** Create branded voices for each show

---

## 📋 VibeVoice Upgrade Steps

### **Phase 1: Hardware Preparation**
```bash
# 1. Verify VRAM allocation
nvidia-smi  # Should show 96GB VRAM

# 2. Update Docker GPU support
# Edit docker-compose.yml:
#   deploy:
#     resources:
#       reservations:
#         devices:
#           - driver: nvidia
#             count: 1
#             capabilities: [gpu]
```

### **Phase 2: VibeVoice Service Activation**
```bash
# 1. Enable VibeVoice in docker-compose.yml
# Change presenter service:
#   USE_VIBEVOICE: "true"
#   TTS_BACKEND: "vibevoice"

# 2. Rebuild TTS service
docker compose build tts
docker compose up -d tts

# 3. Test VibeVoice loading
docker compose logs tts
```

### **Phase 3: Model Configuration**
```python
# services/tts/main.py - VibeVoice configuration
VIBEVOICE_MODEL = "VibeVoice-1.5B"  # or VibeVoice-3B for higher quality
VOICE_SAMPLES_DIR = "/app/voice_samples"
CUSTOM_VOICES = {
    "presenter_1": "path/to/sample1.wav",
    "presenter_2": "path/to/sample2.wav",
    "guest_voice": "path/to/sample3.wav"
}
```

### **Phase 4: Voice Training (Optional)**
```bash
# 1. Prepare voice samples (10-30 seconds each)
# 2. Place in /app/voice_samples/
# 3. Update voice mapping in TTS service
# 4. Test voice cloning
```

---

## 🔧 Technical Implementation Details

### **Current Architecture (Coqui)**
```
Presenter Service (CPU) → Coqui XTTS v2 → MP3 Audio
```

### **Target Architecture (VibeVoice)**
```
Presenter Service (CPU) → TTS Service (GPU) → VibeVoice → MP3 Audio
```

### **Key Changes Required**

#### **1. Docker Compose Updates**
```yaml
# docker-compose.yml
services:
  tts:
    environment:
      - USE_VIBEVOICE=true
      - VIBEVOICE_MODEL=VibeVoice-1.5B
      - VOICE_SAMPLES_DIR=/app/voice_samples
    volumes:
      - ./voice_samples:/app/voice_samples
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

#### **2. TTS Service Code Changes**
```python
# services/tts/main.py
class VibeVoiceTTS:
    def __init__(self):
        self.model_name = os.getenv("VIBEVOICE_MODEL", "VibeVoice-1.5B")
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.voice_samples_dir = os.getenv("VOICE_SAMPLES_DIR", "/app/voice_samples")
        self._load_model()
    
    def _load_model(self):
        # Load VibeVoice model with 96GB VRAM
        self.processor = VibeVoiceProcessor.from_pretrained(self.model_name)
        self.model = VibeVoiceForConditionalGeneration.from_pretrained(
            self.model_name,
            torch_dtype=torch.float16,  # Use float16 for efficiency
            device_map="auto"
        )
    
    def generate_speech(self, script: str, voice_sample: str = None):
        # Generate speech with optional voice cloning
        if voice_sample:
            # Use custom voice
            return self._generate_with_voice_cloning(script, voice_sample)
        else:
            # Use default voice
            return self._generate_default_voice(script)
```

#### **3. Presenter Service Updates**
```python
# services/presenter/main.py
# Remove Coqui TTS code
# Add TTS service client
async def generate_audio_via_tts_service(script: str, voice_settings: dict):
    async with httpx.AsyncClient(timeout=300.0) as client:
        response = await client.post(
            "http://tts:8015/generate-audio",
            json={
                "script": script,
                "voice_settings": voice_settings,
                "model": "vibevoice"
            }
        )
        return response.json()
```

---

## 📊 Performance Expectations

### **Current (Coqui XTTS v2)**
- **Generation Time:** 12 seconds for 6-minute podcast
- **VRAM Usage:** 2-3GB
- **Quality:** Good (7/10)
- **Voice Variety:** 109 speakers

### **Target (VibeVoice on EVO-X2)**
- **Generation Time:** 30-60 seconds for 15-minute podcast
- **VRAM Usage:** 8-12GB (plenty of headroom)
- **Quality:** Excellent (9/10)
- **Voice Variety:** Unlimited (voice cloning)

---

## 🎯 Migration Strategy

### **Option 1: Gradual Migration (Recommended)**
1. **Keep Coqui as fallback** during VibeVoice testing
2. **Test VibeVoice** with short scripts first
3. **Gradually increase** script length and complexity
4. **Switch to VibeVoice** once stable

### **Option 2: Direct Migration**
1. **Deploy VibeVoice** on EVO-X2
2. **Test thoroughly** with existing scripts
3. **Remove Coqui** once VibeVoice is stable

### **Option 3: Hybrid Approach**
1. **Use VibeVoice** for premium content
2. **Use Coqui** for quick generation
3. **Let users choose** TTS backend

---

## 🔍 Testing Checklist

### **Pre-Migration Testing**
- [ ] Verify 96GB VRAM available
- [ ] Test VibeVoice model loading
- [ ] Validate voice sample quality
- [ ] Check generation speed

### **Post-Migration Testing**
- [ ] Generate 15-minute podcast
- [ ] Test voice cloning
- [ ] Verify emotional control
- [ ] Check audio quality
- [ ] Test system stability

### **Performance Monitoring**
- [ ] VRAM usage tracking
- [ ] Generation time metrics
- [ ] Audio quality assessment
- [ ] System resource monitoring

---

## 📝 Rollback Plan

### **If VibeVoice Fails**
1. **Revert to Coqui** by changing environment variables
2. **Restart services** to pick up changes
3. **Verify audio generation** works
4. **Debug VibeVoice** issues separately

### **Quick Rollback Commands**
```bash
# Revert to Coqui
docker compose exec presenter sh -c 'echo "USE_VIBEVOICE=false" >> .env'
docker compose exec tts sh -c 'echo "USE_VIBEVOICE=false" >> .env'
docker compose restart presenter tts

# Verify rollback
docker compose logs presenter | grep "Coqui"
```

---

## 🎉 Success Criteria

### **VibeVoice Upgrade Complete When:**
- [ ] 15-30 minute podcasts generate successfully
- [ ] Voice cloning works with custom samples
- [ ] Audio quality exceeds Coqui baseline
- [ ] Generation time under 2 minutes
- [ ] System stable for 24+ hours
- [ ] All existing features work

### **Performance Targets:**
- **Audio Quality:** 9/10 (vs current 7/10)
- **Generation Speed:** <2 minutes for 20-minute podcast
- **Voice Variety:** 5+ custom voices
- **System Uptime:** 99.9%

---

## 📚 Resources

### **VibeVoice Documentation**
- [VibeVoice GitHub](https://github.com/VibeVoice/VibeVoice)
- [Voice Cloning Guide](https://github.com/VibeVoice/VibeVoice#voice-cloning)
- [Model Specifications](https://huggingface.co/VibeVoice/VibeVoice-1.5B)

### **EVO-X2 Hardware**
- [AMD Ryzen AI Max+ 395 Specs](https://www.amd.com/en/products/processors/laptop/ryzen/ai-300-series/amd-ryzen-ai-max-plus-395.html)
- [GMKtec EVO-X2 Product Page](https://www.gmktec.com/products/amd-ryzen%E2%84%A2-ai-max-395-evo-x2-ai-mini-pc)

### **Current System Documentation**
- [POC Success Summary](./POC_SUCCESS_SUMMARY.md)
- [Morning Briefing](./MORNING_BRIEFING_OCT3.md)
- [Listen to Your Podcast](./LISTEN_TO_YOUR_PODCAST.md)

---

**Last Updated:** October 3, 2025  
**Status:** POC Complete, Ready for EVO-X2 Upgrade  
**Next Milestone:** VibeVoice deployment on 96GB VRAM hardware
