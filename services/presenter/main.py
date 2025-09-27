"""
VibeVoice-Enhanced Presenter Service - Generates high-quality MP3 audio files using VibeVoice.
Falls back to synthetic audio when VibeVoice is unavailable.
"""

import logging
import os
import tempfile
from datetime import datetime
from typing import Dict, Any, Optional, List
from uuid import UUID

import numpy as np
import torch
import soundfile as sf
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pydub import AudioSegment
from pydub.generators import Sine, WhiteNoise

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Presenter Service (MP3)", version="1.0.0")

# Configuration
# Root storage directory; files will be written under /episodes/{episode_id}/
AUDIO_STORAGE_PATH = os.getenv("AUDIO_STORAGE_PATH", "/app/storage")
SAMPLE_RATE = 22050
BIT_RATE = 128  # kbps for MP3


class AudioGenerationRequest(BaseModel):
    episode_id: UUID
    script: str
    presenter_ids: List[UUID]
    voice_settings: Optional[Dict[str, Any]] = None


class AudioGenerationResponse(BaseModel):
    episode_id: UUID
    audio_url: str
    duration_seconds: int
    file_size_bytes: int
    format: str
    generation_metadata: Dict[str, Any]


class VibeVoiceTTS:
    """VibeVoice Text-to-Speech implementation with fallback."""
    
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = None
        self.processor = None
        self.is_loaded = False
        self.use_vibevoice = os.getenv("USE_VIBEVOICE", "true").lower() == "true"
        
        if self.use_vibevoice:
            self._load_model()
    
    def _load_model(self):
        """Load the VibeVoice model if available."""
        try:
            logger.info(f"Loading VibeVoice model on {self.device}")
            
            # Try to import VibeVoice - this may fail if not installed
            try:
                from transformers import AutoModel, AutoProcessor
                logger.info("Loading VibeVoice model from HuggingFace...")
                
                # Load VibeVoice model
                self.model = AutoModel.from_pretrained("microsoft/VibeVoice-1.5B", trust_remote_code=True)
                self.processor = AutoProcessor.from_pretrained("microsoft/VibeVoice-1.5B", trust_remote_code=True)
                
                self.model = self.model.to(self.device)
                self.is_loaded = True
                logger.info("✅ VibeVoice model loaded successfully!")
                
            except Exception as hf_error:
                logger.warning(f"HuggingFace VibeVoice failed: {hf_error}")
                # Try local vibevoice package
                from vibevoice.modular.modeling_vibevoice_inference import VibeVoiceForConditionalGenerationInference
                from vibevoice.processor.vibevoice_processor import VibeVoiceProcessor
                
                self.model = VibeVoiceForConditionalGenerationInference.from_pretrained("vibevoice/VibeVoice-1.5B")
                self.processor = VibeVoiceProcessor.from_pretrained("vibevoice/VibeVoice-1.5B")
                
                self.model = self.model.to(self.device)
                self.is_loaded = True
                logger.info("✅ Local VibeVoice model loaded successfully!")
            
        except ImportError as e:
            logger.warning(f"VibeVoice not available: {e}")
            logger.warning("Falling back to synthetic audio generation")
            self.is_loaded = False
        except Exception as e:
            logger.warning(f"Failed to load VibeVoice model: {e}")
            logger.warning("Falling back to synthetic audio generation")
            self.is_loaded = False
    
    def generate_speech(self, text: str, voice_id: str = "default") -> np.ndarray:
        """Generate speech from text using VibeVoice or fallback."""
        if self.is_loaded and self.use_vibevoice:
            return self._generate_vibevoice_speech(text, voice_id)
        else:
            return self._generate_synthetic_speech(text)
    
    def _generate_vibevoice_speech(self, text: str, voice_id: str) -> np.ndarray:
        """Generate speech using VibeVoice model."""
        try:
            logger.info(f"Generating speech with VibeVoice for voice: {voice_id}")
            logger.info(f"Text length: {len(text)} characters")
            
            # Process text chunks to avoid memory issues
            max_chunk_length = 500
            if len(text) > max_chunk_length:
                chunks = [text[i:i+max_chunk_length] for i in range(0, len(text), max_chunk_length)]
            else:
                chunks = [text]
            
            audio_chunks = []
            
            for i, chunk in enumerate(chunks):
                logger.info(f"Processing chunk {i+1}/{len(chunks)}")
                
                # Prepare inputs
                inputs = self.processor(chunk, return_tensors="pt", padding=True, truncation=True)
                inputs = {k: v.to(self.device) for k, v in inputs.items()}
                
                # Generate audio
                with torch.no_grad():
                    audio_outputs = self.model.generate(**inputs)
                
                # Convert to numpy array
                if hasattr(audio_outputs, 'cpu'):
                    audio_array = audio_outputs.cpu().numpy()
                else:
                    audio_array = audio_outputs
                
                if audio_array.ndim > 1:
                    audio_array = audio_array.flatten()
                
                audio_chunks.append(audio_array)
            
            # Concatenate all chunks
            full_audio = np.concatenate(audio_chunks)
            
            # Ensure it's stereo
            if full_audio.ndim == 1:
                # Convert to stereo by duplicating mono channel
                full_audio = np.stack([full_audio, full_audio], axis=-1)
            
            logger.info(f"✅ Generated VibeVoice audio: {full_audio.shape}")
            return full_audio
            
        except Exception as e:
            logger.error(f"VibeVoice generation failed: {e}")
            logger.info("Falling back to synthetic audio")
            return self._generate_synthetic_speech(text)
    
    def _generate_synthetic_speech(self, text: str) -> np.ndarray:
        """Generate synthetic speech as fallback."""
        logger.info("Generating synthetic speech (fallback)")
        
        # Calculate duration based on text length (rough estimate: 150 words per minute)
        words = len(text.split())
        duration_minutes = max(1, words / 150)  # Minimum 1 minute
        duration_seconds = int(duration_minutes * 60)
        
        # Create synthetic audio using sine waves and white noise
        sample_rate = SAMPLE_RATE
        total_samples = int(duration_seconds * sample_rate)
        
        # Generate base tone (simulating voice)
        t = np.linspace(0, duration_seconds, total_samples, False)
        base_freq = 200 + np.sin(t * 0.5) * 50  # Varying frequency for more natural sound
        audio = np.sin(2 * np.pi * base_freq * t)
        
        # Add harmonics for richer sound
        audio += 0.3 * np.sin(2 * np.pi * base_freq * 2 * t)
        audio += 0.2 * np.sin(2 * np.pi * base_freq * 3 * t)
        
        # Add some white noise for texture
        noise = np.random.normal(0, 0.05, total_samples)
        audio += noise
        
        # Apply amplitude modulation to simulate speech patterns
        words_per_second = words / duration_seconds
        modulation_freq = words_per_second / 3  # Rough speech rhythm
        modulation = 0.5 + 0.5 * np.sin(2 * np.pi * modulation_freq * t)
        audio *= modulation
        
        # Normalize
        audio = audio / np.max(np.abs(audio)) * 0.8
        
        # Convert to stereo
        stereo_audio = np.stack([audio, audio], axis=-1)
        
        return stereo_audio


