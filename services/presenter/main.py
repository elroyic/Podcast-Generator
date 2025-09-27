"""
VibeVoice Presenter Service - Generates high-quality MP3 audio files using VibeVoice only.
Service fails if VibeVoice is unavailable - no synthetic fallback for production quality.
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
        """Generate speech from text using VibeVoice only - fail if not available."""
        if not self.use_vibevoice:
            raise Exception("VibeVoice is disabled via USE_VIBEVOICE=false environment variable")
        
        if not self.is_loaded:
            raise Exception("VibeVoice model failed to load. Cannot generate speech without the VibeVoice model.")
        
        return self._generate_vibevoice_speech(text, voice_id)
    
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
            raise Exception(f"VibeVoice speech generation failed: {str(e)}")
    


# Global TTS instance
vibevoice_tts = VibeVoiceTTS()




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
        raise Exception(f"Failed to generate audio with VibeVoice: {str(e)}")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    # Check if VibeVoice is available
    vibevoice_status = "loaded" if vibevoice_tts.is_loaded else "failed"
    vibevoice_enabled = vibevoice_tts.use_vibevoice
    
    # Service is only healthy if VibeVoice is working
    overall_status = "healthy" if (vibevoice_enabled and vibevoice_tts.is_loaded) else "unhealthy"
    
    return {
        "status": overall_status,
        "service": "presenter-vibevoice", 
        "vibevoice_enabled": vibevoice_enabled,
        "vibevoice_status": vibevoice_status,
        "model_loaded": vibevoice_tts.is_loaded,
        "device": str(vibevoice_tts.device),
        "timestamp": datetime.utcnow()
    }


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
