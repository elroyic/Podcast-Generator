"""
Coqui XTTS v2 Integration for Podcast Generator
================================================
Local, multi-speaker TTS that runs on 8GB GPU.
Perfect for POC demonstration!

Features:
- Multi-voice support
- Natural-sounding speech
- Runs on RTX 3070 Ti (2-3GB VRAM)
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
import torchaudio
from TTS.api import TTS

logger = logging.getLogger(__name__)

class CoquiTTS:
    """Piper TTS wrapper with multi-voice support."""
    
    # Voice mapping for different speakers
    VOICES = {
        1: "en_US-amy-medium",        # Female voice for Speaker 1
        2: "en_US-ryan-medium",       # Male voice for Speaker 2
        3: "en_US-lessac-medium",     # Alternative voice for Speaker 3
        4: "en_US-libritts-high",     # High quality voice for Speaker 4
    }
    
    def __init__(self, model_dir: str = "/app/.local/share/piper"):
        """Initialize Piper TTS."""
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Initialized Piper TTS with model dir: {self.model_dir}")
    
    def _download_voice(self, voice_name: str) -> Path:
        """Download Piper voice model if not exists."""
        model_file = self.model_dir / f"{voice_name}.onnx"
        config_file = self.model_dir / f"{voice_name}.onnx.json"
        
        if model_file.exists() and config_file.exists():
            logger.info(f"Voice {voice_name} already downloaded")
            return model_file
        
        # Download from Piper voices (HuggingFace repository)
        # Format: en_US-amy-medium -> en/en_US/amy/medium/
        parts = voice_name.split('-')
        lang_code = parts[0]  # en_US
        lang_short = lang_code.split('_')[0]  # en
        speaker = parts[1]  # amy
        quality = parts[2]  # medium
        
        base_url = f"https://huggingface.co/rhasspy/piper-voices/resolve/main/{lang_short}/{lang_code}/{speaker}/{quality}"
        
        logger.info(f"Downloading voice: {voice_name}")
        logger.info(f"URL: {base_url}/{voice_name}.onnx")
        
        # Download model
        subprocess.run([
            "wget", "-q", "-O", str(model_file),
            f"{base_url}/{voice_name}.onnx"
        ], check=True)
        
        # Download config
        subprocess.run([
            "wget", "-q", "-O", str(config_file),
            f"{base_url}/{voice_name}.onnx.json"
        ], check=True)
        
        logger.info(f"Downloaded {voice_name}")
        return model_file
    
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
                if clean_text:
                    segments.append((speaker_id, clean_text))
            logger.info(f"Parsed {len(segments)} speaker segments")
        else:
            # Fallback: treat as single speaker
            logger.warning("No speaker markers found, using single voice")
            segments = [(1, script.strip())]
        
        return segments
    
    def _generate_segment(self, text: str, voice_name: str, output_file: Path) -> None:
        """Generate audio for a single segment using Piper."""
        model_file = self._download_voice(voice_name)
        
        # Write text to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(text)
            text_file = f.name
        
        try:
            # Run Piper
            cmd = [
                "piper",
                "--model", str(model_file),
                "--output_file", str(output_file),
                "--quiet"
            ]
            
            with open(text_file, 'r') as input_f:
                result = subprocess.run(
                    cmd,
                    stdin=input_f,
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minutes max per segment
                )
            
            if result.returncode != 0:
                raise RuntimeError(f"Piper failed: {result.stderr}")
                
        finally:
            os.unlink(text_file)
    
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
        logger.info(f"Generating multi-speaker audio with Piper")
        
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
                voice_name = self.VOICES.get(speaker_id, self.VOICES[1])
                speakers_used.add(speaker_id)
                
                segment_file = temp_path / f"segment_{idx:04d}.wav"
                
                logger.info(f"Generating segment {idx+1}/{len(segments)} (Speaker {speaker_id}, {len(text)} chars)")
                
                self._generate_segment(text, voice_name, segment_file)
                segment_files.append(segment_file)
            
            # Concatenate all segments
            logger.info(f"Concatenating {len(segment_files)} segments")
            
            combined = AudioSegment.empty()
            for segment_file in segment_files:
                audio = AudioSegment.from_wav(str(segment_file))
                combined += audio
                # Add small pause between speakers (200ms)
                combined += AudioSegment.silent(duration=200)
            
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
        
        logger.info(f"✅ Generated {duration:.1f}s audio ({file_size / (1024*1024):.2f} MB) with {len(speakers_used)} voices")
        
        return {
            "audio_path": str(output_path),
            "duration_seconds": duration,
            "file_size_bytes": file_size,
            "speakers_used": len(speakers_used)
        }

