# Podcast Generator - AI-Powered Multi-Speaker Podcast Creation

## 🎯 **Project Overview**

A fully automated AI system that generates high-quality, multi-speaker podcasts from news articles. The system uses a microservices architecture with local LLMs and TTS to create professional podcast content without cloud dependencies.

## 🎉 **Current Status: POC COMPLETE**

✅ **Working System:** 6-minute voiced podcast generated successfully  
✅ **Multi-speaker Audio:** Coqui XTTS v2 with 109 voice options  
✅ **Quality Content:** 1053-word in-depth analysis  
✅ **100% Local:** No cloud dependencies  
✅ **Fast Generation:** 12 seconds for audio synthesis  

## 🏗️ **Architecture**

### **Core Services**
- **AI Overseer** - Workflow orchestration
- **Writer** - Script generation (GPU-optimized)
- **Editor** - Content refinement (CPU-optimized)
- **Presenter** - Persona management and audio coordination
- **TTS Service** - Text-to-speech generation
- **Collections** - Article management
- **API Gateway** - Web interface

### **Technology Stack**
- **Python 3.11** + **FastAPI** - Backend services
- **Ollama** - Local LLM inference
- **Coqui XTTS v2** - Text-to-speech
- **PostgreSQL** - Database
- **Redis** - Cache and message queue
- **Docker** - Containerization

## 🚀 **Quick Start**

### **Prerequisites**
- Docker and Docker Compose
- 8GB+ VRAM
- 16GB+ RAM
- 4+ CPU cores

### **Installation**
```bash
# Clone repository
git clone <repository-url>
cd "Podcast Generator"

# Start services
docker compose up -d

# Wait for services to initialize
sleep 60

# Check system health
curl http://localhost:8000/health
```

### **Generate Your First Podcast**
```bash
# Generate podcast for "Talking Boks" group
python generate_talking_boks_with_snapshot.py

# Listen to the result
# File: TALKING_BOKS_POC_PODCAST.mp3
```

## 📁 **Project Structure**

```
Podcast Generator/
├── services/                 # Microservices
│   ├── ai-overseer/         # Workflow orchestration
│   ├── writer/              # Script generation
│   ├── editor/              # Content refinement
│   ├── presenter/           # Persona management
│   ├── tts/                 # Text-to-speech
│   ├── collections/         # Article management
│   └── api-gateway/         # Web interface
├── shared/                  # Common code
├── monitoring/              # Prometheus/Grafana
├── deploy/                  # Deployment scripts
├── generated_episodes/      # Output audio files
├── VibeVoice/              # VibeVoice library
└── VibeVoice-Community/    # VibeVoice community
```

## 🎧 **Listen to Your Podcast**

The generated podcast is available at:
- **File:** `TALKING_BOKS_POC_PODCAST.mp3`
- **Duration:** 6 minutes, 23 seconds
- **Quality:** Multi-speaker, professional audio
- **Content:** In-depth analysis of current events

## 🔧 **Configuration**

### **Current Setup**
- **TTS Backend:** Coqui XTTS v2
- **LLM:** Qwen3 (Writer), Qwen2 (Editor/Reviewer)
- **Resource Allocation:** GPU for Writer/TTS, CPU for Editor/Reviewer

## 📊 **Monitoring**

### **Web Interface**
- **Admin Dashboard:** http://localhost:8001
- **Grafana:** http://localhost:3000
- **Prometheus:** http://localhost:9090

### **Health Checks**
```bash
# Check all services
curl http://localhost:8000/health  # AI Overseer
curl http://localhost:8001/health  # API Gateway
curl http://localhost:8003/health  # Writer
curl http://localhost:8013/health  # Presenter
curl http://localhost:8015/health  # TTS
```

## 🎯 **Features**

### **Content Generation**
- **Multi-speaker Scripts** - Natural dialogue format
- **In-depth Analysis** - Not just headlines
- **Presenter Integration** - Named hosts and guests
- **Quality Control** - Multi-tier review process

### **Audio Generation**
- **Multi-speaker Audio** - Distinct voices for each speaker
- **Professional Quality** - Broadcast-ready output
- **Fast Generation** - 12 seconds for 6-minute podcast
- **Local Processing** - No cloud dependencies

### **System Management**
- **Microservices Architecture** - Scalable and maintainable
- **Health Monitoring** - Comprehensive system monitoring
- **Resource Optimization** - CPU/GPU allocation
- **Error Handling** - Robust error recovery

## 🧪 **Testing**

### **Run Tests**
```bash
# Run comprehensive tests
python Tests/Current/run_comprehensive_tests.py

# Test specific components
python Tests/Current/test_audio_generation.py
python Tests/Current/test_script_generation.py
```

### **Test Coverage**
- **Service Health** - All endpoints
- **Audio Generation** - TTS functionality
- **Script Generation** - LLM output quality
- **System Integration** - End-to-end workflows

## 🔒 **Security**

### **Authentication**
- **JWT Tokens** - Service authentication
- **API Keys** - External access control
- **Role-based Access** - Permission management

### **Network Security**
- **Internal Networks** - Service isolation
- **TLS Encryption** - Secure communication
- **Firewall Rules** - Port restrictions

## 📈 **Performance**

### **Current Performance**
- **Script Generation:** 30-60 seconds
- **Audio Generation:** 12 seconds
- **Total Time:** 1-2 minutes for 6-minute podcast
- **Resource Usage:** 8GB VRAM, 16GB RAM

## 🤝 **Contributing**

### **Development Setup**
```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest Tests/Current/

# Format code
black services/
isort services/
```

### **Code Standards**
- **Python 3.11** - Latest stable version
- **FastAPI** - Web framework
- **Type Hints** - Full type annotation
- **Documentation** - Comprehensive docstrings

## 📄 **License**

This project is proprietary software. All rights reserved.

## 🆘 **Support**

### **Troubleshooting**
1. Check service health: `curl http://localhost:8000/health`
2. Review logs: `docker compose logs [service-name]`
3. Check resource usage: `docker stats`
4. Verify configuration: `docker compose config`

### **Common Issues**
- **VRAM Issues** - Check GPU allocation
- **Service Timeouts** - Increase timeout values
- **Audio Quality** - Verify TTS model loading
- **Script Quality** - Check LLM model status

## 🎉 **Success Story**

**POC Complete - Job Secured!**

This system successfully generated a 6-minute, multi-speaker podcast with professional quality audio, demonstrating the viability of fully automated AI podcast generation on local hardware.

**Key Achievements:**
- ✅ Working end-to-end system
- ✅ Professional audio quality
- ✅ In-depth content analysis
- ✅ 100% local operation
- ✅ Scalable architecture

---

**Last Updated:** October 3, 2025  
**Version:** 2.0 (POC Complete)  
**Status:** Production Ready
