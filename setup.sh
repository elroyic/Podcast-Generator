#!/bin/bash

set -euo pipefail

# Podcast AI Setup Script
echo "🎙️  Setting up Podcast AI Application..."

# Check if Docker is installed
if ! command -v docker >/dev/null 2>&1; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose plugin is available
if ! docker compose version >/dev/null 2>&1; then
    echo "❌ Docker Compose plugin not found (docker compose). Please install/update Docker Desktop or docker-compose-plugin."
    exit 1
fi

# Optional: Check for NVIDIA GPU availability (for vLLM/Ollama GPU acceleration)
if command -v nvidia-smi >/dev/null 2>&1; then
    echo "✅ NVIDIA GPU detected. vLLM/Ollama can use GPU acceleration."
else
    echo "⚠️  No NVIDIA GPU detected. vLLM/Ollama will run on CPU (slower)."
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        echo "📝 Creating .env from .env.example..."
        cp .env.example .env
    else
        echo "📝 Creating minimal .env with sensible defaults..."
        {
            echo "# Basic defaults created by setup.sh"
            echo "OLLAMA_BASE_URL=http://ollama:11434"
            echo "OLLAMA_MODEL=llama3.1"
            echo "REVIEWER_CONF_THRESHOLD=0.85"
            echo "REVIEWER_LIGHT_MODEL=qwen2:0.5b"
            echo "REVIEWER_HEAVY_MODEL=qwen3:4b"
        } > .env
    fi
    echo "✅ .env ready. You can edit it to customize models and settings."
fi

# Pre-pull container images to save time on first startup
echo "🐳 Pulling base images (this may take a while the first time)..."
docker compose pull || true

# Start infrastructure services needed for model pulls
echo "🚀 Starting core infrastructure (Postgres, Redis, Ollama, vLLM)..."
docker compose up -d postgres redis ollama vllm

# Wait for Ollama container to be ready
echo "⏳ Waiting for Ollama service (container) to be ready..."
ATTEMPTS=0
until docker compose exec -T ollama ollama list >/dev/null 2>&1 || [ $ATTEMPTS -ge 30 ]; do
    ATTEMPTS=$((ATTEMPTS+1))
    sleep 2
done
if [ $ATTEMPTS -ge 30 ]; then
    echo "❌ Ollama did not become ready in time. Check 'docker compose logs ollama'."
    exit 1
fi
echo "✅ Ollama is ready."

# Pull required Ollama models inside the container
echo "🤖 Pulling Ollama models inside the container..."
set +e
docker compose exec -T ollama ollama pull llama3.1 || echo "⚠️  Failed to pull llama3.1 (check model name/network)."
docker compose exec -T ollama ollama pull qwen2.5:latest || docker compose exec -T ollama ollama pull qwen2.5 || echo "⚠️  Failed to pull qwen2.5 (optional)."
docker compose exec -T ollama ollama pull qwen3:latest || echo "ℹ️  'qwen3:latest' may not be available on Ollama; skipping."
set -e
echo "✅ Ollama model pulls attempted."

# Warm up vLLM by triggering a tiny request (host port 8020)
echo "🔥 Warming up vLLM (this may download models on first run)..."
VLLM_WARMUP_PAYLOAD='{"model":"Qwen2-0.5B","prompt":"hello","max_tokens":8}'
if curl -sf -X POST "http://localhost:8020/v1/completions" \
    -H "Content-Type: application/json" \
    -d "$VLLM_WARMUP_PAYLOAD" >/dev/null 2>&1; then
    echo "✅ vLLM warmed (Qwen2-0.5B)."
else
    echo "⚠️  vLLM warmup request failed. The container may still be downloading the model."
fi

# Build and start all services
echo "🔨 Building and starting all Docker services..."
docker compose build
docker compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 30

# Check service health
echo "🔍 Checking service health..."
if curl -fsS http://localhost:8000/health >/dev/null 2>&1; then
    echo "✅ API Gateway is healthy"
else
    echo "❌ API Gateway health check failed"
fi

echo ""
echo "🎉 Setup complete!"
echo ""
echo "📱 Access the admin interface at: http://localhost:8000"
echo "📊 Health check: http://localhost:8000/health"
echo "📚 API documentation: http://localhost:8000/docs"
echo ""
echo "🔧 To stop services: docker compose down"
echo "📋 To view logs: docker compose logs -f"
echo ""
echo "ℹ️  Note: Ollama and vLLM are running in Docker containers managed by Compose."
