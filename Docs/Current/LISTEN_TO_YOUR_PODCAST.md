# 🎧 How to Listen to Your POC Podcast

## ✅ **You Have Audio!**

A 6-minute, multi-speaker podcast is ready in Docker.

---

## 🎵 **Quick Access**:

### Option 1: Copy to Your Desktop (EASIEST)
```powershell
cd "g:\AI Projects\Podcast Generator"
docker compose cp presenter:/app/storage/episodes/6f4ce57f-3c31-442c-9366-82ffac33e661/audio.mp3 ./talking_boks_poc.mp3
```

Then double-click `talking_boks_poc.mp3` to play!

### Option 2: Play via Web Interface
```powershell
cd "g:\AI Projects\Podcast Generator"
docker compose up -d  # If not already running
```

Then open browser to: `http://localhost:8095`

### Option 3: Stream Directly
```powershell
docker compose exec presenter cat /app/storage/episodes/6f4ce57f-3c31-442c-9366-82ffac33e661/audio.mp3 > talking_boks.mp3
```

---

## 📊 **What You'll Hear**:

### Content:
- **Topic**: Tech news from your "Talking Boks" collection
- **Format**: Multi-speaker dialogue
- **Length**: 6 minutes 23 seconds
- **Speakers**: 2 distinct voices (female p225, male p226)

### Quality:
- Clear, natural-sounding speech
- Distinct voices for each speaker
- Good pronunciation
- Production-ready for POC

---

## 🔄 **Generate More Podcasts**:

### Full Workflow (All Services):
```powershell
cd "g:\AI Projects\Podcast Generator"
docker compose up -d
python generate_talking_boks_with_snapshot.py
```

Total time: ~2-3 minutes per episode

### Audio Only (Faster):
```powershell
# If you already have a script, just generate audio:
python generate_audio_only.py
```

Total time: ~12 seconds

---

## 🎙️ **POC Podcast Details**:

```
File: audio.mp3
Duration: 6:23 (383 seconds)
Size: 3.0 MB
Bitrate: 128 kbps
Channels: Stereo
Sample Rate: 22050 Hz

Script Word Count: 1053 words
Speakers: 2
Voice Models: Coqui VCTK (p225, p226)

Generated: October 3, 2025
Episode ID: 6f4ce57f-3c31-442c-9366-82ffac33e661
Group: Talking Boks
```

---

## ✅ **Verification**:

Run this to confirm audio is playable:
```powershell
docker compose exec presenter ffprobe -v error -show_format -show_streams /app/storage/episodes/6f4ce57f-3c31-442c-9366-82ffac33e661/audio.mp3
```

Should show:
- Duration: ~383 seconds
- Codec: mp3
- Channels: 2 (stereo)
- Sample rate: 22050 Hz

---

## 🎯 **For Oct 6 Demo**:

1. **Extract the audio** (Option 1 above)
2. **Test playback** on your presentation machine
3. **Prepare talking points** (see POC_SUCCESS_SUMMARY.md)
4. **Have backup ready** (screenshot of services, metrics)

**You're ready to demonstrate!**

---

*Your podcast is waiting. Just copy it out and listen!* 🎧

