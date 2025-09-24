"""
Simplified Presenter Service for local testing.
This version creates mock audio files without requiring VibeVoice.
"""

import logging
import os
import tempfile
from datetime import datetime
from typing import Dict, Any, Optional, List
from uuid import UUID

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Presenter Service (Simple)", version="1.0.0")

# Configuration
AUDIO_STORAGE_PATH = os.getenv("AUDIO_STORAGE_PATH", "/tmp/podcast_storage/episodes")
SAMPLE_RATE = 22050


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


def create_mock_audio_file(episode_id: UUID, script: str) -> str:
    """Create a mock audio file."""
    
    # Ensure storage directory exists
    os.makedirs(AUDIO_STORAGE_PATH, exist_ok=True)
    
    # Create a simple text file as a mock audio file
    audio_filename = f"episode_{episode_id}_audio.txt"
    audio_path = os.path.join(AUDIO_STORAGE_PATH, audio_filename)
    
    # Write script content as mock audio
    with open(audio_path, 'w') as f:
        f.write(f"Mock Audio File for Episode {episode_id}\n")
        f.write(f"Generated at: {datetime.utcnow()}\n")
        f.write(f"Script content:\n{script}\n")
        f.write(f"This would be actual audio content in a real implementation.\n")
    
    return audio_path


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "presenter-simple", "timestamp": datetime.utcnow()}


@app.post("/generate-audio", response_model=AudioGenerationResponse)
async def generate_audio(request: AudioGenerationRequest):
    """Generate audio from script."""
    
    logger.info(f"Generating audio for episode {request.episode_id}")
    
    try:
        # Create mock audio file
        audio_path = create_mock_audio_file(request.episode_id, request.script)
        
        # Calculate mock metrics
        file_size = os.path.getsize(audio_path)
        
        # Estimate duration based on script length (rough: 150 words per minute)
        word_count = len(request.script.split())
        estimated_duration = max(30, int(word_count / 150 * 60))  # At least 30 seconds
        
        generation_metadata = {
            "model_used": "mock-audio-generator",
            "voice_settings": request.voice_settings or {},
            "presenter_ids": [str(pid) for pid in request.presenter_ids],
            "generation_timestamp": datetime.utcnow().isoformat(),
            "script_length": word_count,
            "sample_rate": SAMPLE_RATE
        }
        
        return AudioGenerationResponse(
            episode_id=request.episode_id,
            audio_url=f"file://{audio_path}",
            duration_seconds=estimated_duration,
            file_size_bytes=file_size,
            format="txt",  # Mock format
            generation_metadata=generation_metadata
        )
        
    except Exception as e:
        logger.error(f"Error generating audio: {e}")
        raise HTTPException(status_code=500, detail=f"Audio generation failed: {str(e)}")


@app.post("/test-audio-generation")
async def test_audio_generation(test_text: str = "Hello, this is a test of the text-to-speech system."):
    """Test endpoint for audio generation."""
    
    # Create a temporary mock audio file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(f"Test Audio File\n")
        f.write(f"Generated at: {datetime.utcnow()}\n")
        f.write(f"Text: {test_text}\n")
        temp_path = f.name
    
    file_size = os.path.getsize(temp_path)
    
    return {
        "audio_url": f"file://{temp_path}",
        "duration_seconds": 30,  # Mock duration
        "file_size_bytes": file_size,
        "format": "txt",
        "model_used": "mock-audio-generator",
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)
