"""
Writer Service - Generates episode metadata using Ollama.
"""
import logging
import os
from datetime import datetime
from typing import Dict, Any, Optional
from uuid import UUID

import httpx
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from shared.database import get_db, create_tables
from shared.models import PodcastGroup, Episode, EpisodeMetadata
from shared.schemas import EpisodeMetadataCreate, EpisodeMetadata as EpisodeMetadataSchema

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Writer Service", version="1.0.0")

# Configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "gpt-oss:120b-cloud")


class MetadataGenerationRequest(BaseModel):
    episode_id: UUID
    script: str
    group_id: UUID
    style_preferences: Optional[Dict[str, Any]] = None


class MetadataGenerationResponse(BaseModel):
    metadata: EpisodeMetadataCreate
    generation_metadata: Dict[str, Any]


class OllamaClient:
    """Client for interacting with Ollama API."""
    
    def __init__(self, base_url: str = OLLAMA_BASE_URL):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=60.0)
    
    async def generate_metadata(
        self,
        model: str,
        prompt: str,
        system_prompt: str = None
    ) -> str:
        """Generate metadata using Ollama."""
        try:
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.8,
                    "top_p": 0.9,
                    "max_tokens": 2000
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
            logger.error(f"Error generating metadata with Ollama: {e}")
            raise HTTPException(status_code=500, detail=f"Metadata generation failed: {str(e)}")


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
        
        # Generate metadata
        model = DEFAULT_MODEL
        response = await self.ollama_client.generate_metadata(
            model=model,
            prompt=content_prompt,
            system_prompt=system_prompt
        )
        
        # Parse response into structured metadata
        metadata = self.parse_metadata_response(response)
        
        generation_metadata = {
            "model_used": model,
            "generation_timestamp": datetime.utcnow().isoformat(),
            "script_length_words": len(request.script.split()),
            "style_preferences": request.style_preferences or {},
            "raw_response": response[:500] + "..." if len(response) > 500 else response
        }
        
        return MetadataGenerationResponse(
            metadata=metadata,
            generation_metadata=generation_metadata
        )


# Initialize services
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
    
    # Get episode details
    episode = db.query(Episode).filter(Episode.id == request.episode_id).first()
    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")
    
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
            "generated_metadata": result.episode_metadata.dict(),
            "generation_metadata": result.generation_metadata,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in test metadata generation: {e}")
        raise HTTPException(status_code=500, detail=f"Test metadata generation failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)