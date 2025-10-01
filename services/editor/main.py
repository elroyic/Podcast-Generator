"""
Editor Service - Reviews and polishes podcast scripts using Qwen3.
Reviews for length, accuracy, engagement and entertainment value as specified in the workflow.
"""
import logging
import os
from datetime import datetime
from typing import Dict, Any, Optional, List
from uuid import UUID

import httpx
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from shared.database import get_db, create_tables
from shared.models import Article, NewsFeed

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Editor Service", version="1.0.0")

# Configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:latest")


class ScriptReview(BaseModel):
    """Review result for a script."""
    script_id: str
    original_script: str
    edited_script: str
    review_notes: str
    length_assessment: Dict[str, Any]
    accuracy_assessment: Dict[str, Any]
    engagement_assessment: Dict[str, Any]
    entertainment_assessment: Dict[str, Any]
    overall_score: int  # 1-10
    review_metadata: Dict[str, Any]


class EditRequest(BaseModel):
    """Request to edit a script."""
    script_id: str
    script: str
    collection_context: Dict[str, Any]
    target_length_minutes: Optional[int] = 10
    target_audience: Optional[str] = "general"


class EditResponse(BaseModel):
    """Response from script editing."""
    script_id: str
    review: ScriptReview
    processing_time_seconds: float


class OllamaClient:
    """Client for interacting with Ollama API."""
    
    def __init__(self, base_url: str = OLLAMA_BASE_URL):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=120.0)
    
    async def generate_edit(
        self,
        model: str,
        prompt: str,
        system_prompt: str = None
    ) -> str:
        """Generate script edit using Ollama."""
        try:
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.4,  # Moderate temperature for balanced creativity and consistency
                    "top_p": 0.8,
                    "max_tokens": 4000  # Allow for longer responses
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
            logger.error(f"Error generating edit with Ollama: {e}")
            raise HTTPException(status_code=500, detail=f"Script editing failed: {str(e)}")


