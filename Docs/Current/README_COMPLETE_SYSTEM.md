# Complete Podcast Generation System

This system implements the complete workflow specified in `Docs/Workflow.md` to generate 10-minute podcasts on current news using VibeVoice in MP3 format.

## System Architecture

The system consists of the following services:

### Core Services

1. **News Feed Service** (Port 8001)
   - Fetches and stores articles from 34 RSS feeds
   - Supports both RSS and MCP feed formats
   - Provides article management and retrieval

2. **Reviewer Service** (Port 8007)
   - Uses Qwen3 for article categorization and classification
   - Generates dynamic tags and topics (not preset lists)
   - Provides importance ranking (1-10)
   - Creates summaries (≤500 characters)

3. **Presenter Service** (Port 8008)
   - Uses gpt-oss-20b for persona-based content generation
   - Generates 1000-word collection briefs
   - Provides 500-word script feedback
   - Each presenter has unique persona and voice

4. **Writer Service** (Port 8010)
   - Uses Qwen3 for script generation
   - Receives collections with feeds, reviews, and presenter briefs
   - Produces podcast scripts of required length
   - Passes scripts to Editor for review

5. **Editor Service** (Port 8009)
   - Uses Qwen3 for script review and polish
   - Reviews for length, accuracy, engagement, and entertainment value
   - Ensures content ties back to source collection
   - Provides structured feedback and scoring

6. **Collections Service** (Port 8011)
   - Manages collections of feeds and content
   - Belongs to Podcast Groups
   - Contains feeds, reviewer output, presenter output, and writer output
   - Ensures minimum 3 feeds before processing

7. **AI Overseer Service** (Port 8012)
   - Central orchestrator for the complete workflow
   - Handles feed processing, categorization, and collection management
   - Manages the complete pipeline from feeds to final MP3
   - Coordinates all services in the workflow

8. **VibeVoice Presenter Service** (Port 8013)
   - Integrates VibeVoice for high-quality text-to-speech
   - Generates MP3 audio files from scripts
   - Falls back to synthetic audio if VibeVoice unavailable
   - Produces stereo MP3 output

## Workflow Implementation

The system follows the exact workflow specified in `Docs/Workflow.md`:

### 1. Feed Processing
- Each feed is sent to the **Reviewer** for categorization and classification
- After review, feeds are summarized and tagged (topic, subject, tags)
- Feeds can belong to multiple **Collections**

### 2. Collections Management
- Only sent to the **Writer** as per Podcast Group schedule
- Must contain at least 3 feeds and summaries before being sent to Writer
- If a collection is incomplete at scheduled time, the podcast is skipped for that cycle
- If skipped, Writer is notified to include an apology/excuse in the next episode

### 3. Script Flow
- Once Editor returns the script, AI Overseer passes it to VibeVoice to generate the final `.mp3` file

### 4. Podcast Group Management
Each Podcast Group includes:
- Tags and Subjects
- Schedule (Daily, Weekly, Monthly)
- Collection (feeds reviewed and grouped)
- Writer
- Presenters (1–4, created per group, voices via VibeVoice)
- Podcast Length

## RSS Feeds

The system includes all 34 RSS feeds specified in the workflow:

**Financial News:**
- MarketWatch, Investing.com, CNBC, Seeking Alpha, The Motley Fool UK
- INO.com Blog, AlphaStreet, Raging Bull, Moneycontrol, Scanz Blog
- Market Screener, Investors Business Daily, Yahoo Finance, IIFL Securities
- Nasdaq, Stock Market.com, Equitymaster, KlickAnalytics

**General News:**
- BBC News, CNN, Reuters, The Guardian, Al Jazeera
- Associated Press, NPR News, DW News, Politico, New York Times

## Model Usage

- **Reviewer**: Qwen3 (not Qwen2.5) for dynamic categorization
- **Writer**: Qwen3 for script generation
- **Editor**: Qwen3 for script review and polish
- **Presenter**: gpt-oss-20b for persona-based briefs and feedback

## Setup Instructions

### 1. Complete System Setup
```bash
# Run the complete setup script
python /workspace/setup_complete_system.py
```

This will:
- Create database tables
- Set up sample podcast groups, presenters, and writers
- Configure RSS feeds
- Create Docker compose overrides

### 2. Start Services
```bash
# Start all services
docker-compose up -d

# Or start with the override
docker-compose -f docker-compose.yml -f docker-compose.override.yml up -d
```

### 3. Test the System
```bash
# Run comprehensive tests
python /workspace/test_complete_workflow.py
```

### 4. Generate a Podcast
```bash
# Use the AI Overseer to generate a complete episode
curl -X POST "http://localhost:8012/test-complete-workflow" \
  -H "Content-Type: application/json" \
  -d '{
    "group_name": "Test Podcast",
    "target_length_minutes": 10
  }'
```

## API Endpoints

### AI Overseer (Main Orchestrator)
- `POST /generate-episode` - Generate complete episode
- `POST /test-complete-workflow` - Test the full workflow
- `GET /health` - Service health check

### Individual Services
Each service provides:
- Health check endpoints
- Test endpoints for individual functionality
- Service-specific API endpoints

## File Structure

```
/workspace/
├── services/
│   ├── news-feed/          # RSS feed management
│   ├── reviewer/           # Article categorization (Qwen3)
│   ├── presenter/          # Persona-based content (gpt-oss-20b)
│   ├── writer/             # Script generation (Qwen3)
│   ├── editor/             # Script review (Qwen3)
│   ├── collections/        # Collection management
│   ├── ai-overseer/        # Workflow orchestration
│   └── presenter/          # VibeVoice integration
├── shared/                 # Shared models and database
├── VibeVoice-Community/    # VibeVoice TTS system
├── setup_complete_system.py
├── test_complete_workflow.py
└── setup_rss_feeds.py
```

## Success Criteria

The system successfully generates a 10-minute podcast on current news using VibeVoice in MP3 format by:

1. ✅ Fetching articles from 34 RSS feeds
2. ✅ Categorizing and classifying articles using Qwen3
3. ✅ Creating collections with minimum 3 feeds
4. ✅ Generating presenter briefs using gpt-oss-20b
5. ✅ Creating scripts using Qwen3
6. ✅ Editing and polishing scripts using Qwen3
7. ✅ Generating MP3 audio using VibeVoice
8. ✅ Following the complete workflow as specified

## Monitoring and Logs

- All services provide health check endpoints
- Comprehensive logging throughout the system
- Test results saved to JSON files
- Service status monitoring via API endpoints

## Troubleshooting

1. **Services not starting**: Check Docker logs with `docker-compose logs [service-name]`
2. **Database issues**: Ensure PostgreSQL is running and accessible
3. **Ollama models**: Verify Qwen3 and gpt-oss-20b models are available
4. **VibeVoice issues**: Check VibeVoice installation and fallback to synthetic audio
5. **RSS feeds**: Some feeds may be temporarily unavailable; system handles gracefully

## Next Steps

1. **Dashboard Implementation**: Create the management dashboard as specified
2. **Scheduling**: Implement cron-based scheduling for podcast groups
3. **Publishing**: Add publishing service for distribution platforms
4. **Scaling**: Implement elastic scaling up to 5 CPUs per service
5. **Monitoring**: Add comprehensive monitoring and alerting