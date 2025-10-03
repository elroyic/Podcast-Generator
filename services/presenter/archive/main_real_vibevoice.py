#!/usr/bin/env python3
"""
Real VibeVoice Presenter Service - Uses actual VibeVoice-1.5B for high-quality stereo podcast generation.
This implementation uses the real VibeVoice model for generating human-like speech with stereo output.
"""

import logging
import os
import tempfile
import numpy as np
import soundfile as sf
from datetime import datetime
from typing import Dict, Any, Optional, List
from uuid import UUID

import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Real VibeVoice Presenter Service", version="1.0.0")

# Configuration
AUDIO_STORAGE_PATH = os.getenv("AUDIO_STORAGE_PATH", "./generated_episodes")
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


class RealVibeVoiceTTS:
    """Real VibeVoice Text-to-Speech implementation."""
    
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = None
        self.processor = None
        self.is_loaded = False
        self._load_model()
    
    def _load_model(self):
        """Load the actual VibeVoice model."""
        try:
            logger.info(f"Loading VibeVoice model on {self.device}")
            
            # Import VibeVoice components with correct paths
            from vibevoice.modular.modeling_vibevoice_inference import VibeVoiceForConditionalGenerationInference
            from vibevoice.processor.vibevoice_processor import VibeVoiceProcessor
            
            logger.info("Loading VibeVoice model from HuggingFace...")
            self.model = VibeVoiceForConditionalGenerationInference.from_pretrained("vibevoice/VibeVoice-1.5B")
            self.processor = VibeVoiceProcessor.from_pretrained("vibevoice/VibeVoice-1.5B")
            
            self.model = self.model.to(self.device)
            self.is_loaded = True
            logger.info("VibeVoice model loaded successfully!")
            
        except ImportError as e:
            logger.error(f"VibeVoice not available: {e}")
            logger.error("Please ensure VibeVoice is properly installed")
            self.is_loaded = False
        except Exception as e:
            logger.error(f"Failed to load VibeVoice model: {e}")
            self.is_loaded = False
    
    def generate_speech(self, text: str, voice_id: str = "Alice") -> bytes:
        """Generate high-quality stereo speech from text using VibeVoice."""
        if not self.is_loaded:
            raise Exception("VibeVoice model not loaded. Cannot generate speech without the actual model.")
        
        try:
            logger.info(f"Generating speech with VibeVoice for speaker: {voice_id}")
            logger.info(f"Text length: {len(text)} characters")
            
            # Check if text already has speaker labels
            if not text.startswith("Speaker "):
                # Format text for VibeVoice (Speaker format)
                formatted_text = f"Speaker 1: {text}"
            else:
                formatted_text = text
            
            logger.info(f"Formatted text preview: {formatted_text[:200]}...")
            
            # Get voice samples for multiple speakers if needed
            voice_samples = self._get_voice_samples_for_text(formatted_text)
            
            # Process input text and voice samples
            inputs = self.processor(
                text=[formatted_text],
                voice_samples=[voice_samples],
                padding=True,
                return_tensors="pt",
                return_attention_mask=True,
            )
            
            # Move inputs to device
            for k, v in inputs.items():
                if torch.is_tensor(v):
                    inputs[k] = v.to(self.device)
            
            # Set model to eval mode and configure inference steps
            self.model.eval()
            self.model.set_ddpm_inference_steps(num_steps=10)
            
            # Generate speech with VibeVoice
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=None,
                    cfg_scale=1.0,
                    tokenizer=self.processor.tokenizer,
                    generation_config={'do_sample': False},
                    verbose=False,
                )
            
            # Extract audio from outputs
            if outputs.speech_outputs and outputs.speech_outputs[0] is not None:
                audio_tensor = outputs.speech_outputs[0]
                audio = audio_tensor.cpu().numpy()
                
                # Convert to stereo if mono
                if len(audio.shape) == 1:
                    audio = np.stack([audio, audio], axis=1)  # Convert to stereo
                elif audio.shape[1] == 1:
                    audio = np.repeat(audio, 2, axis=1)  # Duplicate to stereo
                
                # Convert to WAV bytes with stereo output
                return self._numpy_to_stereo_wav_bytes(audio, 24000)  # VibeVoice uses 24kHz
            else:
                raise Exception("No audio output generated by VibeVoice")
            
        except Exception as e:
            logger.error(f"Error generating speech with VibeVoice: {e}")
            raise Exception(f"VibeVoice speech generation failed: {str(e)}")
    
    def _get_voice_samples_for_text(self, text: str) -> List[str]:
        """Get voice samples for all speakers in the text."""
        # Count unique speakers in the text
        import re
        speaker_matches = re.findall(r'Speaker (\d+):', text)
        unique_speakers = list(set(speaker_matches))
        
        logger.info(f"Found {len(unique_speakers)} unique speakers: {unique_speakers}")
        
        voice_samples = []
        voices_dir = os.path.join(os.path.dirname(__file__), "..", "..", "VibeVoice-Community", "demo", "voices")
        
        # Available voice files
        available_voices = [
            "en-Alice_woman.wav",
            "en-Frank_man.wav",
            "en-Carter_man.wav",
            "en-Maya_woman.wav"
        ]
        
        for i, speaker_num in enumerate(sorted(unique_speakers)):
            voice_file = available_voices[i % len(available_voices)]
            voice_path = os.path.join(voices_dir, voice_file)
            
            if os.path.exists(voice_path):
                voice_samples.append(voice_path)
                logger.info(f"Speaker {speaker_num} -> {voice_file}")
            else:
                # Fallback to first available voice
                fallback_voice = os.path.join(voices_dir, available_voices[0])
                if os.path.exists(fallback_voice):
                    voice_samples.append(fallback_voice)
                    logger.warning(f"Speaker {speaker_num} -> fallback to {available_voices[0]}")
        
        if not voice_samples:
            raise Exception("No voice samples found. Please ensure voice samples are available.")
        
        return voice_samples
    
    def _get_voice_sample(self, voice_name: str = "Alice") -> List[str]:
        """Get voice sample path for the given voice name."""
        # Use default Alice voice from VibeVoice demo
        voices_dir = os.path.join(os.path.dirname(__file__), "..", "..", "VibeVoice-Community", "demo", "voices")
        alice_voice = os.path.join(voices_dir, "en-Alice_woman.wav")
        
        if os.path.exists(alice_voice):
            return [alice_voice]
        else:
            # Fallback - try to find any available voice
            if os.path.exists(voices_dir):
                voice_files = [f for f in os.listdir(voices_dir) if f.endswith('.wav')]
                if voice_files:
                    return [os.path.join(voices_dir, voice_files[0])]
            
            raise Exception(f"Voice sample not found for {voice_name}. Please ensure voice samples are available.")
    
    def _numpy_to_stereo_wav_bytes(self, audio_data: np.ndarray, sample_rate: int) -> bytes:
        """Convert numpy array to stereo WAV bytes."""
        
        # Ensure audio data is in the right format (samples, channels)
        if len(audio_data.shape) == 1:
            # Mono audio - convert to stereo
            audio_data = np.stack([audio_data, audio_data], axis=1)
        elif audio_data.shape[0] == 2 and audio_data.shape[1] > audio_data.shape[0]:
            # Channels first - transpose to samples first
            audio_data = audio_data.T
        
        # Ensure we have stereo audio
        if audio_data.shape[1] != 2:
            # If not stereo, duplicate the channel
            audio_data = np.stack([audio_data[:, 0], audio_data[:, 0]], axis=1)
        
        # Ensure audio data is in the right format
        if audio_data.dtype != np.float32:
            audio_data = audio_data.astype(np.float32)
        
        # Clamp values to prevent clipping
        audio_data = np.clip(audio_data, -1.0, 1.0)
        
        # Create temporary file for WAV
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            # Write stereo WAV file
            sf.write(temp_path, audio_data, sample_rate, subtype='PCM_16')
            
            # Read the WAV file
            with open(temp_path, 'rb') as f:
                wav_bytes = f.read()
            
            return wav_bytes
            
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


