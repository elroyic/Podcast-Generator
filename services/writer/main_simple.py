"""
Simplified Writer Service for local testing.
This version generates mock metadata without requiring Ollama.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
from uuid import UUID

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Writer Service (Simple)", version="1.0.0")


class MetadataGenerationRequest(BaseModel):
    episode_id: UUID
    script: str
    group_id: UUID
    style_preferences: Optional[Dict[str, Any]] = None


class EpisodeMetadataCreate(BaseModel):
    title: str
    description: str
    tags: list
    keywords: list
    category: str
    subcategory: str
    language: str
    country: str


class MetadataGenerationResponse(BaseModel):
    metadata: EpisodeMetadataCreate
    generation_metadata: Dict[str, Any]


def generate_mock_metadata(script: str, group_id: UUID) -> EpisodeMetadataCreate:
    """Generate mock episode metadata from script."""
    
    # Extract first few words as potential title
    words = script.split()[:8]
    title = " ".join(words) + "..." if len(words) == 8 else " ".join(words)
    
    # Generate description from script summary
    description = f"An engaging podcast episode discussing current topics and news. Generated for podcast group {group_id}."
    
    # Mock tags and keywords
    tags = ["technology", "news", "podcast", "current events"]
    keywords = ["technology news", "podcast", "current events", "discussion"]
    
    return EpisodeMetadataCreate(
        title=title,
        description=description,
        tags=tags,
        keywords=keywords,
        category="Technology",
        subcategory="News",
        language="en",
        country="US"
    )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "writer-simple", "timestamp": datetime.utcnow()}


@app.post("/generate-metadata", response_model=MetadataGenerationResponse)
async def generate_metadata(request: MetadataGenerationRequest):
    """Generate episode metadata from script."""
    
    logger.info(f"Generating metadata for episode {request.episode_id}")
    
    try:
        # Generate mock metadata
        metadata = generate_mock_metadata(request.script, request.group_id)
        
        generation_metadata = {
            "model_used": "mock-metadata-generator",
            "generation_timestamp": datetime.utcnow().isoformat(),
            "script_length": len(request.script.split()),
            "group_id": str(request.group_id),
            "style_preferences": request.style_preferences or {}
        }
        
        return MetadataGenerationResponse(
            metadata=metadata,
            generation_metadata=generation_metadata
        )
        
    except Exception as e:
        logger.error(f"Error generating metadata: {e}")
        raise HTTPException(status_code=500, detail=f"Metadata generation failed: {str(e)}")


@app.post("/test-metadata-generation")
async def test_metadata_generation():
    """Test endpoint for metadata generation."""
    
    mock_script = "Welcome to today's podcast where we discuss the latest in technology and current events."
    mock_group_id = UUID("12345678-1234-1234-1234-123456789012")
    
    metadata = generate_mock_metadata(mock_script, mock_group_id)
    
    return {
        "metadata": metadata.dict(),
        "model_used": "mock-metadata-generator",
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)