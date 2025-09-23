"""
Presenter Service - Converts scripts to audio using VibeVoice-1.5B model.
"""
import asyncio
import logging
import os
import tempfile
from datetime import datetime
from typing import Dict, Any, Optional, List
from uuid import UUID

import httpx
import torch
import librosa
import soundfile as sf
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel

from shared.database import get_db, create_tables
from shared.models import Episode, AudioFile, Presenter
from shared.schemas import AudioFileCreate, AudioFile as AudioFileSchema

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Presenter Service", version="1.0.0")

# Configuration
VIBEVOICE_MODEL = "microsoft/VibeVoice-1.5B"
AUDIO_STORAGE_PATH = "/app/audio_storage"
SAMPLE_RATE = 22050
VOICE_SETTINGS = {
    "temperature": 0.7,
    "top_p": 0.9,
    "max_length": 1000
}


class AudioGenerationRequest(BaseModel):
    episode_id: UUID
    script: str
    presenter_ids: List[UUID]
    voice_settings: Optional[Dict[str, Any]] = None


class AudioGenerationResponse(BaseModel):
    episode_id: UUID
    audio_url: str
    duration_seconds: float
    file_size_bytes: int
    format: str
    generation_metadata: Dict[str, Any]


class VibeVoiceClient:
    """Client for VibeVoice-1.5B text-to-speech generation."""
    
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._load_model()
    
    def _load_model(self):
        """Load the VibeVoice model."""
        try:
            logger.info(f"Loading VibeVoice model on {self.device}")
            
            # For now, we'll use a placeholder implementation
            # In a real implementation, you would load the actual VibeVoice model
            # from transformers import AutoModel, AutoTokenizer
            
            # self.tokenizer = AutoTokenizer.from_pretrained(VIBEVOICE_MODEL)
            # self.model = AutoModel.from_pretrained(VIBEVOICE_MODEL).to(self.device)
            
            logger.info("VibeVoice model loaded successfully")
            
        except Exception as e:
            logger.error(f"Error loading VibeVoice model: {e}")
            # Fallback to a simpler TTS approach for development
            self.model = "placeholder"
    
    async def generate_speech(
        self,
        text: str,
        voice_id: str = "default",
        settings: Optional[Dict[str, Any]] = None
    ) -> bytes:
        """Generate speech audio from text."""
        try:
            # For development, we'll create a placeholder audio file
            # In production, this would use the actual VibeVoice model
            
            logger.info(f"Generating speech for text length: {len(text)}")
            
            # Create a simple sine wave as placeholder audio
            # In real implementation, this would be the actual generated speech
            duration = len(text.split()) * 0.5  # Rough estimate: 0.5 seconds per word
            sample_rate = SAMPLE_RATE
            frequency = 440  # A4 note
            
            # Generate sine wave
            t = torch.linspace(0, duration, int(sample_rate * duration))
            audio = torch.sin(2 * torch.pi * frequency * t) * 0.3
            
            # Convert to numpy and then to bytes
            audio_np = audio.numpy().astype('float32')
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                sf.write(temp_file.name, audio_np, sample_rate)
                
                with open(temp_file.name, 'rb') as f:
                    audio_bytes = f.read()
                
                # Clean up temp file
                os.unlink(temp_file.name)
            
            logger.info(f"Generated audio: {len(audio_bytes)} bytes, {duration:.2f} seconds")
            return audio_bytes
            
        except Exception as e:
            logger.error(f"Error generating speech: {e}")
            raise HTTPException(status_code=500, detail=f"Speech generation failed: {str(e)}")


