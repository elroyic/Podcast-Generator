# VibeVoice TTS Debugging Notes

**Date**: October 2, 2025  
**Status**: 🔧 In Progress - Transformers API Compatibility Issues

---

## 🎯 Goal
Get VibeVoice working in the dedicated TTS service (port 8015) for the split architecture.

## ✅ Progress Made

### 1. Fixed Import Errors
- ✅ `BaseStreamer` - Added fallback in `streamer.py`
- ✅ `FlashAttentionKwargs` - Added try/except in both `modeling_vibevoice_inference.py` and `modeling_vibevoice.py`

### 2. Fixed Transformers API Compatibility
- ✅ `_prepare_generation_config()` - Removed extra `True` parameter
- ✅ `_prepare_cache_for_generation()` - Added missing `assistant_model` parameter (None)
- ✅ `prepare_inputs_for_generation()` - Added missing method to model class

### 3. Dependencies
- ✅ Added `librosa==0.10.2` to TTS requirements
- ✅ Downgraded transformers from 4.48.0 to 4.45.2 for compatibility

## ❌ Current Blocker

**Error**: `Input type (float) and bias type (c10::BFloat16) should be the same`

**What we've tried**:
1. ❌ Load model as float32 → Still has bfloat16 buffers
2. ❌ Load model as float16 → Same issue
3. ❌ Explicit parameter/buffer conversion → Doesn't catch all tensors
4. ❌ Native dtype loading → Model uses bfloat16, inputs are float32
5. ❌ Input dtype matching → Still mismatch somewhere

**Root Cause**: The VibeVoice processor loads voice samples as float32, but the model has some layers in bfloat16. The conversion happens deep in the forward pass.

## 🔍 Technical Details

### Transformers API Signatures (v4.45.2)

**`_prepare_generation_config`**:
```python
(self, generation_config, kwargs)
```

**`_prepare_cache_for_generation`**:
```python
(self, generation_config, model_kwargs, assistant_model, batch_size, max_cache_length, device)
```
- Note: `assistant_model` is NEW in 4.45+, pass `None` for non-assistant models

### Files Modified

1. **`VibeVoice-Community/vibevoice/modular/modeling_vibevoice_inference.py`**:
   - Line 13-17: FlashAttentionKwargs import with fallback
   - Line 270-276: Fixed _prepare_generation_config call
   - Line 308-315: Fixed _prepare_cache_for_generation call with assistant_model
   - Line 153-193: Added prepare_inputs_for_generation method

2. **`VibeVoice-Community/vibevoice/modular/modeling_vibevoice.py`**:
   - Line 16-20: FlashAttentionKwargs import with fallback

3. **`VibeVoice-Community/vibevoice/modular/streamer.py`**:
   - Line 10-18: BaseStreamer import with fallback

4. **`services/tts/requirements.txt`**:
   - transformers: 4.48.0 → 4.45.2
   - Added librosa==0.10.2

5. **`services/tts/main.py`**:
   - Multiple dtype conversion attempts

## 🎯 Next Steps

### Option 1: Match Presenter's Setup (RECOMMENDED)
The Presenter service successfully runs VibeVoice. Key differences:
- **Base Image**: `pytorch/pytorch:2.3.1-cuda12.1-cudnn8-runtime` (not python:3.11-slim)
- **Transformers**: Installed from git (latest dev version)
- **Setup**: May have additional compatibility patches

**Action**: Switch TTS Dockerfile to match Presenter's base image and setup.

### Option 2: Continue Debugging Dtype Issue
- Investigate processor's audio loading code
- Check if voice sample loading can be forced to bfloat16
- Add dtype conversion in processor before model.generate()

### Option 3: Use Different TTS Backend
- Try Coqui TTS, Bark, or XTTS instead of VibeVoice
- These might have better transformers compatibility

---

## 📊 Working Components (Despite TTS Issue)

1. ✅ **Script Generation**: 1600-2400 words (was 566)
2. ✅ **Presenter Names**: Real names in scripts
3. ✅ **Post-Generation Cleanup**: Strips all LLM artifacts
4. ✅ **Architectural Split**: Presenter (CPU) ↔️ TTS (GPU)
5. ✅ **Editor Service**: Cleans and polishes scripts

**Script quality has improved dramatically!** Just need to get audio working.

---

**Recommendation**: Try matching Presenter's exact Docker setup since we know that works.