# Initialize VibeVoice TTS system
vibevoice_tts = RealVibeVoiceTTS()


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy", 
        "service": "presenter-real-vibevoice", 
        "timestamp": datetime.utcnow(),
        "vibevoice_loaded": vibevoice_tts.is_loaded,
        "device": str(vibevoice_tts.device)
    }


@app.post("/generate-audio", response_model=AudioGenerationResponse)
async def generate_audio(request: AudioGenerationRequest):
    """Generate high-quality stereo podcast audio from script using VibeVoice."""
    
    logger.info(f"Generating podcast audio for episode {request.episode_id}")
    logger.info(f"Script length: {len(request.script)} characters")
    
    if not vibevoice_tts.is_loaded:
        raise HTTPException(
            status_code=500, 
            detail="VibeVoice model not loaded. Cannot generate speech without the actual VibeVoice model."
        )
    
    try:
        # Ensure storage directory exists
        os.makedirs(AUDIO_STORAGE_PATH, exist_ok=True)
        
        # Create output filename
        audio_filename = f"episode_{request.episode_id}_vibevoice_podcast.wav"
        audio_path = os.path.join(AUDIO_STORAGE_PATH, audio_filename)
        
        # Generate speech with VibeVoice
        logger.info("Generating speech with VibeVoice...")
        audio_bytes = vibevoice_tts.generate_speech(
            request.script, 
            voice_id="Alice"  # Default speaker
        )
        
        # Save audio file
        with open(audio_path, 'wb') as f:
            f.write(audio_bytes)
        
        # Get file statistics
        file_size = os.path.getsize(audio_path)
        
        # Calculate duration from script (rough estimate)
        word_count = len(request.script.split())
        estimated_duration = max(10, int(word_count / 2.5))
        
        generation_metadata = {
            "model_used": "vibevoice-1.5b-real",
            "voice_settings": request.voice_settings or {},
            "presenter_ids": [str(pid) for pid in request.presenter_ids],
            "generation_timestamp": datetime.utcnow().isoformat(),
            "script_length": word_count,
            "sample_rate": SAMPLE_RATE,
            "audio_format": "wav",
            "channels": 2,  # Stereo
            "method": "vibevoice-real-tts",
            "device": str(vibevoice_tts.device)
        }
        
        logger.info(f"Successfully generated VibeVoice podcast audio: {audio_path}")
        logger.info(f"File size: {file_size} bytes, Duration: ~{estimated_duration}s")
        logger.info(f"Audio format: Stereo WAV")
        
        return AudioGenerationResponse(
            episode_id=request.episode_id,
            audio_url=f"file://{os.path.abspath(audio_path)}",
            duration_seconds=estimated_duration,
            file_size_bytes=file_size,
            format="wav",
            generation_metadata=generation_metadata
        )
        
    except Exception as e:
        logger.error(f"Error generating VibeVoice podcast audio: {e}")
        raise HTTPException(status_code=500, detail=f"VibeVoice podcast audio generation failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)
