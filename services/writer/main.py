"""
Writer Service - Generates episode metadata using Ollama.
"""
import logging
import os
import re
from datetime import datetime
from typing import Dict, Any, Optional, List
from uuid import UUID

import httpx
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from shared.database import get_db, create_tables
from shared.models import PodcastGroup, Episode, EpisodeMetadata, Presenter
from shared.schemas import EpisodeMetadataCreate, EpisodeMetadata as EpisodeMetadataSchema

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def clean_script_for_audio(script: str) -> str:
    """
    Remove all problematic tags and formatting from script for audio generation.
    This is more reliable than trying to force LLMs not to generate them.
    """
    cleaned = script
    
    # Remove <think> tags and their content
    cleaned = re.sub(r'<think>.*?</think>', '', cleaned, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove any remaining standalone think tags
    cleaned = re.sub(r'</?think>', '', cleaned, flags=re.IGNORECASE)
    
    # Remove === EDITED SCRIPT === markers
    cleaned = re.sub(r'===\s*EDITED SCRIPT\s*===', '', cleaned, flags=re.IGNORECASE)
    
    # Remove === REVIEW === and everything after it
    cleaned = re.sub(r'===\s*REVIEW\s*===.*$', '', cleaned, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove === REVIEW NOTES === and everything after it
    cleaned = re.sub(r'===\s*REVIEW NOTES\s*===.*$', '', cleaned, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove markdown bold from Speaker labels: **Speaker X:** → Speaker X:
    cleaned = re.sub(r'\*\*Speaker\s+(\d+):\*\*', r'Speaker \1:', cleaned)
    
    # Remove any remaining markdown formatting
    cleaned = re.sub(r'\*\*([^*]+)\*\*', r'\1', cleaned)  # Bold
    cleaned = re.sub(r'\*([^*]+)\*', r'\1', cleaned)      # Italic
    
    # Remove common LLM artifacts
    cleaned = re.sub(r'Final Answer.*$', '', cleaned, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r'\\boxed\{.*?\}', '', cleaned)
    cleaned = re.sub(r'\$\$.*?\$\$', '', cleaned, flags=re.DOTALL)
    
    # Keep only lines that start with "Speaker X:" (the actual dialogue)
    # Everything else is LLM meta-commentary
    lines = cleaned.split('\n')
    speaker_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('Speaker '):
            speaker_lines.append(line)
        # Allow blank lines between speakers
        elif not stripped and speaker_lines:
            speaker_lines.append(line)
    
    cleaned = '\n'.join(speaker_lines)
    
    # Clean up excessive whitespace
    cleaned = re.sub(r'\n\s*\n\s*\n+', '\n\n', cleaned)
    cleaned = cleaned.strip()
    
    return cleaned

app = FastAPI(title="Writer Service", version="1.0.0")

# Configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:latest")
MAX_TOKENS_PER_REQUEST = int(os.getenv("MAX_TOKENS_PER_REQUEST", "5000"))


class MetadataGenerationRequest(BaseModel):
    episode_id: UUID
    script: str
    group_id: UUID
    style_preferences: Optional[Dict[str, Any]] = None


class MetadataGenerationResponse(BaseModel):
    metadata: EpisodeMetadataCreate
    generation_metadata: Dict[str, Any]


class ScriptGenerationRequest(BaseModel):
    group_id: UUID
    articles: List[str]  # Article content/summaries for the episode
    style_preferences: Optional[Dict[str, Any]] = None


class ScriptGenerationResponse(BaseModel):
    script: str
    generation_metadata: Dict[str, Any]


class OllamaClient:
    """Client for interacting with Ollama API."""
    
    def __init__(self, base_url: str = OLLAMA_BASE_URL):
        self.base_url = base_url
        # Increased timeout for gpt-oss:20b which includes thinking time
        self.client = httpx.AsyncClient(timeout=180.0)
    
    async def generate_metadata(
        self,
        model: str,
        prompt: str,
        system_prompt: str = None,
        max_tokens: int = None
    ) -> str:
        """Generate metadata using Ollama."""
        try:
            if max_tokens is None:
                max_tokens = MAX_TOKENS_PER_REQUEST
            
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.8,
                    "top_p": 0.9,
                    "num_predict": max_tokens  # Ollama uses num_predict for max tokens
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
            response_text = result.get("response", "")
            
            # Clean gpt-oss:20b thinking sections
            # Remove "Thinking..." sections that appear before actual response
            import re
            cleaned_text = re.sub(r'Thinking\.\.\..*?\.\.\.done thinking\.\s*', '', response_text, flags=re.DOTALL | re.IGNORECASE)
            
            # Also remove standalone thinking markers
            cleaned_text = re.sub(r'^Thinking\.\.\.', '', cleaned_text, flags=re.MULTILINE | re.IGNORECASE)
            cleaned_text = re.sub(r'\.\.\.done thinking\.$', '', cleaned_text, flags=re.MULTILINE | re.IGNORECASE)
            
            return cleaned_text.strip()
            
        except Exception as e:
            logger.error(f"Error generating metadata with Ollama: {e}")
            raise HTTPException(status_code=500, detail=f"Metadata generation failed: {str(e)}")


class ScriptGenerator:
    """Handles episode script generation logic using gpt-oss-20b (high-quality model with 4k token limit)."""
    
    def __init__(self):
        self.ollama_client = OllamaClient()
        logger.info(f"🎯 ScriptGenerator initialized with model: {DEFAULT_MODEL}, max tokens: {MAX_TOKENS_PER_REQUEST}")
    
    def create_script_system_prompt(self, podcast_group: PodcastGroup) -> str:
        """Create system prompt for script generation."""
        return f"""
You are an expert podcast script writer creating engaging, professional podcast content.

⚠️ CRITICAL OUTPUT FORMAT RULE:
- ONLY output the podcast dialogue script - nothing else!
- ABSOLUTELY NO <think> tags, <reasoning>, or meta-commentary
- Do NOT explain your process, choices, or thinking
- Do NOT include ANY XML tags, markdown, or formatting
- ONLY provide the final script dialogue
- Start IMMEDIATELY with "Speaker 1:" and continue from there
- If you include <think> tags, the script will FAIL completely

PODCAST DETAILS:
- Name: {podcast_group.name}
- Description: {podcast_group.description or 'No description'}
- Category: {podcast_group.category or 'General'}
- Language: {podcast_group.language or 'English'}
- Target Audience: General audience interested in {podcast_group.category or 'current events'}

SCRIPT WRITING GUIDELINES:
1. Write in a conversational, engaging style suitable for audio
2. Include natural transitions between topics
3. Start with a compelling introduction
4. Present information clearly with depth and detail
5. Include interesting insights, analysis, and expert perspectives
6. End with a strong, comprehensive conclusion
7. **TARGET: 15-20 minutes of content (2000-3000 words) - DO NOT make it shorter!**
8. Use presenter-friendly language (easy to speak)
9. Include natural pauses and emphasis cues
10. Cover topics thoroughly - this is a podcast, not a news brief

STYLE REQUIREMENTS:
- Maintain professional yet conversational tone
- Use active voice and clear sentence structure
- Include rhetorical questions to engage listeners
- Provide context for complex topics
- Balance information with entertainment value
- Don't include URLs or complex technical references
- Write for clarity when spoken aloud

FORMAT - MULTI-SPEAKER DIALOGUE (REQUIRED):
Write the script as a natural conversation between 2-4 speakers (hosts/guests).
Each line MUST start with "Speaker 1:", "Speaker 2:", "Speaker 3:", or "Speaker 4:".
Maximum 4 speakers allowed.

⚠️ CRITICAL: Do NOT use markdown formatting!
- Write: Speaker 1: (plain text, NO asterisks)
- NOT: **Speaker 1:** (this breaks the audio generation!)
- NOT: *Speaker 1:* (no italics either)

Example format (plain text only):
  Speaker 1: Welcome to today's episode!
  Speaker 2: Thanks for having me! I'm excited to discuss this topic.
  Speaker 1: Let's dive right in...

Use Speaker 1 and Speaker 2 as the primary hosts who can discuss topics naturally.
Add Speaker 3 or Speaker 4 only if truly beneficial for the discussion.
Create engaging back-and-forth dialogue, not a monologue.

⚠️ REMEMBER: 
- Output ONLY the script dialogue, starting with "Speaker 1:"
- NO markdown formatting (no ** or * around Speaker labels)
- No tags, no explanations
"""

    def create_script_content_prompt(self, articles: List[str], podcast_group: PodcastGroup, presenter_names: List[str]) -> str:
        """Create the main content prompt for script generation."""
        articles_text = "\n\n".join([f"Article {i+1}: {article[:1000]}" for i, article in enumerate(articles)])
        
        # Build presenter info
        presenter_info = ""
        if presenter_names:
            for i, name in enumerate(presenter_names[:4], 1):
                presenter_info += f"- Speaker {i}: {name}\n"
        else:
            presenter_info = "- Speaker 1: Primary Host\n- Speaker 2: Co-Host"
        
        return f"""
Create a compelling IN-DEPTH podcast script based on the following news articles and information:

PODCAST: {podcast_group.name}
CATEGORY: {podcast_group.category or 'General News'}
EPISODE FOCUS: Current events and trending topics

PRESENTERS (use these names when speakers introduce themselves):
{presenter_info}

SOURCE ARTICLES (You have {len(articles)} articles to cover):
{articles_text}

SCRIPT REQUIREMENTS:
1. Create an engaging opening where speakers introduce themselves by name
2. **COVER ALL ARTICLES IN DEPTH** - don't just summarize, provide analysis
3. **TARGET LENGTH: 2000-3000 WORDS** for a 15-20 minute episode
4. Synthesize information from ALL articles into cohesive narrative
5. Provide detailed analysis, context, and expert insights
6. Include smooth transitions between different topics
7. Maintain listener engagement with dynamic dialogue
8. End with comprehensive summary and call-to-action
9. Write in a natural speaking style with depth and substance

STRUCTURE REQUIREMENT (MULTI-SPEAKER DIALOGUE):
- Opening: Welcome, speaker introductions by name, episode preview (150-250 words)
- Main Content: In-depth conversation covering ALL articles (1600-2400 words)
  * Speakers should naturally exchange detailed thoughts
  * Cover each article with meaningful discussion (not just headlines)
  * One speaker introduces a topic, other provides deep analysis
  * Include questions, answers, and follow-up discussion
  * Don't rush - give each topic the time it deserves
  * Aim for 200-400 words per major topic
- Closing: Comprehensive summary and wrap-up (200-300 words)

⚠️ DEPTH REQUIREMENTS:
- Each article should get 150-300 words of discussion
- Provide context, implications, and analysis
- Include expert perspectives and insights
- Connect topics to broader themes
- Don't just state facts - discuss what they mean

CRITICAL: Every line must start with "Speaker 1:", "Speaker 2:", "Speaker 3:", or "Speaker 4:".
- Do NOT use names like "Host:", "Guest:", or "Narrator:". Only use "Speaker N:" format.
- Do NOT use markdown: NO **Speaker 1:** or *Speaker 1:* - use plain "Speaker 1:" only!
- Do NOT add any formatting, asterisks, or special characters around Speaker labels.
- Speakers should introduce themselves with their actual names (see PRESENTERS list above)

Please write the complete IN-DEPTH multi-speaker podcast dialogue script (plain text, no markdown, 2000-3000 words):
"""

    async def generate_episode_script(
        self,
        request: ScriptGenerationRequest,
        podcast_group: PodcastGroup,
        presenter_names: List[str] = None
    ) -> ScriptGenerationResponse:
        """Generate episode script from articles."""
        
        logger.info(f"Generating script for podcast group: {podcast_group.name}")
        
        # Get presenter names if not provided
        if not presenter_names and podcast_group.presenters:
            presenter_names = [p.name for p in podcast_group.presenters[:4]]
            logger.info(f"Using presenters: {presenter_names}")
        
        # Create prompts
        system_prompt = self.create_script_system_prompt(podcast_group)
        content_prompt = self.create_script_content_prompt(request.articles, podcast_group, presenter_names or [])
        
        # Generate script with graceful fallback
        model = DEFAULT_MODEL
        script_text = ""
        fallback_used = False
        try:
            script_text = await self.ollama_client.generate_metadata(  # Reusing the client method
                model=model,
                prompt=content_prompt,
                system_prompt=system_prompt
            )
            
            # Clean the script for audio generation (removes all problematic tags)
            script_text = clean_script_for_audio(script_text)
            logger.info(f"Cleaned script: {len(script_text)} chars, {len(script_text.split())} words")
        except Exception as e:
            logger.warning(f"Ollama script generation failed, using fallback: {e}")
            fallback_used = True
            # Simple fallback script generation
            script_text = self._generate_fallback_script(request.articles, podcast_group)
        
        generation_metadata = {
            "model_used": model,
            "generation_timestamp": datetime.utcnow().isoformat(),
            "article_count": len(request.articles),
            "style_preferences": request.style_preferences or {},
            "fallback_used": fallback_used,
            "script_length_words": len(script_text.split()) if script_text else 0
        }
        
        return ScriptGenerationResponse(
            script=script_text,
            generation_metadata=generation_metadata
        )
    
    def _generate_fallback_script(self, articles: List[str], podcast_group: PodcastGroup) -> str:
        """Generate a basic fallback script in multi-speaker format when Ollama fails."""
        script_lines = []
        
        # Opening with 2 speakers
        script_lines.append(f"Speaker 1: Welcome to {podcast_group.name}, your source for {podcast_group.category or 'current events'}.")
        script_lines.append(f"Speaker 2: Thanks for tuning in! We have some great topics to cover today.")
        
        # Content with alternating speakers
        for i, article in enumerate(articles[:3]):  # Limit to first 3 articles
            article_preview = article[:200] + "..." if len(article) > 200 else article
            speaker_num = (i % 2) + 1  # Alternate between Speaker 1 and Speaker 2
            script_lines.append(f"Speaker {speaker_num}: Let's discuss this next topic. {article_preview}")
        
        # Closing with both speakers
        script_lines.append(f"Speaker 1: Thank you for listening to {podcast_group.name}. Stay informed and stay engaged.")
        script_lines.append(f"Speaker 2: We'll see you next time!")
        
        return "\n".join(script_lines)


class MetadataGenerator:
    """Handles episode metadata generation logic."""
    
    def __init__(self):
        self.ollama_client = OllamaClient()
    
    def create_system_prompt(self, podcast_group: PodcastGroup) -> str:
        """Create system prompt for metadata generation."""
        system_prompt = f"""
You are an expert podcast metadata generator. Create compelling, SEO-friendly metadata for podcast episodes.

PODCAST DETAILS:
- Name: {podcast_group.name}
- Description: {podcast_group.description or 'No description'}
- Category: {podcast_group.category or 'General'}
- Language: {podcast_group.language or 'English'}
- Country: {podcast_group.country or 'International'}

METADATA REQUIREMENTS:
1. Title: Create an engaging, descriptive title (50-60 characters max)
2. Description: Write a compelling episode description (150-300 words)
3. Tags: Generate 5-10 relevant tags for discoverability
4. Keywords: Extract 3-5 key terms for SEO
5. Category: Use the podcast's main category
6. Subcategory: Suggest a relevant subcategory
7. Language: Use the podcast's language setting
8. Country: Use the podcast's country setting

STYLE GUIDELINES:
- Make titles catchy and descriptive
- Write descriptions that hook listeners
- Use relevant, trending keywords
- Include episode highlights in description
- Make it accessible to general audiences
- Follow podcast platform best practices
- Don't include URL's in the script.

FORMAT OUTPUT AS JSON:
{{
    "title": "Episode title here",
    "description": "Episode description here",
    "tags": ["tag1", "tag2", "tag3"],
    "keywords": ["keyword1", "keyword2", "keyword3"],
    "category": "Main category",
    "subcategory": "Subcategory",
    "language": "Language code",
    "country": "Country code"
}}
"""
        return system_prompt
    
    def create_content_prompt(self, script: str, podcast_group: PodcastGroup) -> str:
        """Create the main content prompt for metadata generation."""
        
        # Extract key topics from script (first 1000 characters for analysis)
        script_preview = script[:1000] + "..." if len(script) > 1000 else script
        
        prompt = f"""
Based on the following podcast script, generate compelling episode metadata.

PODCAST GROUP: {podcast_group.name}
CATEGORY: {podcast_group.category or 'General News'}
EXISTING KEYWORDS: {', '.join(podcast_group.keywords or [])}
EXISTING TAGS: {', '.join(podcast_group.tags or [])}

SCRIPT PREVIEW:
{script_preview}

SCRIPT LENGTH: {len(script.split())} words (approximately {len(script.split()) / 150:.1f} minutes)

REQUIREMENTS:
1. Create an engaging title that summarizes the episode content
2. Write a compelling description that highlights key topics and hooks listeners
3. Generate relevant tags for podcast platform discoverability
4. Extract important keywords for SEO
5. Use appropriate category and subcategory
6. Include episode length and content highlights in description
7. Make it appealing to the target audience

Consider the podcast's existing keywords and tags, but focus on the specific content of this episode.

Please generate the metadata as a JSON object:
"""
        return prompt
    
    def parse_metadata_response(self, response: str) -> EpisodeMetadataCreate:
        """Parse the Ollama response into structured metadata."""
        try:
            # Try to extract JSON from response
            import json
            import re
            
            # Look for JSON in the response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                metadata_dict = json.loads(json_str)
            else:
                # Fallback: parse manually from text
                metadata_dict = self._parse_text_response(response)
            
            return EpisodeMetadataCreate(
                title=metadata_dict.get("title", "Untitled Episode"),
                description=metadata_dict.get("description", "No description available"),
                tags=metadata_dict.get("tags", []),
                keywords=metadata_dict.get("keywords", []),
                category=metadata_dict.get("category"),
                subcategory=metadata_dict.get("subcategory"),
                language=metadata_dict.get("language"),
                country=metadata_dict.get("country")
            )
            
        except Exception as e:
            logger.error(f"Error parsing metadata response: {e}")
            # Return default metadata
            return EpisodeMetadataCreate(
                title="Generated Episode",
                description="Episode description generated from script content.",
                tags=["podcast", "episode"],
                keywords=["podcast"],
                category="General",
                language="en",
                country="US"
            )
    
    def _parse_text_response(self, response: str) -> Dict[str, Any]:
        """Parse metadata from text response when JSON parsing fails."""
        lines = response.split('\n')
        metadata = {}
        
        for line in lines:
            line = line.strip()
            if line.startswith("Title:"):
                metadata["title"] = line.replace("Title:", "").strip()
            elif line.startswith("Description:"):
                metadata["description"] = line.replace("Description:", "").strip()
            elif line.startswith("Tags:"):
                tags_str = line.replace("Tags:", "").strip()
                metadata["tags"] = [tag.strip() for tag in tags_str.split(",")]
            elif line.startswith("Keywords:"):
                keywords_str = line.replace("Keywords:", "").strip()
                metadata["keywords"] = [kw.strip() for kw in keywords_str.split(",")]
            elif line.startswith("Category:"):
                metadata["category"] = line.replace("Category:", "").strip()
            elif line.startswith("Subcategory:"):
                metadata["subcategory"] = line.replace("Subcategory:", "").strip()
        
        return metadata
    
    async def generate_episode_metadata(
        self,
        request: MetadataGenerationRequest,
        podcast_group: PodcastGroup
    ) -> MetadataGenerationResponse:
        """Generate episode metadata from script."""
        
        logger.info(f"Generating metadata for episode: {request.episode_id}")
        
        # Create prompts
        system_prompt = self.create_system_prompt(podcast_group)
        content_prompt = self.create_content_prompt(request.script, podcast_group)
        
        # Generate metadata with graceful fallback if Ollama errors
        model = DEFAULT_MODEL
        response_text = ""
        fallback_used = False
        try:
            response_text = await self.ollama_client.generate_metadata(
                model=model,
                prompt=content_prompt,
                system_prompt=system_prompt
            )
            # Parse response into structured metadata
            metadata = self.parse_metadata_response(response_text)
        except Exception as e:
            # Fallback metadata generation to avoid 500s
            logger.warning(f"Ollama metadata generation failed, using fallback: {e}")
            fallback_used = True
            # Simple fallback heuristics
            title_words = request.script.strip().split()
            fallback_title = (
                f"{podcast_group.name}: " + " ".join(title_words[:10])
            ) if title_words else f"{podcast_group.name}: Episode"
            fallback_description = request.script.strip()[:600] or "Episode description generated from script."
            metadata = EpisodeMetadataCreate(
                title=fallback_title,
                description=fallback_description,
                tags=podcast_group.tags or ["podcast", "ai"],
                keywords=podcast_group.keywords or ["podcast", "ai"],
                category=podcast_group.category or "General",
                subcategory=getattr(podcast_group, "subcategory", None),
                language=podcast_group.language or "en",
                country=podcast_group.country or "US",
            )
            response_text = ""
        
        generation_metadata = {
            "model_used": model,
            "generation_timestamp": datetime.utcnow().isoformat(),
            "script_length_words": len(request.script.split()),
            "style_preferences": request.style_preferences or {},
            "raw_response": response_text[:500] + "..." if response_text and len(response_text) > 500 else response_text,
            "fallback_used": fallback_used,
        }
        
        return MetadataGenerationResponse(
            metadata=metadata,
            generation_metadata=generation_metadata
        )


# Initialize services
script_generator = ScriptGenerator()
metadata_generator = MetadataGenerator()

# Create tables on startup
@app.on_event("startup")
async def startup_event():
    create_tables()
    logger.info("Writer Service started")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "writer", "timestamp": datetime.utcnow()}


@app.get("/metrics/prometheus")
async def get_prometheus_metrics(db: Session = Depends(get_db)):
    """Prometheus-compatible metrics endpoint."""
    from fastapi.responses import PlainTextResponse
    
    try:
        # Get worker count from environment or default to 1
        workers_active = int(os.getenv("WORKERS_ACTIVE", "1"))
        
        # Count scripts generated
        total_episodes = db.query(Episode).count()
        
        # Calculate scripts per hour (last 1 hour)
        from datetime import timedelta
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        scripts_last_hour = db.query(Episode).filter(Episode.created_at >= one_hour_ago).count()
        
        # Generate Prometheus format
        metrics = []
        metrics.append(f"writer_workers_active {workers_active}")
        metrics.append(f"writer_episodes_total {total_episodes}")
        metrics.append(f"writer_scripts_per_hour {scripts_last_hour}")
        metrics.append("writer_service_up 1")
        
        prometheus_output = "\n".join([
            "# HELP writer_workers_active Number of active workers",
            "# TYPE writer_workers_active gauge",
            "# HELP writer_episodes_total Total episodes written",
            "# TYPE writer_episodes_total gauge",
            "# HELP writer_scripts_per_hour Scripts generated in the last hour",
            "# TYPE writer_scripts_per_hour gauge",
            "# HELP writer_service_up Service health status",
            "# TYPE writer_service_up gauge",
            "",
            *metrics
        ])
        
        return PlainTextResponse(prometheus_output, media_type="text/plain")
    except Exception as e:
        logger.error(f"Error generating Prometheus metrics: {e}")
        return PlainTextResponse("# Error generating metrics\n", media_type="text/plain")


@app.post("/generate-script", response_model=ScriptGenerationResponse)
async def generate_script(
    request: ScriptGenerationRequest,
    db: Session = Depends(get_db)
):
    """Generate episode script from articles."""
    
    # Get podcast group details
    podcast_group = db.query(PodcastGroup).filter(
        PodcastGroup.id == request.group_id
    ).first()
    
    if not podcast_group:
        raise HTTPException(status_code=404, detail="Podcast group not found")
    
    try:
        result = await script_generator.generate_episode_script(request, podcast_group)
        logger.info(f"Successfully generated script for podcast group {request.group_id}")
        return result
        
    except Exception as e:
        logger.error(f"Error generating script for group {request.group_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Script generation failed: {str(e)}")


@app.post("/generate-metadata", response_model=MetadataGenerationResponse)
async def generate_metadata(
    request: MetadataGenerationRequest,
    db: Session = Depends(get_db)
):
    """Generate episode metadata from script."""
    
    # Get podcast group details
    podcast_group = db.query(PodcastGroup).filter(
        PodcastGroup.id == request.group_id
    ).first()
    
    if not podcast_group:
        raise HTTPException(status_code=404, detail="Podcast group not found")
    
    # Get episode details (optional for testing)
    episode = db.query(Episode).filter(Episode.id == request.episode_id).first()
    if not episode:
        logger.warning(f"Episode {request.episode_id} not found, proceeding without episode validation")
    
    try:
        result = await metadata_generator.generate_episode_metadata(request, podcast_group)
        logger.info(f"Successfully generated metadata for episode {request.episode_id}")
        return result
        
    except Exception as e:
        logger.error(f"Error generating metadata for episode {request.episode_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Metadata generation failed: {str(e)}")


@app.post("/episodes/{episode_id}/metadata", response_model=EpisodeMetadataSchema)
async def create_episode_metadata(
    episode_id: UUID,
    metadata_data: EpisodeMetadataCreate,
    db: Session = Depends(get_db)
):
    """Create or update episode metadata."""
    
    # Check if episode exists
    episode = db.query(Episode).filter(Episode.id == episode_id).first()
    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")
    
    # Check if metadata already exists
    existing_metadata = db.query(EpisodeMetadata).filter(
        EpisodeMetadata.episode_id == episode_id
    ).first()
    
    if existing_metadata:
        # Update existing metadata
        for field, value in metadata_data.dict(exclude_unset=True).items():
            setattr(existing_metadata, field, value)
        db.commit()
        db.refresh(existing_metadata)
        return existing_metadata
    else:
        # Create new metadata
        metadata = EpisodeMetadata(
            episode_id=episode_id,
            **metadata_data.dict()
        )
        db.add(metadata)
        db.commit()
        db.refresh(metadata)
        return metadata


@app.get("/episodes/{episode_id}/metadata", response_model=EpisodeMetadataSchema)
async def get_episode_metadata(
    episode_id: UUID,
    db: Session = Depends(get_db)
):
    """Get episode metadata."""
    metadata = db.query(EpisodeMetadata).filter(
        EpisodeMetadata.episode_id == episode_id
    ).first()
    
    if not metadata:
        raise HTTPException(status_code=404, detail="Episode metadata not found")
    
    return metadata


@app.post("/test-metadata-generation")
async def test_metadata_generation(
    test_script: str = "Welcome to today's tech podcast! We'll be discussing the latest developments in artificial intelligence, including new language models and their impact on various industries. Join us as we explore these fascinating topics with expert insights and analysis.",
    db: Session = Depends(get_db)
):
    """Test endpoint for metadata generation."""
    try:
        # Create a test request
        request = MetadataGenerationRequest(
            episode_id=UUID("00000000-0000-0000-0000-000000000001"),
            script=test_script,
            group_id=UUID("00000000-0000-0000-0000-000000000001")
        )
        
        # Create a test podcast group
        test_group = PodcastGroup(
            id=request.group_id,
            name="Test Podcast",
            description="A test podcast for metadata generation",
            category="Technology",
            language="en",
            country="US"
        )
        
        result = await metadata_generator.generate_episode_metadata(request, test_group)
        
        return {
            "generated_metadata": result.metadata.dict(),
            "generation_metadata": result.generation_metadata,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in test metadata generation: {e}")
        raise HTTPException(status_code=500, detail=f"Test metadata generation failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)