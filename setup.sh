#!/bin/bash

# Podcast AI Setup Script
echo "🎙️  Setting up Podcast AI Application..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Check if Ollama is installed
if ! command -v ollama &> /dev/null; then
    echo "⚠️  Ollama is not installed. Installing Ollama..."
    curl -fsSL https://ollama.ai/install.sh | sh
    echo "✅ Ollama installed. Please restart your terminal and run this script again."
    exit 0
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "✅ .env file created. Please edit it with your configuration."
fi

# Pull required Ollama models
echo "🤖 Pulling Ollama models..."
ollama pull llama3.1
echo "✅ Ollama models ready."

# Start Ollama service in background
echo "🚀 Starting Ollama service..."
ollama serve &
OLLAMA_PID=$!
echo "✅ Ollama service started (PID: $OLLAMA_PID)"

# Wait for Ollama to be ready
echo "⏳ Waiting for Ollama to be ready..."
sleep 10

# Build and start Docker services
echo "🐳 Building and starting Docker services..."
docker-compose build
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 30

# Check service health
echo "🔍 Checking service health..."
curl -f http://localhost:8000/health > /dev/null 2>&1
if [ $? -eq 0 ]; then
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
echo "🔧 To stop services: docker-compose down"
echo "📋 To view logs: docker-compose logs -f"
echo ""
echo "⚠️  Note: Keep Ollama running in the background for the services to work properly."
echo "   Ollama PID: $OLLAMA_PID"
