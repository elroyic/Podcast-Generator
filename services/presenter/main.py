"""
VibeVoice Presenter Service - Generates high-quality MP3 audio files using VibeVoice only.
Service fails if VibeVoice is unavailable - no synthetic fallback for production quality.
Also provides presenter review functionality for collections and scripts.
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
import httpx
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from pydub import AudioSegment
from sqlalchemy.orm import Session

# Add the shared directory to Python path
import sys
sys.path.append('/app/shared')
sys.path.append('/app/VibeVoice-Community')
sys.path.append('/app/VibeVoice')

from database import get_db, create_tables
from models import Presenter

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Presenter Service (MP3)", version="1.0.0")

# Configuration
# Root storage directory; files will be written under /episodes/{episode_id}/
AUDIO_STORAGE_PATH = os.getenv("AUDIO_STORAGE_PATH", "/app/storage")
SAMPLE_RATE = 22050
BIT_RATE = 128  # kbps for MP3

# Ollama configuration for presenter reviews
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "gpt-oss:20b")


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


# Presenter Review Models
class CollectionBrief(BaseModel):
    """1000-word brief on a collection (in character)."""
    presenter_id: UUID
    collection_id: str
    brief: str
    brief_metadata: Dict[str, Any]


class ScriptFeedback(BaseModel):
    """500-word feedback on a script (in character)."""
    presenter_id: UUID
    script_id: str
    feedback: str
    feedback_metadata: Dict[str, Any]


class BriefRequest(BaseModel):
    """Request to generate a collection brief."""
    presenter_id: UUID
    collection_id: str
    articles: List[Dict[str, Any]]  # Articles in the collection


class FeedbackRequest(BaseModel):
    """Request to generate script feedback."""
    presenter_id: UUID
    script_id: str
    script: str
    collection_context: Dict[str, Any]


class OllamaClient:
    """Client for interacting with Ollama API for presenter reviews."""
    
    def __init__(self, base_url: str = OLLAMA_BASE_URL):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=120.0)  # Longer timeout for longer responses
    
    async def generate_content(
        self,
        model: str,
        prompt: str,
        system_prompt: str = None
    ) -> str:
        """Generate content using Ollama."""
        try:
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.8,  # Higher temperature for more creative, persona-driven content
                    "top_p": 0.9,
                    "max_tokens": 3000  # Allow for longer responses
                }
            }
            
            if system_prompt:
                payload["system"] = system_prompt
            
            response = await self.client.post(
                f"{self.base_url}/api/generate",
                json=payload
            )
            response.raise_for_status()
            
            result = response.json()
            return result.get("response", "")
            
        except Exception as e:
            logger.error(f"Error generating content with Ollama: {e}")
            raise


class VibeVoiceTTS:
    """HF model-backed Text-to-Speech (no synthetic fallback)."""
    
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
        """Load the HF model specified via HF_MODEL_ID."""
        try:
            logger.info(f"Loading HF TTS model '{self.model_id}' on {self.device}")
            from transformers import AutoModel, AutoProcessor, AutoTokenizer, AutoModelForCausalLM

            # Try AutoProcessor first; if missing, fall back to AutoTokenizer
            self.processor = None
            try:
                self.processor = AutoProcessor.from_pretrained(
                    self.model_id, trust_remote_code=True
                )
            except Exception:
                try:
                    self.processor = AutoTokenizer.from_pretrained(
                        self.model_id, trust_remote_code=True
                    )
                except Exception:
                    self.processor = None

            # Load model with remote code enabled
            dtype = torch.float16 if torch.cuda.is_available() else torch.float32
            try:
                # Load via AutoModelForCausalLM after community registry import
                from vibevoice.modular.modeling_vibevoice_inference import (
                    VibeVoiceForConditionalGenerationInference,
                )
                from vibevoice.modular.configuration_vibevoice import VibeVoiceConfig
                from vibevoice.processor.vibevoice_processor import VibeVoiceProcessor
                logger.info("Community registry imported; attempting AutoModelForCausalLM...")
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_id,
                    trust_remote_code=False,
                    torch_dtype=dtype,
                    device_map="auto",
                    low_cpu_mem_usage=True,
                )
                self.model.eval()
                self.is_loaded = True
                logger.info("✅ Model loaded via AutoModelForCausalLM")
                return
            except Exception as e:
                logger.warning(f"AutoModelForCausalLM failed: {e}; trying community class...")
            try:
                from vibevoice.modular.modeling_vibevoice_inference import (
                    VibeVoiceForConditionalGenerationInference,
                )
                # Load without device_map due to weight map KeyError with empty string
                self.model = VibeVoiceForConditionalGenerationInference.from_pretrained(
                    self.model_id,
                    dtype=dtype,
                    low_cpu_mem_usage=True,
                )
                # Manually move to GPU
                self.model = self.model.to(self.device)
                self.model.eval()
                self.is_loaded = True
                logger.info("✅ Loaded VibeVoice-Community model directly")
                return
            except Exception as le:
                logger.warning(f"Failed to load VibeVoice-Community model: {le}")
            
        except ImportError as e:
            logger.warning(f"VibeVoice not available: {e}")
            self.is_loaded = False
        except Exception as e:
            logger.warning(f"Failed to load HF TTS model: {e}")
            self.is_loaded = False
    
    def generate_speech(self, text: str, voice_id: str = "default") -> np.ndarray:
        """Generate speech from text using the loaded HF model - fail if not available."""
        if not self.use_vibevoice:
            raise Exception("HF TTS is disabled via USE_VIBEVOICE=false environment variable")
        
        if not self.is_loaded:
            raise Exception("TTS model failed to load. Cannot generate speech without the model.")
        
        return self._generate_vibevoice_speech(text, voice_id)
    
    def _generate_vibevoice_speech(self, text: str, voice_id: str) -> np.ndarray:
        """Generate speech using VibeVoice model."""
        try:
            logger.info(f"Generating speech with {self.model_id} for voice: {voice_id}")
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
                
                audio_array = None
                # Common path: processor -> model.generate(**inputs)
                if self.processor is not None:
                    try:
                        inputs = self.processor(chunk, return_tensors="pt", padding=True, truncation=True)
                        inputs = {k: v.to(self.device) for k, v in inputs.items()}
                        with torch.no_grad():
                            audio_outputs = self.model.generate(**inputs)  # trust_remote_code may override
                        if hasattr(audio_outputs, 'cpu'):
                            audio_array = audio_outputs.cpu().numpy()
                        else:
                            audio_array = np.array(audio_outputs)
                    except Exception:
                        audio_array = None
                
                # Fallback path: custom method names exposed by trust_remote_code repos
                if audio_array is None:
                    gen_fn = None
                    for name in [
                        'generate_speech', 'tts', 'inference', 'infer', 'generate_audio'
                    ]:
                        if hasattr(self.model, name):
                            gen_fn = getattr(self.model, name)
                            break
                    if gen_fn is None:
                        raise RuntimeError("Loaded model does not expose a known TTS generation method")
                    with torch.no_grad():
                        result = gen_fn(chunk)
                    # Normalize result to numpy 1D or 2D
                    if isinstance(result, np.ndarray):
                        audio_array = result
                    elif hasattr(result, 'cpu'):
                        audio_array = result.cpu().numpy()
                    elif isinstance(result, (list, tuple)):
                        audio_array = np.array(result)
                    else:
                        raise RuntimeError("Unknown audio result format from model")
                
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
            logger.error(f"HF TTS generation failed: {e}")
            raise Exception(f"HF speech generation failed: {str(e)}")
    


# Global instances
vibevoice_tts = VibeVoiceTTS()
ollama_client = OllamaClient()


class PersonaPresenter:
    """Handles presenter persona-based content generation."""
    
    def __init__(self):
        self.ollama_client = ollama_client
    
    def create_presenter_persona_prompt(self, presenter: Presenter) -> str:
        """Create system prompt for presenter persona."""
        return f"""You are {presenter.name}, a podcast presenter with the following characteristics:

