# Podcast AI Application

A comprehensive microservices-based podcast generation system that automatically creates podcast episodes from news feeds using AI.

## 🎯 Overview

This application automatically generates podcast episodes by:
1. **Fetching news articles** from RSS/MCP feeds
2. **Generating podcast scripts** using Ollama LLM
3. **Creating episode metadata** (titles, descriptions, tags)
4. **Converting scripts to audio** using VibeVoice-1.5B TTS
5. **Publishing episodes** to local hosting platforms

## 🏗️ Architecture

The system consists of 8 microservices:

| Service | Port | Description |
|---------|------|-------------|
| **API Gateway** | 8000 | Central entry point and admin interface |
| **News Feed** | 8001 | RSS/MCP feed fetching and article storage |
| **Text Generation** | 8002 | Podcast script generation using Ollama |
| **Writer** | 8003 | Episode metadata generation |
| **Presenter** | 8004 | Text-to-speech using VibeVoice-1.5B |
| **Publishing** | 8005 | Episode publishing to platforms |
| **AI Overseer** | 8006 | Central orchestration and scheduling |
| **Podcast Host** | 8006 | Local podcast hosting and RSS feeds |
| **Nginx** | 8080 | Static file serving and request proxying |

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- Ollama (for LLM inference)
- NVIDIA GPU (recommended for VibeVoice)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd podcast-ai
   ```

2. **Setup the application**
   ```bash
   make setup
   ```

3. **Start all services**
   ```bash
   make up
   ```

4. **Access the admin interface**
   - Admin Dashboard: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - Health Check: http://localhost:8000/health

### Manual Setup

If you prefer manual setup:

1. **Install Ollama**
   ```bash
   curl -fsSL https://ollama.ai/install.sh | sh
   ollama serve &
   ollama pull llama3.1
   ```

2. **Create environment file**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Build and start services**
   ```bash
   docker-compose build
   docker-compose up -d
   ```

## 📋 Available Commands

```bash
make help          # Show all available commands
make setup         # Setup the application
make build         # Build Docker images
make up            # Start all services
make down          # Stop all services
make logs          # View logs from all services
make test          # Run health checks
make health        # Check service health
make clean         # Clean up containers and volumes
```

## 🔧 Configuration

### Environment Variables

Key configuration options in `.env`:

```bash
# Database
DATABASE_URL=postgresql://podcast_user:podcast_pass@localhost:5432/podcast_ai

# Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1

# Local Storage
LOCAL_STORAGE_PATH=/app/storage
LOCAL_SERVER_URL=http://localhost:8080

# VibeVoice
VIBEVOICE_MODEL=microsoft/VibeVoice-1.5B
```

### Service Configuration

Each service can be configured independently:

- **News Feed Service**: Configure RSS/MCP feed sources
- **Text Generation**: Adjust Ollama model and prompts
- **Presenter Service**: Configure VibeVoice settings
- **Publishing Service**: Set up platform credentials

## 📊 Usage

### 1. Create a Presenter

```bash
curl -X POST http://localhost:8000/api/presenters \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Alex Johnson",
    "bio": "Tech enthusiast and podcast host",
    "gender": "non-binary",
    "country": "US",
    "specialties": ["technology", "AI"]
  }'
```

### 2. Create a Writer

```bash
curl -X POST http://localhost:8000/api/writers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "AI Writer",
    "capabilities": ["title", "description", "tags", "keywords"]
  }'
```

### 3. Add a News Feed

```bash
curl -X POST http://localhost:8000/api/news-feeds \
  -H "Content-Type: application/json" \
  -d '{
    "source_url": "https://feeds.bbci.co.uk/news/technology/rss.xml",
    "name": "BBC Technology",
    "type": "RSS"
  }'
```

### 4. Create a Podcast Group

```bash
curl -X POST http://localhost:8000/api/podcast-groups \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Tech Talk Daily",
    "description": "Daily technology news podcast",
    "category": "Technology",
    "presenter_ids": ["<presenter-id>"],
    "writer_id": "<writer-id>",
    "news_feed_ids": ["<feed-id>"],
    "schedule": "0 9 * * 1"
  }'
```

### 5. Generate an Episode

```bash
curl -X POST http://localhost:8000/api/generate-episode \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": "<group-id>"
  }'
```

## 🧪 Testing

### Run System Tests

```bash
python test_system.py
```

### Individual Service Tests

```bash
# Test text generation
curl http://localhost:8002/test-generation

# Test audio generation
curl http://localhost:8004/test-audio-generation

# Test metadata generation
curl http://localhost:8003/test-metadata-generation

# Test publishing
curl http://localhost:8005/test-publish
```

## 📁 Project Structure

```
podcast-ai/
├── services/
│   ├── api-gateway/          # Central API and admin interface
│   ├── ai-overseer/          # Orchestration and scheduling
│   ├── news-feed/            # RSS/MCP feed processing
│   ├── text-generation/      # Script generation with Ollama
│   ├── writer/               # Metadata generation
│   ├── presenter/            # Text-to-speech with VibeVoice
│   ├── publishing/           # Episode publishing
│   └── podcast-host/         # Local hosting and RSS feeds
├── shared/                   # Shared models and database
├── Docs/                     # Documentation
├── docker-compose.yml        # Service orchestration
├── nginx.conf               # Nginx configuration
├── Makefile                 # Build and deployment commands
└── test_system.py           # Comprehensive system tests
```

## 🔍 Monitoring

### Health Checks

- **API Gateway**: http://localhost:8000/health
- **Individual Services**: http://localhost:800X/health
- **System Stats**: http://localhost:8000/api/stats

### Logs

```bash
# View all logs
make logs

# View specific service logs
docker-compose logs -f api-gateway
docker-compose logs -f ai-overseer
```

## 🚨 Troubleshooting

### Common Issues

1. **Services not starting**
   - Check if Ollama is running: `ollama serve`
   - Verify Docker is running: `docker ps`
   - Check logs: `make logs`

2. **Database connection errors**
   - Ensure PostgreSQL is running
   - Check DATABASE_URL in .env
   - Run: `make db-migrate`

3. **Audio generation fails**
   - Verify VibeVoice model is available
   - Check GPU availability for CUDA
   - Review presenter service logs

4. **Text generation issues**
   - Ensure Ollama is running
   - Check if model is pulled: `ollama list`
   - Verify OLLAMA_BASE_URL in .env

### Debug Mode

```bash
# Start in development mode
make dev

# Access service shell
make shell
```

## 🔒 Security

- All services run as non-root users
- Database credentials are configurable
- API endpoints include proper validation
- Static files served with security headers

## 📈 Performance

### Optimization Tips

1. **GPU Acceleration**: Use NVIDIA GPU for VibeVoice
2. **Model Caching**: Ollama models are cached locally
3. **Database Indexing**: Proper indexes on frequently queried fields
4. **Resource Limits**: Configure Docker resource limits

### Scaling

- Services can be scaled horizontally
- Use load balancer for high availability
- Consider Redis clustering for Celery
- Database read replicas for read-heavy workloads

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **Ollama** for local LLM inference
- **VibeVoice** for text-to-speech capabilities
- **FastAPI** for the web framework
- **Docker** for containerization

## 📞 Support

For support and questions:
- Create an issue in the repository
- Check the documentation in `Docs/`
- Review the troubleshooting section above

---

**Happy Podcasting! 🎙️**