# Global TTS instance
vibevoice_tts = VibeVoiceTTS()


def text_to_speech_audio(script: str, duration_seconds: int = 30) -> AudioSegment:
    """Generate synthetic speech audio from text."""
    
    # Calculate words per second for natural speech (average ~2.5 words/second)
    words = script.split()
    word_count = len(words)
    natural_duration = max(duration_seconds, word_count / 2.5)
    
    # Generate base audio with multiple sine waves to simulate speech (stereo)
    base_audio = AudioSegment.silent(duration=int(natural_duration * 1000)).set_channels(2)  # Stereo
    
    # Create speech-like audio using multiple sine waves (stereo)
    speech_audio = AudioSegment.silent(duration=int(natural_duration * 1000)).set_channels(2)  # Stereo
    
    # Generate formants (frequency bands that characterize speech)
    formants = [
        (200, 0.8),   # Fundamental frequency
        (800, 0.6),   # First formant
        (1200, 0.4),  # Second formant
        (2500, 0.2),  # Third formant
    ]
    
    # Create speech-like waveform
    for freq, amplitude in formants:
        # Generate sine wave with some variation
        sine_wave = Sine(freq).to_audio_segment(duration=int(natural_duration * 1000))
        
        # Add some randomness to make it more speech-like
        noise = WhiteNoise().to_audio_segment(duration=int(natural_duration * 1000))
        noise = noise - 20  # Reduce noise volume
        
        # Combine sine wave with noise
        combined = sine_wave.overlay(noise)
        combined = combined - (20 - int(amplitude * 10))  # Adjust volume based on amplitude
        
        # Add to speech audio
        speech_audio = speech_audio.overlay(combined)
    
    # Add some natural pauses and variations
    # Create a more dynamic audio by varying the volume over time (stereo)
    final_audio = AudioSegment.silent(duration=int(natural_duration * 1000)).set_channels(2)  # Stereo
    
    # Split into chunks and vary volume to simulate speech patterns
    chunk_duration = 500  # 0.5 seconds
    for i in range(0, len(speech_audio), chunk_duration):
        chunk = speech_audio[i:i + chunk_duration]
        
        # Vary volume to simulate speech rhythm
        volume_variation = np.sin(i / 1000 * 2 * np.pi) * 5  # ±5dB variation
        chunk = chunk + volume_variation
        
        # Add some silence between "words"
        if i % 2000 == 0:  # Every 2 seconds
            silence = AudioSegment.silent(duration=100).set_channels(2)  # 100ms pause (stereo)
            final_audio = final_audio + chunk + silence
        else:
            final_audio = final_audio + chunk
    
    return final_audio