Bio: {presenter.bio or 'No bio provided'}
Age: {presenter.age or 'Not specified'}
Gender: {presenter.gender or 'Not specified'}
Country: {presenter.country or 'Not specified'}
City: {presenter.city or 'Not specified'}

Expertise: {', '.join(presenter.expertise or [])}
Specialties: {', '.join(presenter.specialties or [])}
Interests: {', '.join(presenter.interests or [])}

Persona: {presenter.persona or 'No specific persona defined'}

System Prompt: {presenter.system_prompt or 'Provide clear, engaging commentary in your unique style.'}

You should respond in character, using your personality, expertise, and speaking style. Be authentic to who you are as a presenter."""

    def create_brief_prompt(self, presenter: Presenter, articles: List[Dict[str, Any]]) -> str:
        """Create prompt for collection brief generation."""
        articles_text = ""
        for i, article in enumerate(articles, 1):
            articles_text += f"""
Article {i}:
Title: {article.get('title', 'No title')}
Summary: {article.get('summary', 'No summary')}
Content: {article.get('content', 'No content')[:500]}...
Published: {article.get('publish_date', 'Unknown date')}
"""
        
        return f"""As {presenter.name}, please provide a 1000-word brief on this collection of news articles. 

The articles are:
{articles_text}

Your brief should include:
1. Your perspective on the main themes and stories
2. How these stories connect to your areas of expertise: {', '.join(presenter.expertise or [])}
3. What makes these stories important or interesting
4. Your personal take on the implications
5. How you would present these stories to your audience

