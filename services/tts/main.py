"""
TTS Service - Dedicated VibeVoice audio generation service.
ONLY handles text-to-speech conversion using VibeVoice on GPU.
"""

import logging
import os
import tempfile
from datetime import datetime
from typing import Dict, Any, Optional, List
from uuid import UUID
import re

import numpy as np
import torch
import soundfile as sf
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pydub import AudioSegment

# Add VibeVoice to path
import sys
sys.path.append('/app/VibeVoice-Community')
sys.path.append('/app/VibeVoice')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="TTS Service (VibeVoice)", version="1.0.0")

# Configuration
AUDIO_STORAGE_PATH = os.getenv("AUDIO_STORAGE_PATH", "/app/storage")
SAMPLE_RATE = 22050
BIT_RATE = 128  # kbps for MP3


class AudioGenerationRequest(BaseModel):
    episode_id: UUID
    script: str
    duration_seconds: Optional[int] = None
    voice_settings: Optional[Dict[str, Any]] = None


class AudioGenerationResponse(BaseModel):
    episode_id: UUID
    audio_url: str
    duration_seconds: int
    file_size_bytes: int
    format: str
    generation_metadata: Dict[str, Any]


class VibeVoiceTTS:
    """VibeVoice Text-to-Speech - GPU-based high-quality audio generation."""
    
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = None
        self.processor = None
        self.is_loaded = False
        self.use_vibevoice = os.getenv("USE_VIBEVOICE", "true").lower() == "true"
        self.model_id = os.getenv("HF_MODEL_ID", "vibevoice/VibeVoice-1.5B")
        
        if self.use_vibevoice:
            self._load_model()
    
    def _load_model(self):
        """Load the VibeVoice model using the correct processor and model classes."""
        try:
            logger.info(f"Loading VibeVoice model '{self.model_id}' on {self.device}")
            from vibevoice.modular.modeling_vibevoice_inference import (
                VibeVoiceForConditionalGenerationInference,
            )
            from vibevoice.processor.vibevoice_processor import VibeVoiceProcessor

            # Load processor
            logger.info("Loading VibeVoiceProcessor...")
            self.processor = VibeVoiceProcessor.from_pretrained(self.model_id)

            # Load to CPU first to avoid device placement issues, then move to target device
            attn_impl = "sdpa"  # Use SDPA (CPU and GPU compatible)
            
            logger.info(f"Loading model on CPU first, then moving to {self.device}, attn_implementation={attn_impl}")
            
            # Load model to CPU first
            self.model = VibeVoiceForConditionalGenerationInference.from_pretrained(
                self.model_id,
                attn_implementation=attn_impl,
            )
            
            # Move to target device
            logger.info(f"Moving model to {self.device}...")
            self.model = self.model.to(self.device)
            
            self.model.eval()
            self.model.set_ddpm_inference_steps(num_steps=10)
            self.is_loaded = True
            logger.info("✅ VibeVoice model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load VibeVoice model: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.is_loaded = False
    
    def generate_speech(self, text: str, voice_id: str = "default") -> np.ndarray:
        """Generate speech from text using the loaded VibeVoice model."""
        if not self.use_vibevoice:
            raise Exception("VibeVoice TTS is disabled")
        
        if not self.is_loaded:
            raise Exception("VibeVoice model failed to load")
        
        return self._generate_vibevoice_speech(text, voice_id)
    
    def _clean_script(self, text: str) -> str:
        """Clean script by removing think tags and markdown before TTS processing."""
        cleaned_text = text
        
        # Remove <think> tags and their content
        cleaned_text = re.sub(r'<think>.*?</think>', '', cleaned_text, flags=re.DOTALL)
        
        # Remove markdown bold from Speaker labels: **Speaker X:** → Speaker X:
        cleaned_text = re.sub(r'\*\*Speaker\s+(\d+):\*\*', r'Speaker \1:', cleaned_text)
        
        # Remove any remaining markdown formatting
        cleaned_text = re.sub(r'\*\*([^*]+)\*\*', r'\1', cleaned_text)  # Bold
        cleaned_text = re.sub(r'\*([^*]+)\*', r'\1', cleaned_text)      # Italic
        
        # Remove "=== EDITED SCRIPT ===" and "=== REVIEW NOTES ===" markers
        cleaned_text = re.sub(r'===\s*EDITED SCRIPT\s*===', '', cleaned_text, flags=re.IGNORECASE)
        cleaned_text = re.sub(r'===\s*REVIEW NOTES\s*===.*$', '', cleaned_text, flags=re.DOTALL | re.IGNORECASE)
        
        # Clean up excessive whitespace
        cleaned_text = re.sub(r'\n\s*\n\s*\n+', '\n\n', cleaned_text)
        cleaned_text = cleaned_text.strip()
        
        return cleaned_text
    
    def _generate_vibevoice_speech(self, text: str, voice_id: str) -> np.ndarray:
        """Generate speech using VibeVoice model with proper API."""
        try:
            logger.info(f"Generating speech with {self.model_id} for voice: {voice_id}")
            logger.info(f"Text length: {len(text)} characters")
            
            # Clean the script first
            cleaned_text = self._clean_script(text)
            logger.info(f"Cleaned text length: {len(cleaned_text)} characters")
            
            # VibeVoice expects scripts formatted as "Speaker X: text"
            if not cleaned_text.strip().startswith("Speaker "):
                # Format as single speaker script
                formatted_text = f"Speaker 1: {cleaned_text}"
                logger.info("Formatted plain text as Speaker 1 script")
            else:
                formatted_text = cleaned_text
            
            # VibeVoice requires voice samples - assign different voices to speakers
            voice_mapping = {
                1: "/app/VibeVoice-Community/demo/voices/en-Carter_man.wav",
                2: "/app/VibeVoice-Community/demo/voices/en-Maya_woman.wav",
                3: "/app/VibeVoice-Community/demo/voices/en-Frank_man.wav",
                4: "/app/VibeVoice-Community/demo/voices/en-Alice_woman.wav"
            }
            
            # Detect which speakers are in the script
            speaker_matches = re.findall(r'Speaker\s+(\d+)\s*:', formatted_text)
            unique_speakers = sorted(set(int(s) for s in speaker_matches))
            
            # Build voice samples list in order
            voice_samples = [voice_mapping.get(speaker, voice_mapping[1]) for speaker in unique_speakers]
            logger.info(f"Using {len(voice_samples)} voices for speakers: {unique_speakers}")
            
            # Prepare inputs using VibeVoiceProcessor
            inputs = self.processor(
                text=[formatted_text],
                voice_samples=[voice_samples],
                padding=True,
                return_tensors="pt",
                return_attention_mask=True,
            )
            
            # Move tensors to target device AND match model dtype
            model_dtype = next(self.model.parameters()).dtype
            logger.info(f"Converting inputs to model dtype: {model_dtype}")
            for k, v in inputs.items():
                if torch.is_tensor(v):
                    # Convert to model's dtype if it's a floating point tensor
                    if v.dtype.is_floating_point:
                        inputs[k] = v.to(device=self.device, dtype=model_dtype)
                    else:
                        inputs[k] = v.to(device=self.device)
            
            # Generate audio using the model
            # Calculate reasonable max_new_tokens based on text length
            # Speech generation needs ~2-4 tokens per word for audio
            word_count = len(text.split())
            max_new_tokens = min(word_count * 4, 512)  # Cap at 512 for safety
            
            logger.info(f"Running model.generate() with max_new_tokens={max_new_tokens} for {word_count} words...")
            logger.info(f"Input shapes: {[(k, v.shape if hasattr(v, 'shape') else type(v)) for k, v in inputs.items()]}")
            
            # Set a timeout using signal (Unix) or threading
            import threading
            generation_complete = threading.Event()
            outputs = None
            error = None
            
            def run_generation():
                nonlocal outputs, error
                try:
                    logger.info("Entering model.generate()...")
                    with torch.no_grad():
                        # Simplified call - remove cfg_scale and generation_config that might cause issues
                        outputs = self.model.generate(
                            input_ids=inputs['input_ids'],
                            attention_mask=inputs['attention_mask'],
                            speech_input_mask=inputs.get('speech_input_mask'),
                            speech_tensors=inputs.get('speech_tensors'),
                            speech_masks=inputs.get('speech_masks'),
                            max_new_tokens=max_new_tokens,
                            tokenizer=self.processor.tokenizer,
                            do_sample=False,
                            num_beams=1,
                        )
                    logger.info("Generation completed!")
                    generation_complete.set()
                except Exception as e:
                    logger.error(f"Exception in generation thread: {e}")
                    error = e
                    generation_complete.set()
            
            gen_thread = threading.Thread(target=run_generation, daemon=True)
            logger.info("Starting generation thread...")
            gen_thread.start()
            
            # Wait up to 180 seconds
            if not generation_complete.wait(timeout=180):
                raise TimeoutError(f"Generation did not complete within 180 seconds (got to some point but hung)")
            
            if error:
                raise error
            
            if outputs is None:
                raise RuntimeError("Generation completed but no outputs received")
            
            # Extract audio from outputs
            if not outputs.speech_outputs or outputs.speech_outputs[0] is None:
                raise RuntimeError("No audio output generated by model")
            
            # Get the audio tensor (first batch item)
            audio_tensor = outputs.speech_outputs[0]
            
            # Convert to numpy
            if hasattr(audio_tensor, 'cpu'):
                audio_array = audio_tensor.cpu().numpy()
            else:
                audio_array = np.array(audio_tensor)
            
            # Ensure it's 1D (flatten if needed)
            if audio_array.ndim > 1:
                audio_array = audio_array.flatten()
            
            # Convert to stereo by duplicating mono channel
            audio_stereo = np.stack([audio_array, audio_array], axis=-1)
            
            logger.info(f"✅ Generated VibeVoice audio: {audio_stereo.shape}")
            return audio_stereo
            
        except Exception as e:
            logger.error(f"VibeVoice TTS generation failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise Exception(f"VibeVoice speech generation failed: {str(e)}")


# Global TTS instance
vibevoice_tts = VibeVoiceTTS()


@app.on_event("startup")
async def startup_event():
    """Initialize service on startup."""
    logger.info("🎤 TTS Service starting up...")
    if vibevoice_tts.is_loaded:
        logger.info("✅ VibeVoice model loaded and ready")
    else:
        logger.error("❌ VibeVoice model failed to load - service will return errors")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy" if vibevoice_tts.is_loaded else "unhealthy",
        "model_loaded": vibevoice_tts.is_loaded,
        "model_id": vibevoice_tts.model_id,
        "device": str(vibevoice_tts.device)
    }


@app.post("/generate-audio", response_model=AudioGenerationResponse)
async def generate_audio(request: AudioGenerationRequest):
    """Generate MP3 audio from script using VibeVoice."""
    try:
        logger.info(f"Generating MP3 audio for episode {request.episode_id}")
        
        # Calculate expected duration
        word_count = len(request.script.split())
        duration_seconds = request.duration_seconds or int(word_count / 150 * 60)
        logger.info(f"Generating {duration_seconds}-second audio for episode {request.episode_id}")
        
        # Generate audio with VibeVoice
        logger.info("🎤 Generating audio with VibeVoice TTS")
        audio_data = vibevoice_tts.generate_speech(request.script)
        
        # Create episode-specific directory
        episode_dir = os.path.join(AUDIO_STORAGE_PATH, "episodes", str(request.episode_id))
        os.makedirs(episode_dir, exist_ok=True)
        
        # Save as WAV first (VibeVoice output)
        wav_path = os.path.join(episode_dir, "audio.wav")
        sf.write(wav_path, audio_data, SAMPLE_RATE)
        logger.info(f"Saved WAV: {wav_path}")
        
        # Convert to MP3
        mp3_path = os.path.join(episode_dir, "audio.mp3")
        audio = AudioSegment.from_wav(wav_path)
        audio.export(mp3_path, format="mp3", bitrate=f"{BIT_RATE}k")
        logger.info(f"✅ Created VibeVoice MP3 file: {mp3_path}")
        
        # Get file info
        file_size = os.path.getsize(mp3_path)
        actual_duration = int(len(audio_data) / SAMPLE_RATE)
        
        # Clean up WAV
        os.remove(wav_path)
        
        return AudioGenerationResponse(
            episode_id=request.episode_id,
            audio_url=f"/storage/episodes/{request.episode_id}/audio.mp3",
            duration_seconds=actual_duration,
            file_size_bytes=file_size,
            format="mp3",
            generation_metadata={
                "tts_backend": "vibevoice",
                "model_id": vibevoice_tts.model_id,
                "device": str(vibevoice_tts.device),
                "sample_rate": SAMPLE_RATE,
                "bit_rate": BIT_RATE,
                "generated_at": datetime.utcnow().isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"Error generating audio: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Audio generation failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8015)