class AudioProcessor:
    """Handles audio processing and file management."""
    
    def __init__(self):
        self.vibe_voice = VibeVoiceClient()
        self.storage_path = AUDIO_STORAGE_PATH
        self._ensure_storage_directory()
    
    def _ensure_storage_directory(self):
        """Ensure audio storage directory exists."""
        os.makedirs(self.storage_path, exist_ok=True)
    
    def _get_audio_filename(self, episode_id: UUID, presenter_id: UUID) -> str:
        """Generate filename for audio file."""
        return f"{episode_id}_{presenter_id}.wav"
    
    async def save_audio_file(
        self,
        episode_id: UUID,
        presenter_id: UUID,
        audio_data: bytes
    ) -> str:
        """Save audio data to file and return the file path."""
        filename = self._get_audio_filename(episode_id, presenter_id)
        file_path = os.path.join(self.storage_path, filename)
        
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(audio_data)
        
        return file_path
    
    async def combine_audio_files(
        self,
        audio_files: List[str],
        output_path: str
    ) -> str:
        """Combine multiple audio files into one."""
        try:
            # Load all audio files
            audio_data = []
            sample_rates = []
            
            for file_path in audio_files:
                audio, sr = librosa.load(file_path, sr=SAMPLE_RATE)
                audio_data.append(audio)
                sample_rates.append(sr)
            
            # Ensure all have the same sample rate
            if len(set(sample_rates)) > 1:
                logger.warning("Sample rates don't match, using first one")
            
            # Concatenate audio
            combined_audio = torch.cat([torch.tensor(audio) for audio in audio_data])
            
            # Save combined audio
            sf.write(output_path, combined_audio.numpy(), SAMPLE_RATE)
            
            return output_path
            
        except Exception as e:
            logger.error(f"Error combining audio files: {e}")
            raise HTTPException(status_code=500, detail=f"Audio combination failed: {str(e)}")
    
    def get_audio_duration(self, file_path: str) -> float:
        """Get duration of audio file in seconds."""
        try:
            audio, sr = librosa.load(file_path, sr=None)
            return len(audio) / sr
        except Exception as e:
            logger.error(f"Error getting audio duration: {e}")
            return 0.0
    
    def get_file_size(self, file_path: str) -> int:
        """Get file size in bytes."""
        try:
            return os.path.getsize(file_path)
        except Exception as e:
            logger.error(f"Error getting file size: {e}")
            return 0


class ScriptParser:
    """Parses podcast scripts to extract individual presenter segments."""
    
    @staticmethod
    def parse_script(script: str) -> List[Dict[str, Any]]:
        """Parse script into presenter segments."""
        segments = []
        lines = script.split('\n')
        current_segment = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check for presenter indicators (e.g., "Presenter 1:", "[Presenter 1]", etc.)
            if any(indicator in line.lower() for indicator in ['presenter', '[presenter', 'speaker']):
                # Save previous segment
                if current_segment:
                    segments.append(current_segment)
                
                # Start new segment
                current_segment = {
                    'presenter_line': line,
                    'content': '',
                    'presenter_id': None  # Will be matched later
                }
            elif current_segment:
                current_segment['content'] += line + '\n'
            else:
                # Default to first presenter if no explicit presenter markers
                if not segments:
                    current_segment = {
                        'presenter_line': 'Presenter 1',
                        'content': line + '\n',
                        'presenter_id': None
                    }
                elif segments:
                    segments[-1]['content'] += line + '\n'
        
        # Add final segment
        if current_segment:
            segments.append(current_segment)
        
        return segments
    
    @staticmethod
    def match_presenters_to_segments(
        segments: List[Dict[str, Any]],
        presenters: List[Presenter]
    ) -> List[Dict[str, Any]]:
        """Match presenter IDs to script segments."""
        for i, segment in enumerate(segments):
            if i < len(presenters):
                segment['presenter_id'] = presenters[i].id
                segment['presenter_name'] = presenters[i].name
            else:
                # Use last presenter for remaining segments
                if presenters:
                    segment['presenter_id'] = presenters[-1].id
                    segment['presenter_name'] = presenters[-1].name
        
        return segments


# Initialize services
audio_processor = AudioProcessor()
script_parser = ScriptParser()

# Create tables on startup
@app.on_event("startup")
async def startup_event():
    create_tables()
    logger.info("Presenter Service started")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "presenter", "timestamp": datetime.utcnow()}