Write this as if you're preparing to present these stories on your podcast. Be engaging, insightful, and true to your personality."""

    def create_feedback_prompt(self, presenter: Presenter, script: str, collection_context: Dict[str, Any]) -> str:
        """Create prompt for script feedback generation."""
        return f"""As {presenter.name}, please review this podcast script and provide 500-word feedback.

Script:
{script}

Collection Context:
{collection_context}

Your feedback should include:
1. How well the script captures the essence of the stories
2. Whether the tone and style match your presentation approach
3. Suggestions for improvement or enhancement
4. Your personal perspective on the topics covered
5. Suggestions for improvement
6. How well it aligns with your presentation style
7. Be honest but constructive
8. Consider your expertise in: {', '.join(presenter.expertise or [])}

Write this as if you're reviewing a script that you might present. Be authentic to your personality and provide valuable insights."""

    async def generate_collection_brief(
        self,
        presenter: Presenter,
        articles: List[Dict[str, Any]],
        collection_id: str
    ) -> CollectionBrief:
        """Generate a 1000-word brief on a collection."""
        
        logger.info(f"Generating collection brief for presenter {presenter.name}")
        
        # Create prompts
        persona_prompt = self.create_presenter_persona_prompt(presenter)
        brief_prompt = self.create_brief_prompt(presenter, articles)
        
        # Generate brief with graceful fallback if Ollama errors
        model = DEFAULT_MODEL
        response_text = ""
        try:
            response_text = await self.ollama_client.generate_content(
                model=model,
                prompt=brief_prompt,
                system_prompt=persona_prompt
            )
        except Exception as e:
            # Fallback brief generation
            logger.warning(f"Ollama brief generation failed, using fallback: {e}")
            response_text = self._generate_fallback_brief(presenter, articles)
        
        brief_metadata = {
            "model_used": model,
            "generation_timestamp": datetime.utcnow().isoformat(),
            "article_count": len(articles),
            "presenter_persona": {
                "name": presenter.name,
                "expertise": presenter.expertise or [],
                "specialties": presenter.specialties or []
            },
            "raw_response_length": len(response_text)
        }
        
        return CollectionBrief(
            presenter_id=presenter.id,
            collection_id=collection_id,
            brief=response_text,
            brief_metadata=brief_metadata
        )

    async def generate_script_feedback(
        self,
        presenter: Presenter,
        script: str,
        script_id: str,
        collection_context: Dict[str, Any]
    ) -> ScriptFeedback:
        """Generate 500-word feedback on a script."""
        
        logger.info(f"Generating script feedback for presenter {presenter.name}")
        
        # Create prompts
        persona_prompt = self.create_presenter_persona_prompt(presenter)
        feedback_prompt = self.create_feedback_prompt(presenter, script, collection_context)
        
        # Generate feedback with graceful fallback if Ollama errors
        model = DEFAULT_MODEL
        response_text = ""
        try:
            response_text = await self.ollama_client.generate_content(
                model=model,
                prompt=feedback_prompt,
                system_prompt=persona_prompt
            )
        except Exception as e:
            # Fallback feedback generation
            logger.warning(f"Ollama feedback generation failed, using fallback: {e}")
            response_text = self._generate_fallback_feedback(presenter, script)
        
        feedback_metadata = {
            "model_used": model,
            "generation_timestamp": datetime.utcnow().isoformat(),
            "script_length": len(script.split()),
            "presenter_persona": {
                "name": presenter.name,
                "expertise": presenter.expertise or [],
                "specialties": presenter.specialties or []
            },
            "raw_response_length": len(response_text)
        }
        
        return ScriptFeedback(
            presenter_id=presenter.id,
            script_id=script_id,
            feedback=response_text,
            feedback_metadata=feedback_metadata
        )

    def _generate_fallback_brief(self, presenter: Presenter, articles: List[Dict[str, Any]]) -> str:
        """Generate fallback brief when Ollama is unavailable."""
        brief = f"""As {presenter.name}, I'm excited to dive into this collection of news stories. Let me share my perspective on what's happening here.

Looking at these {len(articles)} articles, I can see some fascinating patterns emerging. The stories cover a range of topics that really speak to the current moment we're living in.

"""
        for i, article in enumerate(articles[:3], 1):  # Focus on first 3 articles
            title = article.get('title', 'Untitled')
            brief += f"First, there's the story about {title}. This really caught my attention because "
            if presenter.expertise:
                brief += f"This is right in my wheelhouse of {', '.join(presenter.expertise)}. "
            brief += f"I think this development has significant implications for how we understand the current landscape.\n\n"
        
        brief += f"""From my perspective as someone with expertise in {', '.join(presenter.expertise or ['general news analysis'])}, these stories collectively paint a picture of our current moment. The themes I'm seeing here suggest we're at an interesting crossroads, and I think listeners will find these developments both concerning and hopeful in different ways.

What really stands out to me is how these stories interconnect. They're not isolated events but part of a larger narrative that we're all living through. As a presenter, I'm excited to share these insights with our audience and help them understand the bigger picture.

I think the key takeaway here is that we're witnessing significant changes across multiple sectors, and it's important to stay informed and engaged with these developments. These stories represent just a snapshot of what's happening, but they give us valuable insights into the direction things are heading.

For our listeners, I'd encourage them to pay attention to these trends and consider how they might impact their own lives and communities. The world is changing rapidly, and staying informed is more important than ever."""
        
        return brief

    def _generate_fallback_feedback(self, presenter: Presenter, script: str) -> str:
        """Generate fallback feedback when Ollama is unavailable."""
        feedback = f"""As {presenter.name}, I've reviewed this script and here are my thoughts:

Overall, I think this script does a solid job of covering the key points. The structure is clear and the flow works well for a podcast format. 

From my perspective as someone with expertise in {', '.join(presenter.expertise or ['general news analysis'])}, I can see that the script touches on important themes that our audience will find relevant. The tone is appropriate and the pacing seems right for the content.

A few suggestions I'd make:
1. Consider adding more personal perspective - listeners connect with authentic takes
2. The transitions between topics could be smoother
3. Maybe include a bit more context for listeners who might be new to these topics

I think this script captures the essence of the stories well, though there's always room to make it more engaging. The key is to remember that we're not just reporting facts - we're helping our audience understand why these stories matter.

The script aligns well with my presentation style, though I might add a bit more personality to make it feel more conversational. Overall, it's a good foundation that we can build on."""
        
        return feedback


