# Podcast AI Application

An automated system that produces complete podcast episodes (≈ 60‑80 min) using AI. The system gathers topical news from RSS/MCP feeds, generates full episode scripts, converts scripts to spoken audio using VibeVoice-1.5B, and publishes finished episodes to podcast-hosting platforms.

## Architecture

The application follows a microservices architecture with the following services:

- **API Gateway** (Port 8000): Central entry point and admin interface
- **News Feed Service** (Port 8001): RSS/MCP feed fetching and article storage
- **Text Generation Service** (Port 8002): Script generation using Ollama
- **Writer Service** (Port 8003): Episode metadata generation using Ollama
- **Presenter Service** (Port 8004): Text-to-speech using VibeVoice-1.5B
- **Publishing Service** (Port 8005): Publishing to podcast hosting platforms
- **AI Overseer Service** (Port 8006): Central orchestrator and scheduler

## Prerequisites

- Docker and Docker Compose
- NVIDIA GPU (recommended for VibeVoice model)
- PostgreSQL database
- Redis server
- Ollama with appropriate models

## Quick Start

1. **Clone and setup**:
   ```bash
   git clone <repository>
   cd podcast-ai
   cp .env.example .env
   # Edit .env with your configuration
   ```

2. **Start Ollama** (required for LLM functionality):
   ```bash
   # Install Ollama if not already installed
   curl -fsSL https://ollama.ai/install.sh | sh
   
   # Pull a model (e.g., llama3.1)
   ollama pull llama3.1
   
   # Start Ollama service
   ollama serve
   ```

3. **Start the application**:
   ```bash
   docker-compose up -d
   ```

4. **Access the admin interface**:
   - Open http://localhost:8000 in your browser
   - The API Gateway provides the admin dashboard

## Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string  
- `OLLAMA_BASE_URL`: Ollama service URL
- AWS credentials for S3 storage
- Service URLs for local development

### Database Setup

The application uses PostgreSQL with the following main entities:

- **PodcastGroup**: Podcast configurations and schedules
- **Presenter**: AI voice personalities
- **Writer**: AI script writers
- **NewsFeed**: RSS/MCP feed sources
- **Episode**: Generated podcast episodes
- **Article**: News articles from feeds

### Model Requirements

- **Ollama Models**: Install `llama3.1` or similar for text generation
- **VibeVoice-1.5B**: Will be downloaded automatically by the Presenter service

## Usage

### Creating a Podcast Group

1. Go to the admin interface at http://localhost:8000
2. Click "New Podcast Group"
3. Configure:
   - Name, description, category
   - Language and country settings
   - Schedule (cron expression)
   - Assign presenters and writers
   - Add news feed sources

### Manual Episode Generation

```bash
# Trigger episode generation for a specific group
curl -X POST http://localhost:8000/api/generate-episode \
  -H "Content-Type: application/json" \
  -d '{"group_id": "your-group-id", "force_regenerate": false}'
```

### API Endpoints

- `GET /health` - System health check
- `GET /api/podcast-groups` - List podcast groups
- `POST /api/podcast-groups` - Create podcast group
- `GET /api/episodes` - List episodes
- `POST /api/generate-episode` - Generate new episode
- `GET /api/stats` - System statistics

## Development

### Running Individual Services

Each service can be run independently:

```bash
# News Feed Service
cd services/news-feed
pip install -r requirements.txt
uvicorn main:app --port 8001

# Text Generation Service  
cd services/text-generation
pip install -r requirements.txt
uvicorn main:app --port 8002

# ... and so on for other services
```

### Testing

```bash
# Run health checks
curl http://localhost:8000/health

# Test text generation
curl -X POST http://localhost:8002/test-generation \
  -H "Content-Type: application/json" \
  -d '{"test_prompt": "Write a 2-minute podcast intro about tech news"}'

# Test metadata generation
curl -X POST http://localhost:8003/test-metadata-generation
```

## Monitoring

### Health Checks

Each service provides health check endpoints:
- `http://localhost:8000/health` - Overall system health
- `http://localhost:8001/health` - News Feed Service
- `http://localhost:8002/health` - Text Generation Service
- etc.

### Logs

View logs for all services:
```bash
docker-compose logs -f
```

View logs for specific service:
```bash
docker-compose logs -f news-feed
```

### Celery Tasks

Monitor background tasks:
```bash
# View active tasks
docker-compose exec ai-overseer celery -A app.celery inspect active

# View scheduled tasks
docker-compose exec ai-overseer celery -A app.celery inspect scheduled
```

## Troubleshooting

### Common Issues

1. **Ollama connection errors**: Ensure Ollama is running and accessible
2. **Database connection errors**: Check PostgreSQL is running and credentials are correct
3. **Redis connection errors**: Verify Redis server is accessible
4. **GPU memory errors**: VibeVoice model requires sufficient GPU memory

### Debug Mode

Enable debug logging by setting `LOG_LEVEL=DEBUG` in your `.env` file.

### Service Dependencies

Services have the following startup dependencies:
- All services depend on PostgreSQL
- AI Overseer depends on Redis
- Text Generation and Writer services depend on Ollama
- Presenter service depends on VibeVoice model

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.