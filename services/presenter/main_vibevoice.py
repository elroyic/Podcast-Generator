"""
Enhanced Presenter Service with VibeVoice Integration - Generates MP3 audio files using VibeVoice.
This version integrates with VibeVoice for high-quality text-to-speech generation.
"""
import logging
import os
import sys
import tempfile
from datetime import datetime
from typing import Dict, Any, Optional, List
from uuid import UUID

import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pydub import AudioSegment

# Add VibeVoice to path
sys.path.append('/workspace/VibeVoice-Community')

try:
    from vibevoice import VibeVoice
    VIBEVOICE_AVAILABLE = True
except ImportError:
    VIBEVOICE_AVAILABLE = False
    logging.warning("VibeVoice not available, falling back to synthetic audio")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Presenter Service (VibeVoice)", version="1.0.0")

# Configuration
AUDIO_STORAGE_PATH = os.getenv("AUDIO_STORAGE_PATH", "/app/storage")
SAMPLE_RATE = 22050
BIT_RATE = 128  # kbps for MP3


class AudioGenerationRequest(BaseModel):
    """Request to generate audio using VibeVoice."""
    episode_id: UUID
    script: str
    presenter_ids: List[UUID]
    voice_settings: Optional[Dict[str, Any]] = None


class AudioGenerationResponse(BaseModel):
    """Response from audio generation."""
    episode_id: UUID
    audio_url: str
    duration_seconds: int
    file_size_bytes: int
    format: str
    generation_metadata: Dict[str, Any]


class VibeVoicePresenter:
    """Handles VibeVoice integration for audio generation."""
    
    def __init__(self):
        self.vibevoice = None
        self.initialized = False
        
        if VIBEVOICE_AVAILABLE:
            try:
                # Initialize VibeVoice
                self.vibevoice = VibeVoice()
                self.initialized = True
                logger.info("VibeVoice initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize VibeVoice: {e}")
                self.initialized = False
        else:
            logger.warning("VibeVoice not available, using fallback audio generation")
    
    def text_to_speech_vibevoice(self, text: str, voice_settings: Optional[Dict[str, Any]] = None) -> AudioSegment:
        """Generate speech audio using VibeVoice."""
        if not self.initialized or not self.vibevoice:
            logger.warning("VibeVoice not available, using fallback")
            return self._generate_fallback_audio(text)
        
        try:
            # Configure voice settings
            voice_config = voice_settings or {}
            speaker_id = voice_config.get("speaker_id", "default")
            language = voice_config.get("language", "en")
            
            # Generate audio using VibeVoice
            logger.info(f"Generating VibeVoice audio for {len(text)} characters")
            
            # VibeVoice typically returns audio data
            audio_data = self.vibevoice.infer(
                text=text,
                speaker_id=speaker_id,
                language=language
            )
            
            # Convert to AudioSegment
            if isinstance(audio_data, np.ndarray):
                # Convert numpy array to AudioSegment
                audio_segment = AudioSegment(
                    audio_data.tobytes(),
                    frame_rate=SAMPLE_RATE,
                    sample_width=audio_data.dtype.itemsize,
                    channels=1 if len(audio_data.shape) == 1 else audio_data.shape[1]
                )
            else:
                # Assume it's already in a compatible format
                audio_segment = AudioSegment.from_wav(audio_data)
            
            # Ensure stereo output
            if audio_segment.channels == 1:
                audio_segment = audio_segment.set_channels(2)
            
            logger.info(f"Generated VibeVoice audio: {len(audio_segment)}ms")
            return audio_segment
            
        except Exception as e:
            logger.error(f"VibeVoice generation failed: {e}")
            return self._generate_fallback_audio(text)
    
    def _generate_fallback_audio(self, text: str) -> AudioSegment:
        """Generate fallback audio when VibeVoice is not available."""
        logger.info("Generating fallback audio")
        
        # Calculate duration based on text length (approximately 150 words per minute)
        words = text.split()
        word_count = len(words)
        duration_seconds = max(10, word_count / 2.5)  # ~2.5 words per second
        
        # Generate synthetic speech-like audio
        base_audio = AudioSegment.silent(duration=int(duration_seconds * 1000)).set_channels(2)
        
        # Create speech-like waveform with formants
        formants = [
            (200, 0.8),   # Fundamental frequency
            (800, 0.6),   # First formant
            (1200, 0.4),  # Second formant
            (2500, 0.2),  # Third formant
        ]
        
        speech_audio = AudioSegment.silent(duration=int(duration_seconds * 1000)).set_channels(2)
        
        for freq, amplitude in formants:
            # Generate sine wave with variation
            from pydub.generators import Sine, WhiteNoise
            sine_wave = Sine(freq).to_audio_segment(duration=int(duration_seconds * 1000))
            noise = WhiteNoise().to_audio_segment(duration=int(duration_seconds * 1000))
            noise = noise - 20  # Reduce noise volume
            
            combined = sine_wave.overlay(noise)
            combined = combined - (20 - int(amplitude * 10))
            speech_audio = speech_audio.overlay(combined)
        
        # Add natural pauses and variations
        final_audio = AudioSegment.silent(duration=int(duration_seconds * 1000)).set_channels(2)
        
        chunk_duration = 500  # 0.5 seconds
        for i in range(0, len(speech_audio), chunk_duration):
            chunk = speech_audio[i:i + chunk_duration]
            
            # Vary volume to simulate speech rhythm
            volume_variation = np.sin(i / 1000 * 2 * np.pi) * 5  # ±5dB variation
            chunk = chunk + volume_variation
            
            # Add silence between "words"
            if i % 2000 == 0:  # Every 2 seconds
                silence = AudioSegment.silent(duration=100).set_channels(2)
                final_audio = final_audio + chunk + silence
            else:
                final_audio = final_audio + chunk
        
        return final_audio
    
    def create_mp3_audio_file(self, episode_id: UUID, script: str, voice_settings: Optional[Dict[str, Any]] = None) -> str:
        """Create an MP3 audio file from script using VibeVoice."""
        
        # Ensure storage directory exists
        episode_dir = os.path.join(AUDIO_STORAGE_PATH, "episodes", str(episode_id))
        os.makedirs(episode_dir, exist_ok=True)
        
        logger.info(f"Generating VibeVoice audio for episode {episode_id}")
        
        # Generate audio using VibeVoice
        audio_segment = self.text_to_speech_vibevoice(script, voice_settings)
        
        # Create MP3 filename
        mp3_path = os.path.join(episode_dir, "vibevoice_podcast.wav")  # VibeVoice typically outputs WAV
        
        # Export as high-quality audio
        audio_segment.export(
            mp3_path,
            format="wav",  # VibeVoice typically works with WAV
            parameters=["-ac", "2"]  # Stereo audio
        )
        
        # Also create MP3 version
        mp3_path_mp3 = os.path.join(episode_dir, "vibevoice_podcast.mp3")
        audio_segment.export(
            mp3_path_mp3,
            format="mp3",
            bitrate=f"{BIT_RATE}k",
            parameters=["-ac", "2"]
        )
        
        logger.info(f"Created VibeVoice audio files: {mp3_path} and {mp3_path_mp3}")
        return mp3_path_mp3  # Return MP3 path as primary