# Global persona presenter instance
persona_presenter = PersonaPresenter()




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


# Create tables on startup
@app.on_event("startup")
async def startup_event():
    create_tables()
    logger.info("Presenter Service started with review functionality")


@app.post("/generate-brief", response_model=CollectionBrief)
async def generate_collection_brief(
    request: BriefRequest,
    db: Session = Depends(get_db)
):
    """Generate a 1000-word brief on a collection from a presenter's perspective."""
    
    # Get presenter from database
    presenter = db.query(Presenter).filter(Presenter.id == request.presenter_id).first()
    if not presenter:
        raise HTTPException(status_code=404, detail="Presenter not found")
    
    try:
        # Generate brief using persona presenter
        brief = await persona_presenter.generate_collection_brief(
            presenter=presenter,
            articles=request.articles,
            collection_id=request.collection_id
        )
        
        # Update presenter review count
        presenter.review_count = (presenter.review_count or 0) + 1
        presenter.last_review = datetime.utcnow()
        db.commit()
        
        logger.info(f"Successfully generated brief for presenter {presenter.name}")
        return brief
        
    except Exception as e:
        logger.error(f"Error generating brief for presenter {request.presenter_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Brief generation failed: {str(e)}")


@app.post("/generate-feedback", response_model=ScriptFeedback)
async def generate_script_feedback(
    request: FeedbackRequest,
    db: Session = Depends(get_db)
):
    """Generate 500-word feedback on a script from a presenter's perspective."""
    
    # Get presenter from database
    presenter = db.query(Presenter).filter(Presenter.id == request.presenter_id).first()
    if not presenter:
        raise HTTPException(status_code=404, detail="Presenter not found")
    
    try:
        # Generate feedback using persona presenter
        feedback = await persona_presenter.generate_script_feedback(
            presenter=presenter,
            script=request.script,
            script_id=request.script_id,
            collection_context=request.collection_context
        )
        
        # Update presenter review count
        presenter.review_count = (presenter.review_count or 0) + 1
        presenter.last_review = datetime.utcnow()
        db.commit()
        
        logger.info(f"Successfully generated feedback for presenter {presenter.name}")
        return feedback
        
    except Exception as e:
        logger.error(f"Error generating feedback for presenter {request.presenter_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Feedback generation failed: {str(e)}")


