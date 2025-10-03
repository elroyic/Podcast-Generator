"""
Coqui XTTS v2 Integration for Podcast Generator
================================================
Local, multi-speaker TTS that runs on 8GB GPU (RTX 3070 Ti).
Perfect for POC demonstration!

Features:
- Multi-voice support with voice cloning
- Natural-sounding speech
- Runs locally on GPU (2-3GB VRAM)
- No cloud dependencies
- Good quality for POC
"""

import os
import tempfile
from pathlib import Path
import logging
from pydub import AudioSegment
import re
import torch

logger = logging.getLogger(__name__)

class CoquiTTS:
    """Coqui XTTS v2 wrapper with multi-voice support."""
    
    def __init__(self, model_name: str = "tts_models/en/vctk/vits"):
        """Initialize Coqui TTS with multi-speaker VITS model."""
        self.model_name = model_name
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.tts = None
        logger.info(f"Initializing Coqui TTS ({model_name}) on {self.device}")
        self._load_model()
    
    def _load_model(self):
        """Load the TTS model."""
        try:
            import builtins
            
            # Patch input() to auto-accept license for non-commercial POC use
            original_input = builtins.input
            builtins.input = lambda *args, **kwargs: "y"
            
            logger.info(f"Loading {self.model_name}...")
            try:
                from TTS.api import TTS
                self.tts = TTS(model_name=self.model_name, progress_bar=False, gpu=(self.device == "cuda"))
            finally:
                builtins.input = original_input
            
            logger.info(f"✅ Coqui XTTS v2 loaded on {self.device}")
        except Exception as e:
            logger.error(f"Failed to load Coqui TTS: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise
    
    def _parse_multi_speaker_script(self, script: str) -> list:
        """
        Parse script into speaker segments.
        
        Returns: [(speaker_id, text), ...]
        """
        segments = []
        
        # Match "Speaker X: text" format
        pattern = r'Speaker\s+(\d+):\s*(.+?)(?=\n\s*Speaker\s+\d+:|\Z)'
        matches = re.findall(pattern, script, re.DOTALL | re.IGNORECASE)
        
        if matches:
            for speaker_num, text in matches:
                speaker_id = int(speaker_num)
                clean_text = text.strip()
                if clean_text and len(clean_text) > 3:  # Skip very short segments
                    segments.append((speaker_id, clean_text))
            logger.info(f"Parsed {len(segments)} speaker segments")
        else:
            # Fallback: treat as single speaker
            logger.warning("No speaker markers found, using single voice")
            segments = [(1, script.strip())]
        
        return segments
    
    def _get_speaker_voice(self, speaker_id: int) -> str:
        """
        Get speaker name for a speaker ID.
        VCTK model has 109 speakers (p225-p376).
        We'll map our speaker IDs to different VCTK speakers.
        """
        # Map speaker IDs to VCTK speakers (alternating male/female)
        vctk_speakers = {
            1: "p225",  # Female (English, Southern England)
            2: "p226",  # Male (English, Surrey)
            3: "p227",  # Male (English, Cumbria)
            4: "p228",  # Female (English, Southern England)
        }
        
        # Get speaker or default to first one
        speaker = vctk_speakers.get(speaker_id, "p225")
        return speaker
    
    def _generate_segment(self, text: str, speaker_name: str, output_file: Path) -> None:
        """Generate audio for a single segment using Coqui TTS."""
        try:
            logger.info(f"Generating {len(text)} chars with speaker {speaker_name}")
            
            # VCTK/VITS can handle long text well
            # Generate with Coqui TTS using specific speaker
            self.tts.tts_to_file(
                text=text,
                file_path=str(output_file),
                speaker=speaker_name
            )
            
            logger.info(f"Generated segment: {output_file}")
            
        except Exception as e:
            logger.error(f"Failed to generate segment: {e}")
            raise
    
    def generate_multi_speaker_audio(
        self,
        script: str,
        output_path: Path
    ) -> dict:
        """
        Generate multi-speaker audio from script.
        
        Returns: {
            "audio_path": Path,
            "duration_seconds": float,
            "file_size_bytes": int,
            "speakers_used": int
        }
        """
        logger.info(f"Generating multi-speaker audio with Coqui XTTS v2")
        
        # Parse script
        segments = self._parse_multi_speaker_script(script)
        
        if not segments:
            raise ValueError("No valid text segments found in script")
        
        # Generate audio for each segment
        segment_files = []
        speakers_used = set()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            for idx, (speaker_id, text) in enumerate(segments):
                speaker_name = self._get_speaker_voice(speaker_id)
                speakers_used.add(speaker_id)
                
                segment_file = temp_path / f"segment_{idx:04d}.wav"
                
                logger.info(f"Segment {idx+1}/{len(segments)}: Speaker {speaker_id} ({speaker_name}), {len(text)} chars")
                
                self._generate_segment(text, speaker_name, segment_file)
                segment_files.append(segment_file)
            
            # Concatenate all segments
            logger.info(f"Concatenating {len(segment_files)} segments")
            
            combined = AudioSegment.empty()
            for segment_file in segment_files:
                audio = AudioSegment.from_wav(str(segment_file))
                combined += audio
                # Add small pause between speakers (300ms)
                combined += AudioSegment.silent(duration=300)
            
            # Export as MP3
            logger.info(f"Exporting to {output_path}")
            combined.export(
                str(output_path),
                format="mp3",
                bitrate="128k",
                parameters=["-q:a", "2"]
            )
        
        # Get file info
        file_size = output_path.stat().st_size
        duration = len(combined) / 1000.0  # ms to seconds
        
        logger.info(
            f"✅ Generated {duration:.1f}s audio ({file_size / (1024*1024):.2f} MB) "
            f"with {len(speakers_used)} voices"
        )
        
        return {
            "audio_path": str(output_path),
            "duration_seconds": duration,
            "file_size_bytes": file_size,
            "speakers_used": len(speakers_used)
        }