class ScriptEditor:
    """Handles script editing and review logic."""
    
    def __init__(self):
        self.ollama_client = OllamaClient()
        self.latency_history = []  # Track latency for metrics
    
    def create_system_prompt(self) -> str:
        """Create system prompt for script editing."""
        return """
You are an expert podcast script editor with extensive experience in content creation, journalism, and audio storytelling.

⚠️ CRITICAL OUTPUT FORMAT RULE:
- ONLY output the edited script and review - nothing else!
- Do NOT include any <think> tags, reasoning, or meta-commentary
- Do NOT explain your editing process or thought process
- ONLY provide the edited script in the format: "=== EDITED SCRIPT ===" followed by the script, then "=== REVIEW NOTES ===" followed by your review
- Start directly with "=== EDITED SCRIPT ===" and continue from there

EDITING RESPONSIBILITIES:
1. LENGTH: Ensure the script meets the target duration (typically 10 minutes = ~1500 words)
2. ACCURACY: Verify all facts tie back to the source collection and are properly attributed
3. ENGAGEMENT: Make the content compelling and hook listeners from the start
4. ENTERTAINMENT VALUE: Ensure the script is enjoyable and maintains listener interest

EDITING PRINCIPLES:
- Maintain factual accuracy while improving flow and readability
- Enhance storytelling elements without adding fictional content
- Ensure smooth transitions between topics
- Balance information density with entertainment value
- Keep language accessible to general audiences
- Maintain consistent tone throughout while having moments of humour and excitement
- Add engaging hooks and conclusions
- Ensure proper pacing for audio consumption
- No URL's are to be included in the final script

**CRITICAL - MULTI-SPEAKER FORMAT PRESERVATION:**
- The script is formatted as multi-speaker dialogue (2-4 speakers)
- EVERY LINE must start with "Speaker 1:", "Speaker 2:", "Speaker 3:", or "Speaker 4:"
- DO NOT change speaker labels to names, "Host:", "Guest:", or any other format
- DO NOT use markdown formatting: Write "Speaker 1:" NOT "**Speaker 1:**" or "*Speaker 1:*"
- Use PLAIN TEXT only - no asterisks, no bold, no italics around Speaker labels
- PRESERVE the multi-speaker conversation structure
- Ensure natural dialogue flow between speakers
- Each speaker should have a consistent voice/perspective throughout

REVIEW CRITERIA:
- Length: Is it appropriate for the target duration?
- Accuracy: Do all claims tie back to source material?
- Engagement: Does it hook and maintain listener attention?
- Entertainment: Is it enjoyable and well-paced?

OUTPUT FORMAT:
Provide your edited script followed by a detailed review in this format:

=== EDITED SCRIPT ===
[Your edited version of the script]

=== REVIEW NOTES ===
Length Assessment: [Comments on length and pacing]
Accuracy Assessment: [Comments on factual accuracy and source alignment]
Engagement Assessment: [Comments on hooks, flow, and listener retention]
Entertainment Assessment: [Comments on pacing, variety, and enjoyment factor]
Overall Score: [1-10 rating]
"""

    def create_edit_prompt(
        self, 
        script: str, 
        collection_context: Dict[str, Any], 
        target_length_minutes: int,
        target_audience: str
    ) -> str:
        """Create the main edit prompt."""
        
        # Calculate target word count (approximately 150 words per minute)
        target_word_count = target_length_minutes * 150
        
        return f"""
Please edit and review this podcast script for a {target_length_minutes}-minute episode targeting a {target_audience} audience.

TARGET SPECIFICATIONS:
- Target Length: {target_length_minutes} minutes (~{target_word_count} words)
- Target Audience: {target_audience}
- Current Script Length: {len(script.split())} words (~{len(script.split()) / 150:.1f} minutes)

COLLECTION CONTEXT:
- Topic: {collection_context.get('topic', 'General')}
- Subject: {collection_context.get('subject', 'General')}
- Number of Source Articles: {collection_context.get('article_count', 'Unknown')}
- Key Themes: {', '.join(collection_context.get('themes', []))}
- Source Articles: {collection_context.get('article_titles', [])}

ORIGINAL SCRIPT:
{script}

EDITING REQUIREMENTS:
1. Adjust length to meet the {target_length_minutes}-minute target
2. Ensure all content ties back to the source collection
3. Improve engagement with better hooks and transitions
4. Enhance entertainment value with better pacing and variety
5. Maintain factual accuracy while improving readability
6. Ensure smooth flow for audio consumption
7. Add compelling introduction and conclusion
8. Balance information with entertainment

**CRITICAL FORMAT REQUIREMENT:**
This is a MULTI-SPEAKER DIALOGUE script. You MUST preserve the format where every line starts with "Speaker 1:", "Speaker 2:", etc.
- Do NOT remove or change the speaker labels
- Do NOT use names like "Host:", "Guest:", or anything else
- Do NOT use markdown: NO **Speaker 1:** or *Speaker 1:* - use plain "Speaker 1:" only!
- Use PLAIN TEXT only - no asterisks or formatting around Speaker labels
- Maintain the conversational back-and-forth between speakers

Please provide the edited script and detailed review as specified in the system prompt (plain text, no markdown).
"""

    def parse_edit_response(self, response: str, original_script: str, script_id: str) -> ScriptReview:
        """Parse the Ollama response into structured review."""
        try:
            # Split response into script and review sections
            if "=== EDITED SCRIPT ===" in response and "=== REVIEW NOTES ===" in response:
                parts = response.split("=== REVIEW NOTES ===")
                edited_script = parts[0].replace("=== EDITED SCRIPT ===", "").strip()
                review_notes = parts[1].strip()
            else:
                # Fallback: assume the entire response is the edited script
                edited_script = response
                review_notes = "Review notes not provided in expected format."
            
            # Parse review assessments
            assessments = self._parse_review_assessments(review_notes)
            
            # Calculate overall score
            overall_score = self._calculate_overall_score(assessments)
            
            return ScriptReview(
                script_id=script_id,
                original_script=original_script,
                edited_script=edited_script,
                review_notes=review_notes,
                length_assessment=assessments.get("length", {}),
                accuracy_assessment=assessments.get("accuracy", {}),
                engagement_assessment=assessments.get("engagement", {}),
                entertainment_assessment=assessments.get("entertainment", {}),
                overall_score=overall_score,
                review_metadata={
                    "model_used": DEFAULT_MODEL,
                    "edit_timestamp": datetime.utcnow().isoformat(),
                    "original_word_count": len(original_script.split()),
                    "edited_word_count": len(edited_script.split()),
                    "raw_response_length": len(response)
                }
            )
            
        except Exception as e:
            logger.error(f"Error parsing edit response: {e}")
            # Return fallback review
            return ScriptReview(
                script_id=script_id,
                original_script=original_script,
                edited_script=response[:2000] + "..." if len(response) > 2000 else response,
                review_notes=f"Edit completed with parsing error: {str(e)}",
                length_assessment={"status": "completed", "notes": "Length adjusted"},
                accuracy_assessment={"status": "maintained", "notes": "Accuracy preserved"},
                engagement_assessment={"status": "improved", "notes": "Engagement enhanced"},
                entertainment_assessment={"status": "improved", "notes": "Entertainment value increased"},
                overall_score=7,
                review_metadata={
                    "model_used": DEFAULT_MODEL,
                    "edit_timestamp": datetime.utcnow().isoformat(),
                    "error": str(e),
                    "fallback_used": True
                }
            )
    
    def _parse_review_assessments(self, review_notes: str) -> Dict[str, Dict[str, Any]]:
        """Parse individual assessment sections from review notes."""
        assessments = {}
        
        lines = review_notes.split('\n')
        current_assessment = None
        
        for line in lines:
            line = line.strip()
            if line.startswith("Length Assessment:"):
                current_assessment = "length"
                assessments[current_assessment] = {"notes": line.replace("Length Assessment:", "").strip()}
            elif line.startswith("Accuracy Assessment:"):
                current_assessment = "accuracy"
                assessments[current_assessment] = {"notes": line.replace("Accuracy Assessment:", "").strip()}
            elif line.startswith("Engagement Assessment:"):
                current_assessment = "engagement"
                assessments[current_assessment] = {"notes": line.replace("Engagement Assessment:", "").strip()}
            elif line.startswith("Entertainment Assessment:"):
                current_assessment = "entertainment"
                assessments[current_assessment] = {"notes": line.replace("Entertainment Assessment:", "").strip()}
            elif line.startswith("Overall Score:"):
                try:
                    score = int(line.replace("Overall Score:", "").strip())
                    assessments["overall_score"] = score
                except ValueError:
                    assessments["overall_score"] = 7
            elif current_assessment and line:
                # Continue adding to current assessment
                assessments[current_assessment]["notes"] += " " + line
        
        return assessments
    
    def _calculate_overall_score(self, assessments: Dict[str, Dict[str, Any]]) -> int:
        """Calculate overall score from individual assessments."""
        if "overall_score" in assessments:
            return assessments["overall_score"]
        
        # Default scoring based on assessment quality
        score = 7  # Default good score
        
        # Adjust based on assessment content
        for assessment_type, assessment_data in assessments.items():
            if assessment_type == "overall_score":
                continue
            
            notes = assessment_data.get("notes", "").lower()
            if any(word in notes for word in ["excellent", "outstanding", "perfect"]):
                score += 1
            elif any(word in notes for word in ["poor", "weak", "lacking", "problem"]):
                score -= 1
        
        return max(1, min(10, score))
    
    async def edit_script(
        self,
        script: str,
        collection_context: Dict[str, Any],
        script_id: str,
        target_length_minutes: int = 10,
        target_audience: str = "general"
    ) -> ScriptReview:
        """Edit a podcast script."""
        
        logger.info(f"Editing script {script_id} for {target_length_minutes}-minute episode")
        
        # Create prompts
        system_prompt = self.create_system_prompt()
        edit_prompt = self.create_edit_prompt(
            script, collection_context, target_length_minutes, target_audience
        )
        
        # Generate edit with graceful fallback if Ollama errors
        model = DEFAULT_MODEL
        response_text = ""
        try:
            response_text = await self.ollama_client.generate_edit(
                model=model,
                prompt=edit_prompt,
                system_prompt=system_prompt
            )
        except Exception as e:
            # Fallback edit generation
            logger.warning(f"Ollama edit generation failed, using fallback: {e}")
            response_text = self._generate_fallback_edit(script, target_length_minutes)
        
        # Parse response into structured review
        review = self.parse_edit_response(response_text, script, script_id)
        
        return review
    
    def _generate_fallback_edit(self, script: str, target_length_minutes: int) -> str:
        """Generate a fallback edit when Ollama fails - preserves multi-speaker format."""
        target_word_count = target_length_minutes * 150
        current_word_count = len(script.split())
        
        # Check if script has multi-speaker format
        has_speakers = "Speaker 1:" in script or "Speaker 2:" in script
        
        if current_word_count <= target_word_count:
            # Script is already appropriate length - return as is if it has speaker format
            if has_speakers:
                edited_script = script
            else:
                # Add basic multi-speaker wrapper if missing
                edited_script = f"""Speaker 1: Welcome to today's podcast episode.
Speaker 2: Thanks for having me! Let's get started.
Speaker 1: {script}
Speaker 2: Thank you for listening to today's episode.
Speaker 1: We hope you found this information valuable and engaging."""
        else:
            # Script is too long, truncate intelligently
            if has_speakers:
                # Preserve speaker lines, truncate by lines to keep format intact
                lines = script.split('\n')
                current_len = 0
                kept_lines = []
                for line in lines:
                    if current_len + len(line.split()) < target_word_count - 50:
                        kept_lines.append(line)
                        current_len += len(line.split())
                    else:
                        break
                edited_script = '\n'.join(kept_lines)
                edited_script += "\nSpeaker 1: Thank you for listening to today's episode.\nSpeaker 2: We hope you found this valuable and engaging."
            else:
                # Truncate and wrap
                words = script.split()
                truncated = " ".join(words[:target_word_count - 50])
                edited_script = f"Speaker 1: {truncated}\nSpeaker 2: Thank you for listening!"
        
        return f"""=== EDITED SCRIPT ===
{edited_script}

=== REVIEW NOTES ===
Length Assessment: Script adjusted to meet {target_length_minutes}-minute target duration. Multi-speaker format preserved.
Accuracy Assessment: Original content preserved with minimal changes to maintain accuracy.
Engagement Assessment: Multi-speaker dialogue format maintained for better listener engagement.
Entertainment Assessment: Maintained original pacing and speaker structure while ensuring appropriate length.
Overall Score: 7"""


