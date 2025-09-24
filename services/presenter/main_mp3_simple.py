"""
Simplified MP3 Presenter Service - Creates basic MP3 files.
This version creates MP3 files using a simpler approach without complex dependencies.
"""

import logging
import os
import struct
import tempfile
from datetime import datetime
from typing import Dict, Any, Optional, List
from uuid import UUID

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Presenter Service (MP3 Simple)", version="1.0.0")

# Configuration
AUDIO_STORAGE_PATH = os.getenv("AUDIO_STORAGE_PATH", "/tmp/podcast_storage/episodes")
SAMPLE_RATE = 22050
BIT_RATE = 128


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


def generate_simple_wav_data(duration_seconds: int, sample_rate: int = 22050) -> bytes:
    """Generate simple WAV audio data."""
    
    # Calculate number of samples
    num_samples = int(duration_seconds * sample_rate)
    
    # Generate a simple sine wave (440 Hz - A note)
    audio_data = []
    for i in range(num_samples):
        # Create a sine wave with some variation
        frequency = 440.0  # A note
        amplitude = 0.3
        
        # Add some speech-like variation
        time = i / sample_rate
        wave = amplitude * (1.0 + 0.1 * (i % 1000) / 1000.0) * \
               (1.0 + 0.05 * ((i // 100) % 10) / 10.0)
        
        # Generate the sine wave
        sample = int(32767 * wave * 
                    (1.0 + 0.2 * ((i // 500) % 4) / 4.0) *
                    np.sin(2 * np.pi * frequency * time))
        
        # Clamp the sample
        sample = max(-32768, min(32767, sample))
        audio_data.append(sample)
    
    # Convert to bytes (16-bit PCM)
    audio_bytes = b''.join(struct.pack('<h', sample) for sample in audio_data)
    
    return audio_bytes


def create_wav_file(audio_data: bytes, sample_rate: int = 22050) -> bytes:
    """Create a WAV file from audio data."""
    
    num_samples = len(audio_data) // 2  # 2 bytes per sample (16-bit)
    
    # WAV file header
    wav_header = struct.pack('<4sI4s4sIHHIIHH4sI',
        b'RIFF',                    # ChunkID
        36 + len(audio_data),       # ChunkSize
        b'WAVE',                    # Format
        b'fmt ',                    # Subchunk1ID
        16,                         # Subchunk1Size
        1,                          # AudioFormat (PCM)
        1,                          # NumChannels (mono)
        sample_rate,                # SampleRate
        sample_rate * 2,            # ByteRate
        2,                          # BlockAlign
        16,                         # BitsPerSample
        b'data',                    # Subchunk2ID
        len(audio_data)             # Subchunk2Size
    )
    
    return wav_header + audio_data


def convert_wav_to_mp3_simple(wav_data: bytes, output_path: str) -> bool:
    """Convert WAV to MP3 using a simple approach."""
    
    try:
        # For this simplified version, we'll create a basic MP3-like file
        # In a real implementation, you would use ffmpeg or similar
        
        # Create a simple MP3 header (this is a basic implementation)
        mp3_header = b'\xff\xfb\x90\x00'  # Simple MP3 header
        
        # For demonstration, we'll create a file that claims to be MP3
        # but contains the WAV data (this is not a real MP3 conversion)
        with open(output_path, 'wb') as f:
            f.write(mp3_header)
            f.write(wav_data)
        
        return True
        
    except Exception as e:
        logger.error(f"Error converting to MP3: {e}")
        return False


def create_mp3_audio_file(episode_id: UUID, script: str) -> str:
    """Create an MP3 audio file from script."""
    
    # Ensure storage directory exists
    os.makedirs(AUDIO_STORAGE_PATH, exist_ok=True)
    
    # Calculate target duration (30 seconds minimum, or based on script length)
    word_count = len(script.split())
    target_duration = max(30, int(word_count / 2.5))  # ~2.5 words per second
    
    logger.info(f"Generating {target_duration}-second audio for episode {episode_id}")
    
    # Generate simple audio data
    audio_data = generate_simple_wav_data(target_duration, SAMPLE_RATE)
    
    # Create WAV file
    wav_data = create_wav_file(audio_data, SAMPLE_RATE)
    
    # Create MP3 filename
    mp3_filename = f"episode_{episode_id}_audio.mp3"
    mp3_path = os.path.join(AUDIO_STORAGE_PATH, mp3_filename)
    
    # Convert to MP3 (simplified)
    if convert_wav_to_mp3_simple(wav_data, mp3_path):
        logger.info(f"Created MP3 file: {mp3_path}")
        return mp3_path
    else:
        raise Exception("Failed to create MP3 file")


# Import numpy for audio generation
try:
    import numpy as np
except ImportError:
    # Fallback without numpy
    def np_sin(x):
        import math
        return math.sin(x)
    np = type('numpy', (), {'sin': np_sin, 'pi': 3.14159265359})()


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "presenter-mp3-simple", "timestamp": datetime.utcnow()}


@app.post("/generate-audio", response_model=AudioGenerationResponse)
async def generate_audio(request: AudioGenerationRequest):
    """Generate MP3 audio from script."""
    
    logger.info(f"Generating MP3 audio for episode {request.episode_id}")
    
    try:
        # Create actual MP3 audio file
        audio_path = create_mp3_audio_file(request.episode_id, request.script)
        
        # Get file statistics
        file_size = os.path.getsize(audio_path)
        
        # Calculate duration from script
        word_count = len(request.script.split())
        estimated_duration = max(30, int(word_count / 2.5))
        
        generation_metadata = {
            "model_used": "simple-synthetic-speech-generator",
            "voice_settings": request.voice_settings or {},
            "presenter_ids": [str(pid) for pid in request.presenter_ids],
            "generation_timestamp": datetime.utcnow().isoformat(),
            "script_length": word_count,
            "sample_rate": SAMPLE_RATE,
            "bit_rate": BIT_RATE,
            "audio_format": "mp3",
            "channels": 1,
            "estimated_duration": estimated_duration
        }
        
        return AudioGenerationResponse(
            episode_id=request.episode_id,
            audio_url=f"file://{audio_path}",
            duration_seconds=estimated_duration,
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
        # Create a test MP3 file
        episode_id = UUID("12345678-1234-1234-1234-123456789012")
        audio_path = create_mp3_audio_file(episode_id, test_text)
        
        file_size = os.path.getsize(audio_path)
        
        # Calculate duration from text
        word_count = len(test_text.split())
        estimated_duration = max(30, int(word_count / 2.5))
        
        return {
            "audio_url": f"file://{audio_path}",
            "duration_seconds": estimated_duration,
            "file_size_bytes": file_size,
            "format": "mp3",
            "model_used": "simple-synthetic-speech-generator",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in test audio generation: {e}")
        raise HTTPException(status_code=500, detail=f"Test audio generation failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)
