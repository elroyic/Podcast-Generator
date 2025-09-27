# Podcast AI Makefile

.PHONY: help build up down logs clean setup test health

# Default target
help:
	@echo "Podcast AI - Available commands:"
	@echo "  make setup     - Setup the application (install dependencies, pull models)"
	@echo "  make build     - Build all Docker images"
	@echo "  make up        - Start all services"
	@echo "  make down      - Stop all services"
	@echo "  make logs      - View logs from all services"
	@echo "  make clean     - Clean up containers, images, and volumes"
	@echo "  make test      - Run health checks"
	@echo "  make health    - Check service health"
	@echo "  make dev       - Start in development mode"
	@echo "  make shell     - Open shell in API Gateway container"

# Setup the application
setup:
	@echo "🎙️  Setting up Podcast AI..."
	@./setup.sh

# Build Docker images
build:
	@echo "🔨 Building Docker images..."
	docker compose build

# Start all services
up:
	@echo "🚀 Starting Podcast AI services..."
	docker compose up -d

# Stop all services
down:
	@echo "🛑 Stopping Podcast AI services..."
	docker compose down

# View logs
logs:
	@echo "📋 Viewing logs..."
	docker compose logs -f

# Clean up everything
clean:
	@echo "🧹 Cleaning up..."
	docker compose down -v --remove-orphans
	docker system prune -f
	docker volume prune -f

# Run health checks
test:
	@echo "🔍 Running health checks..."
	@curl -f http://localhost:8000/health && echo "✅ API Gateway healthy" || echo "❌ API Gateway unhealthy"
	@curl -f http://localhost:8001/health && echo "✅ News Feed Service healthy" || echo "❌ News Feed Service unhealthy"
	@curl -f http://localhost:8002/health && echo "✅ Text Generation Service healthy" || echo "❌ Text Generation Service unhealthy"
	@curl -f http://localhost:8003/health && echo "✅ Writer Service healthy" || echo "❌ Writer Service unhealthy"
	@curl -f http://localhost:8004/health && echo "✅ Presenter Service healthy" || echo "❌ Presenter Service unhealthy"
	@curl -f http://localhost:8005/health && echo "✅ Publishing Service healthy" || echo "❌ Publishing Service unhealthy"
	@curl -f http://localhost:8006/health && echo "✅ AI Overseer Service healthy" || echo "❌ AI Overseer Service unhealthy"

# Check service health
health:
	@echo "🔍 Checking service health..."
	@curl -s http://localhost:8000/health | python -m json.tool

# Development mode
dev:
	@echo "🔧 Starting in development mode..."
	docker compose -f docker-compose.yml -f docker-compose.override.yml up

# Open shell in API Gateway
shell:
	@echo "🐚 Opening shell in API Gateway container..."
	docker compose exec api-gateway sh

# Database operations
db-migrate:
	@echo "🗄️  Running database migrations..."
	docker compose exec api-gateway python -c "from shared.database import create_tables; create_tables()"

# Create sample data
sample-data:
	@echo "📝 Creating sample data..."
	@curl -X POST http://localhost:8000/api/presenters \
		-H "Content-Type: application/json" \
		-d '{"name": "Alex Johnson", "bio": "Tech enthusiast and podcast host", "gender": "non-binary", "country": "US", "city": "San Francisco", "specialties": ["technology", "AI"], "expertise": ["software development", "machine learning"]}'
	@curl -X POST http://localhost:8000/api/writers \
		-H "Content-Type: application/json" \
		-d '{"name": "AI Writer", "capabilities": ["title", "description", "tags", "keywords"]}'
	@curl -X POST http://localhost:8000/api/news-feeds \
		-H "Content-Type: application/json" \
		-d '{"source_url": "https://feeds.bbci.co.uk/news/technology/rss.xml", "name": "BBC Technology", "type": "RSS"}'

# Quick start
start: build up
	@echo "✅ Podcast AI is starting up!"
	@echo "📱 Admin interface: http://localhost:8000"
	@echo "🔍 Health check: http://localhost:8000/health"
	@echo "📚 API docs: http://localhost:8000/docs"

# Full restart
restart: down up
	@echo "🔄 Podcast AI restarted!"

# Show service status
status:
	@echo "📊 Service status:"
	@docker compose ps
