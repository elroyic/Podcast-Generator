"""
Enhanced Presenter Service - Generates actual MP3 audio files.
This version creates real MP3 audio files using pydub and numpy.
"""

import logging
import os
import tempfile
from datetime import datetime
from typing import Dict, Any, Optional, List
from uuid import UUID

import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pydub import AudioSegment
from pydub.generators import Sine, WhiteNoise

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Presenter Service (MP3)", version="1.0.0")

# Configuration
AUDIO_STORAGE_PATH = os.getenv("AUDIO_STORAGE_PATH", "/tmp/podcast_storage/episodes")
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


def text_to_speech_audio(script: str, duration_seconds: int = 30) -> AudioSegment:
    """Generate synthetic speech audio from text."""
    
    # Calculate words per second for natural speech (average ~2.5 words/second)
    words = script.split()
    word_count = len(words)
    natural_duration = max(duration_seconds, word_count / 2.5)
    
    # Generate base audio with multiple sine waves to simulate speech
    base_audio = AudioSegment.silent(duration=int(natural_duration * 1000))  # Convert to milliseconds
    
    # Create speech-like audio using multiple sine waves
    speech_audio = AudioSegment.silent(duration=int(natural_duration * 1000))
    
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
    # Create a more dynamic audio by varying the volume over time
    final_audio = AudioSegment.silent(duration=int(natural_duration * 1000))
    
    # Split into chunks and vary volume to simulate speech patterns
    chunk_duration = 500  # 0.5 seconds
    for i in range(0, len(speech_audio), chunk_duration):
        chunk = speech_audio[i:i + chunk_duration]
        
        # Vary volume to simulate speech rhythm
        volume_variation = np.sin(i / 1000 * 2 * np.pi) * 5  # ±5dB variation
        chunk = chunk + volume_variation
        
        # Add some silence between "words"
        if i % 2000 == 0:  # Every 2 seconds
            silence = AudioSegment.silent(duration=100)  # 100ms pause
            final_audio = final_audio + chunk + silence
        else:
            final_audio = final_audio + chunk
    
    return final_audio


def create_mp3_audio_file(episode_id: UUID, script: str) -> str:
    """Create an actual MP3 audio file from script."""
    
    # Ensure storage directory exists
    os.makedirs(AUDIO_STORAGE_PATH, exist_ok=True)
    
    # Calculate target duration (30 seconds minimum, or based on script length)
    word_count = len(script.split())
    target_duration = max(30, int(word_count / 2.5))  # ~2.5 words per second
    
    logger.info(f"Generating {target_duration}-second audio for episode {episode_id}")
    
    # Generate synthetic speech audio
    audio_segment = text_to_speech_audio(script, target_duration)
    
    # Create MP3 filename
    mp3_filename = f"episode_{episode_id}_audio.mp3"
    mp3_path = os.path.join(AUDIO_STORAGE_PATH, mp3_filename)
    
    # Export as MP3
    audio_segment.export(
        mp3_path,
        format="mp3",
        bitrate=f"{BIT_RATE}k",
        parameters=["-ac", "1"]  # Mono audio
    )
    
    logger.info(f"Created MP3 file: {mp3_path}")
    return mp3_path


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "presenter-mp3", "timestamp": datetime.utcnow()}


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
            "channels": 1
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
        logger.error(f"Error generating MP3 audio: {e}")
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