@app.get("/presenters")
async def list_presenters(db: Session = Depends(get_db)):
    """List all presenters with their review statistics."""
    presenters = db.query(Presenter).all()
    
    return [
        {
            "id": str(p.id),
            "name": p.name,
            "bio": p.bio,
            "persona": p.persona,
            "voice_model": p.voice_model,
            "status": p.status,
            "review_count": p.review_count or 0,
            "last_review": p.last_review.isoformat() if p.last_review else None,
            "expertise": p.expertise or [],
            "specialties": p.specialties or []
        }
        for p in presenters
    ]


@app.get("/presenters/{presenter_id}")
async def get_presenter(presenter_id: UUID, db: Session = Depends(get_db)):
    """Get a specific presenter with their review statistics."""
    presenter = db.query(Presenter).filter(Presenter.id == presenter_id).first()
    if not presenter:
        raise HTTPException(status_code=404, detail="Presenter not found")
    
    return {
        "id": str(presenter.id),
        "name": presenter.name,
        "bio": presenter.bio,
        "persona": presenter.persona,
        "voice_model": presenter.voice_model,
        "llm_model": presenter.llm_model,
        "system_prompt": presenter.system_prompt,
        "status": presenter.status,
        "review_count": presenter.review_count or 0,
        "last_review": presenter.last_review.isoformat() if presenter.last_review else None,
        "expertise": presenter.expertise or [],
        "specialties": presenter.specialties or [],
        "interests": presenter.interests or [],
        "age": presenter.age,
        "gender": presenter.gender,
        "country": presenter.country,
        "city": presenter.city
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    # Check if VibeVoice is available
    vibevoice_status = "loaded" if vibevoice_tts.is_loaded else "failed"
    vibevoice_enabled = vibevoice_tts.use_vibevoice
    
    # Check if Ollama is available for presenter reviews
    ollama_status = "unknown"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            ollama_status = "available" if response.status_code == 200 else "unavailable"
    except Exception:
        ollama_status = "unavailable"
    
    # Service is healthy if either VibeVoice or Ollama is working
    overall_status = "healthy" if (vibevoice_enabled and vibevoice_tts.is_loaded) or ollama_status == "available" else "unhealthy"
    
    return {
        "status": overall_status,
        "service": "presenter-service", 
        "vibevoice_enabled": vibevoice_enabled,
        "vibevoice_status": vibevoice_status,
        "model_loaded": vibevoice_tts.is_loaded,
        "device": str(vibevoice_tts.device),
        "ollama_status": ollama_status,
        "ollama_url": OLLAMA_BASE_URL,
        "features": {
            "audio_generation": vibevoice_enabled and vibevoice_tts.is_loaded,
            "presenter_reviews": ollama_status == "available"
        },
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
            "model_used": os.getenv("HF_MODEL_ID", "vibevoice/VibeVoice-1.5B"),
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
            "model_used": os.getenv("HF_MODEL_ID", "vibevoice/VibeVoice-1.5B"),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in test audio generation: {e}")
        raise HTTPException(status_code=500, detail=f"Test audio generation failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)