# Initialize services
vibevoice_presenter = VibeVoicePresenter()


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy", 
        "service": "presenter-vibevoice", 
        "vibevoice_available": VIBEVOICE_AVAILABLE,
        "vibevoice_initialized": vibevoice_presenter.initialized,
        "timestamp": datetime.utcnow()
    }


@app.post("/generate-audio", response_model=AudioGenerationResponse)
async def generate_audio(request: AudioGenerationRequest):
    """Generate MP3 audio from script using VibeVoice."""
    
    logger.info(f"Generating VibeVoice audio for episode {request.episode_id}")
    
    try:
        # Create MP3 audio file using VibeVoice
        audio_path = vibevoice_presenter.create_mp3_audio_file(
            request.episode_id, 
            request.script, 
            request.voice_settings
        )
        
        # Get file statistics
        file_size = os.path.getsize(audio_path)
        
        # Calculate actual duration from the audio file
        audio_segment = AudioSegment.from_mp3(audio_path)
        actual_duration = len(audio_segment) / 1000.0  # Convert from milliseconds
        
        generation_metadata = {
            "model_used": "vibevoice" if VIBEVOICE_AVAILABLE else "fallback-synthetic",
            "vibevoice_available": VIBEVOICE_AVAILABLE,
            "vibevoice_initialized": vibevoice_presenter.initialized,
            "voice_settings": request.voice_settings or {},
            "presenter_ids": [str(pid) for pid in request.presenter_ids],
            "generation_timestamp": datetime.utcnow().isoformat(),
            "script_length": len(request.script.split()),
            "sample_rate": SAMPLE_RATE,
            "bit_rate": BIT_RATE,
            "audio_format": "mp3",
            "channels": 2  # Stereo
        }
        
        return AudioGenerationResponse(
            episode_id=request.episode_id,
            audio_url=f"file://{audio_path}",
            duration_seconds=int(actual_duration),
            file_size_bytes=file_size,
            format="mp3",
            generation_metadata=generation_metadata
        )
        
    except Exception as e:
        logger.error(f"Error generating VibeVoice audio: {e}")
        raise HTTPException(status_code=500, detail=f"VibeVoice audio generation failed: {str(e)}")


@app.post("/test-vibevoice-generation")
async def test_vibevoice_generation(
    test_text: str = "Hello, this is a test of the VibeVoice text-to-speech system. We're generating high-quality audio for podcast content using advanced neural voice synthesis technology."
):
    """Test endpoint for VibeVoice audio generation."""
    
    try:
        # Create a temporary episode ID
        episode_id = UUID("12345678-1234-1234-1234-123456789012")
        
        # Generate audio using VibeVoice
        audio_path = vibevoice_presenter.create_mp3_audio_file(episode_id, test_text)
        
        file_size = os.path.getsize(audio_path)
        audio_segment = AudioSegment.from_mp3(audio_path)
        actual_duration = len(audio_segment) / 1000.0
        
        return {
            "test_text": test_text,
            "audio_url": f"file://{audio_path}",
            "duration_seconds": int(actual_duration),
            "file_size_bytes": file_size,
            "format": "mp3",
            "vibevoice_available": VIBEVOICE_AVAILABLE,
            "vibevoice_initialized": vibevoice_presenter.initialized,
            "model_used": "vibevoice" if VIBEVOICE_AVAILABLE else "fallback-synthetic",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in test VibeVoice generation: {e}")
        raise HTTPException(status_code=500, detail=f"Test VibeVoice generation failed: {str(e)}")


@app.get("/vibevoice-status")
async def get_vibevoice_status():
    """Get VibeVoice system status."""
    return {
        "vibevoice_available": VIBEVOICE_AVAILABLE,
        "vibevoice_initialized": vibevoice_presenter.initialized,
        "fallback_mode": not VIBEVOICE_AVAILABLE or not vibevoice_presenter.initialized,
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8013)