def create_mp3_audio_file(episode_id: UUID, script: str) -> str:
    """Create an actual MP3 audio file from script using VibeVoice."""
    
    # Ensure storage directory exists: /app/storage/episodes/{episode_id}
    episode_dir = os.path.join(AUDIO_STORAGE_PATH, "episodes", str(episode_id))
    os.makedirs(episode_dir, exist_ok=True)
    
    # Calculate target duration (30 seconds minimum, or based on script length)
    word_count = len(script.split())
    target_duration = max(30, int(word_count / 2.5))  # ~2.5 words per second
    
    logger.info(f"Generating {target_duration}-second audio for episode {episode_id}")
    
    try:
        # Generate audio using VibeVoice
        logger.info("🎤 Generating audio with VibeVoice TTS")
        audio_array = vibevoice_tts.generate_speech(script)
        
        # Create temporary WAV file
        temp_wav = os.path.join(episode_dir, "temp_audio.wav")
        
        # Save as WAV first (VibeVoice generates numpy array)
        if audio_array.ndim == 1:
            # Convert mono to stereo
            audio_array = np.stack([audio_array, audio_array], axis=-1)
        
        sf.write(temp_wav, audio_array, SAMPLE_RATE)
        
        # Convert WAV to MP3 using pydub
        audio_segment = AudioSegment.from_wav(temp_wav)
        mp3_path = os.path.join(episode_dir, "audio.mp3")
        
        # Ensure stereo and export as MP3
        audio_segment = audio_segment.set_channels(2)
        audio_segment.export(
            mp3_path,
            format="mp3",
            bitrate=f"{BIT_RATE}k",
            parameters=["-ac", "2"]  # Stereo audio
        )
        
        # Clean up temporary WAV
        os.remove(temp_wav)
        
        logger.info(f"✅ Created VibeVoice MP3 file: {mp3_path}")
        return mp3_path
        
    except Exception as e:
        logger.error(f"❌ VibeVoice generation failed: {e}")
        logger.info("🔄 Falling back to synthetic audio generation")
        
        # Fallback to original synthetic method
        audio_segment = text_to_speech_audio(script, target_duration)
        mp3_path = os.path.join(episode_dir, "audio.mp3")
        
        # Ensure stereo and export as MP3
        audio_segment = audio_segment.set_channels(2)
        audio_segment.export(
            mp3_path,
            format="mp3",
            bitrate=f"{BIT_RATE}k",
            parameters=["-ac", "2"]  # Stereo audio
        )
        
        logger.info(f"Created fallback MP3 file: {mp3_path}")
        return mp3_path


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "presenter-mp3", "timestamp": datetime.utcnow()}


# Global metrics storage (in production, would use Redis or proper metrics store)
METRICS_STORAGE = {
    "total_audio_generated": 0,
    "total_failures": 0,
    "total_duration_seconds": 0,
    "last_generation_time": None
}