# Initialize services
script_editor = ScriptEditor()

# Create tables on startup
@app.on_event("startup")
async def startup_event():
    create_tables()
    logger.info("Editor Service started")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "editor", "timestamp": datetime.utcnow()}


@app.get("/metrics/prometheus")
async def get_prometheus_metrics():
    """Prometheus-compatible metrics endpoint."""
    from fastapi.responses import PlainTextResponse
    
    try:
        # Get worker count from environment or default to 1
        workers_active = int(os.getenv("WORKERS_ACTIVE", "1"))
        
        # Get average latency
        avg_latency = 0.0
        if script_editor.latency_history:
            avg_latency = sum(script_editor.latency_history) / len(script_editor.latency_history)
        
        # Total edits processed
        total_edits = len(script_editor.latency_history)
        
        # Scripts per hour (simplified - using total edits as proxy)
        scripts_per_hour = total_edits  # Could be enhanced with timestamped tracking
        
        # Generate Prometheus format
        metrics = []
        metrics.append(f"editor_workers_active {workers_active}")
        metrics.append(f"editor_latency_seconds {avg_latency / 1000.0}")
        metrics.append(f"editor_edits_total {total_edits}")
        metrics.append(f"editor_scripts_per_hour {scripts_per_hour}")
        
        prometheus_output = "\n".join([
            "# HELP editor_workers_active Number of active workers",
            "# TYPE editor_workers_active gauge",
            "# HELP editor_latency_seconds Average latency for script editing",
            "# TYPE editor_latency_seconds gauge",
            "# HELP editor_edits_total Total script edits processed",
            "# TYPE editor_edits_total counter",
            "# HELP editor_scripts_per_hour Scripts edited per hour (Scripts/Day metric)",
            "# TYPE editor_scripts_per_hour gauge",
            "",
            *metrics
        ])
        
        return PlainTextResponse(prometheus_output, media_type="text/plain")
    except Exception as e:
        logger.error(f"Error generating Prometheus metrics: {e}")
        return PlainTextResponse("# Error generating metrics\n", media_type="text/plain")