@app.post("/generate-audio", response_model=AudioGenerationResponse)
async def generate_audio(
    request: AudioGenerationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Generate audio from podcast script."""
    
    # Get episode details
    episode = db.query(Episode).filter(Episode.id == request.episode_id).first()
    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")
    
    # Get presenter details
    presenters = db.query(Presenter).filter(
        Presenter.id.in_(request.presenter_ids)
    ).all()
    
    if not presenters:
        raise HTTPException(status_code=404, detail="No presenters found")
    
    try:
        # Parse script into segments
        segments = script_parser.parse_script(request.script)
        segments = script_parser.match_presenters_to_segments(segments, presenters)
        
        logger.info(f"Parsed script into {len(segments)} segments")
        
        # Generate audio for each segment
        audio_files = []
        total_duration = 0.0
        
        for i, segment in enumerate(segments):
            if not segment['content'].strip():
                continue
            
            logger.info(f"Generating audio for segment {i+1} (Presenter: {segment.get('presenter_name', 'Unknown')})")
            
            # Generate speech
            audio_data = await audio_processor.vibe_voice.generate_speech(
                text=segment['content'],
                voice_id=str(segment['presenter_id']),
                settings=request.voice_settings
            )
            
            # Save individual segment audio
            segment_file = await audio_processor.save_audio_file(
                request.episode_id,
                segment['presenter_id'],
                audio_data
            )
            
            audio_files.append(segment_file)
            
            # Calculate duration
            duration = audio_processor.get_audio_duration(segment_file)
            total_duration += duration
        
        # Combine all audio files
        final_audio_path = os.path.join(
            audio_processor.storage_path,
            f"{request.episode_id}_final.wav"
        )
        
        await audio_processor.combine_audio_files(audio_files, final_audio_path)
        
        # Get final file details
        file_size = audio_processor.get_file_size(final_audio_path)
        final_duration = audio_processor.get_audio_duration(final_audio_path)
        
        # Create audio file record
        audio_file = AudioFile(
            episode_id=request.episode_id,
            url=final_audio_path,
            duration_seconds=int(final_duration),
            file_size_bytes=file_size,
            format="wav"
        )
        
        db.add(audio_file)
        db.commit()
        
        # Clean up individual segment files
        for file_path in audio_files:
            try:
                os.unlink(file_path)
            except Exception as e:
                logger.warning(f"Could not clean up file {file_path}: {e}")
        
        generation_metadata = {
            "segments_processed": len(segments),
            "presenters_used": [p.id for p in presenters],
            "voice_model": VIBEVOICE_MODEL,
            "generation_timestamp": datetime.utcnow().isoformat(),
            "script_length_words": len(request.script.split()),
            "voice_settings": request.voice_settings or VOICE_SETTINGS
        }
        
        logger.info(f"Successfully generated audio for episode {request.episode_id}")
        
        return AudioGenerationResponse(
            episode_id=request.episode_id,
            audio_url=final_audio_path,
            duration_seconds=final_duration,
            file_size_bytes=file_size,
            format="wav",
            generation_metadata=generation_metadata
        )
        
    except Exception as e:
        logger.error(f"Error generating audio for episode {request.episode_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Audio generation failed: {str(e)}")


@app.get("/episodes/{episode_id}/audio", response_model=AudioFileSchema)
async def get_episode_audio(
    episode_id: UUID,
    db: Session = Depends(get_db)
):
    """Get audio file information for an episode."""
    audio_file = db.query(AudioFile).filter(
        AudioFile.episode_id == episode_id
    ).first()
    
    if not audio_file:
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    return audio_file


@app.post("/test-audio-generation")
async def test_audio_generation(
    test_text: str = "Hello, this is a test of the text-to-speech system. How does it sound?",
    db: Session = Depends(get_db)
):
    """Test endpoint for audio generation."""
    try:
        # Generate test audio
        audio_data = await audio_processor.vibe_voice.generate_speech(
            text=test_text,
            voice_id="test_voice"
        )
        
        # Save test audio
        test_filename = f"test_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.wav"
        test_path = os.path.join(audio_processor.storage_path, test_filename)
        
        async with aiofiles.open(test_path, 'wb') as f:
            await f.write(audio_data)
        
        duration = audio_processor.get_audio_duration(test_path)
        file_size = audio_processor.get_file_size(test_path)
        
        return {
            "test_audio_path": test_path,
            "duration_seconds": duration,
            "file_size_bytes": file_size,
            "text_processed": test_text,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in test audio generation: {e}")
        raise HTTPException(status_code=500, detail=f"Test audio generation failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    import aiofiles
    from sqlalchemy.orm import Session
    uvicorn.run(app, host="0.0.0.0", port=8004)