@app.get("/metrics/prometheus")
async def get_prometheus_metrics():
    """Prometheus-compatible metrics endpoint."""
    from fastapi.responses import PlainTextResponse
    
    metrics = []
    
    # Audio generation metrics
    metrics.append(f"presenter_audio_generated_total {METRICS_STORAGE['total_audio_generated']}")
    metrics.append(f"presenter_failures_total {METRICS_STORAGE['total_failures']}")
    
    # Duration metrics
    if METRICS_STORAGE["total_audio_generated"] > 0:
        avg_duration = METRICS_STORAGE["total_duration_seconds"] / METRICS_STORAGE["total_audio_generated"]
        metrics.append(f"presenter_audio_duration_seconds {avg_duration}")
    else:
        metrics.append("presenter_audio_duration_seconds 0")
    
    # Last generation timestamp
    if METRICS_STORAGE["last_generation_time"]:
        metrics.append(f"presenter_last_generation_timestamp {METRICS_STORAGE['last_generation_time']}")
    
    prometheus_output = "\n".join([
        "# HELP presenter_audio_generated_total Total audio files generated",
        "# TYPE presenter_audio_generated_total counter",
        "# HELP presenter_failures_total Total generation failures",
        "# TYPE presenter_failures_total counter",
        "# HELP presenter_audio_duration_seconds Average audio duration",
        "# TYPE presenter_audio_duration_seconds gauge",
        "# HELP presenter_last_generation_timestamp Last generation timestamp",
        "# TYPE presenter_last_generation_timestamp gauge",
        "",
        *metrics
    ])
    
    return PlainTextResponse(prometheus_output, media_type="text/plain")


@app.post("/generate-audio", response_model=AudioGenerationResponse)
async def generate_audio(request: AudioGenerationRequest):
    """Generate MP3 audio from script."""
    
    logger.info(f"Generating MP3 audio for episode {request.episode_id}")
    
    try:
        # Create actual MP3 audio file
        audio_path = create_mp3_audio_file(request.episode_id, request.script)
        
        # Get file statistics
        file_size = os.path.getsize(audio_path)
        
        # Calculate actual duration from the audio file
        audio_segment = AudioSegment.from_mp3(audio_path)
        actual_duration = len(audio_segment) / 1000.0  # Convert from milliseconds
        
        generation_metadata = {
            "model_used": "synthetic-speech-generator",
            "voice_settings": request.voice_settings or {},
            "presenter_ids": [str(pid) for pid in request.presenter_ids],
            "generation_timestamp": datetime.utcnow().isoformat(),
            "script_length": len(request.script.split()),
            "sample_rate": SAMPLE_RATE,
            "bit_rate": BIT_RATE,
            "audio_format": "mp3",
            "channels": 2  # Stereo
        }
        
        # Update metrics
        METRICS_STORAGE["total_audio_generated"] += 1
        METRICS_STORAGE["total_duration_seconds"] += actual_duration
        METRICS_STORAGE["last_generation_time"] = datetime.utcnow().timestamp()
        
        return AudioGenerationResponse(
            episode_id=request.episode_id,
            audio_url=f"file://{audio_path}",
            duration_seconds=int(actual_duration),
            file_size_bytes=file_size,
            format="mp3",
            generation_metadata=generation_metadata
        )
        
    except Exception as e:
        logger.error(f"Error generating MP3 audio: {e}")
        METRICS_STORAGE["total_failures"] += 1
        raise HTTPException(status_code=500, detail=f"MP3 audio generation failed: {str(e)}")


@app.post("/test-audio-generation")
async def test_audio_generation(test_text: str = "Hello, this is a test of the text-to-speech system."):
    """Test endpoint for MP3 audio generation."""
    
    try:
        # Create a temporary MP3 file
        episode_id = UUID("12345678-1234-1234-1234-123456789012")
        audio_path = create_mp3_audio_file(episode_id, test_text)
        
        file_size = os.path.getsize(audio_path)
        audio_segment = AudioSegment.from_mp3(audio_path)
        actual_duration = len(audio_segment) / 1000.0
        
        return {
            "audio_url": f"file://{audio_path}",
            "duration_seconds": int(actual_duration),
            "file_size_bytes": file_size,
            "format": "mp3",
            "model_used": "synthetic-speech-generator",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in test audio generation: {e}")
        raise HTTPException(status_code=500, detail=f"Test audio generation failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)