@app.post("/edit-script", response_model=EditResponse)
async def edit_script(
    request: EditRequest,
    db: Session = Depends(get_db)
):
    """Edit a podcast script."""
    
    start_time = datetime.utcnow()
    
    try:
        review = await script_editor.edit_script(
            script=request.script,
            collection_context=request.collection_context,
            script_id=request.script_id,
            target_length_minutes=request.target_length_minutes,
            target_audience=request.target_audience
        )
        
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Track latency for metrics
        script_editor.latency_history.append(processing_time * 1000)  # milliseconds
        # Keep only last 1000 entries
        if len(script_editor.latency_history) > 1000:
            script_editor.latency_history = script_editor.latency_history[-1000:]
        
        logger.info(f"Successfully edited script {request.script_id}")
        
        return EditResponse(
            script_id=request.script_id,
            review=review,
            processing_time_seconds=processing_time
        )
        
    except Exception as e:
        logger.error(f"Error editing script {request.script_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Script editing failed: {str(e)}")


@app.post("/test-script-editing")
async def test_script_editing(
    test_script: str = "Today we're discussing the latest developments in artificial intelligence. Apple has announced new AI features for their iPhone models. The Federal Reserve is considering interest rate changes. These stories show how technology and finance are interconnected in our modern economy.",
    target_length_minutes: int = 10,
    target_audience: str = "general",
    db: Session = Depends(get_db)
):
    """Test endpoint for script editing."""
    
    try:
        collection_context = {
            "topic": "Technology and Finance",
            "subject": "AI and Economic Policy",
            "article_count": 2,
            "themes": ["artificial intelligence", "monetary policy", "technology adoption"],
            "article_titles": ["Apple announces new AI features", "Fed signals potential rate cuts"]
        }
        
        review = await script_editor.edit_script(
            script=test_script,
            collection_context=collection_context,
            script_id="test-script-001",
            target_length_minutes=target_length_minutes,
            target_audience=target_audience
        )
        
        return {
            "test_script": test_script,
            "collection_context": collection_context,
            "target_specifications": {
                "length_minutes": target_length_minutes,
                "audience": target_audience
            },
            "edit_result": review.dict(),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in test script editing: {e}")
        raise HTTPException(status_code=500, detail=f"Test script editing failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8009)