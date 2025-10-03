# EVO-X2 Deployment Guide

## 🎯 **Target Hardware: AMD Ryzen AI Max+ 395**

### **Specifications**
- **CPU:** 16-core, 32-thread Zen 5
- **RAM:** 128GB LPDDR5 8000MT (32GB system + 96GB VRAM)
- **Storage:** 6TB NVMe PCIe Gen 4
- **NPU:** 50 TOPS AI acceleration
- **Graphics:** Radeon 8060S (40 cores, 2900 MHz)

### **Performance Expectations**
- **VibeVoice Generation:** 30-60 seconds for 15-minute podcast
- **Concurrent Processing:** Multiple services simultaneously
- **Voice Cloning:** Real-time custom voice generation
- **System Uptime:** 99.9% availability

---

## 🚀 **Deployment Strategy**

### **Phase 1: Hardware Preparation**

#### **1.1 System Setup**
```bash
# 1. Install Ubuntu 22.04 LTS
# 2. Update system
sudo apt update && sudo apt upgrade -y

# 3. Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# 4. Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 5. Install NVIDIA Container Toolkit (for GPU support)
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get update && sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker
```

#### **1.2 VRAM Configuration**
```bash
# Configure 96GB VRAM allocation
# Edit /etc/default/grub
sudo nano /etc/default/grub

# Add: GRUB_CMDLINE_LINUX="nvidia-drm.modeset=1 vram=96G"
# Update grub
sudo update-grub
sudo reboot
```

#### **1.3 Verify Hardware**
```bash
# Check VRAM allocation
nvidia-smi
# Should show 96GB VRAM

# Check CPU cores
nproc
# Should show 32 threads

# Check RAM
free -h
# Should show 128GB total
```

### **Phase 2: Software Deployment**

#### **2.1 Clone Repository**
```bash
# Clone the project
git clone <repository-url>
cd "Podcast Generator"

# Copy configuration files
cp docker-compose.yml docker-compose.evo-x2.yml
cp .env.example .env
```

#### **2.2 Environment Configuration**
```bash
# Edit .env file
nano .env

# Key configurations for EVO-X2:
DATABASE_URL=postgresql://postgres:password@postgres:5432/podcast_generator
REDIS_URL=redis://redis:6379/0
OLLAMA_KEEP_ALIVE=0
OLLAMA_NUM_THREADS=16
USE_VIBEVOICE=true
TTS_BACKEND=vibevoice
VIBEVOICE_MODEL=VibeVoice-1.5B
VOICE_SAMPLES_DIR=/app/voice_samples
```

#### **2.3 Docker Compose Updates**
```yaml
# docker-compose.evo-x2.yml
version: '3.8'

services:
  # Ollama GPU Service (for Writer and VibeVoice)
  ollama:
    image: ollama/ollama:latest
    container_name: ollama-gpu
    ports:
      - "11434:11434"
    environment:
      - OLLAMA_KEEP_ALIVE=0
      - OLLAMA_NUM_THREADS=16
    volumes:
      - ollama_data:/root/.ollama
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    runtime: nvidia

  # Ollama CPU Service (for Editor, Reviewer, Presenter)
  ollama-cpu:
    image: ollama/ollama:latest
    container_name: ollama-cpu
    ports:
      - "11435:11434"
    environment:
      - OLLAMA_KEEP_ALIVE=0
      - OLLAMA_NUM_THREADS=16
    volumes:
      - ollama_cpu_data:/root/.ollama

  # TTS Service with VibeVoice
  tts:
    build: ./services/tts
    container_name: tts-service
    ports:
      - "8015:8015"
    environment:
      - USE_VIBEVOICE=true
      - VIBEVOICE_MODEL=VibeVoice-1.5B
      - VOICE_SAMPLES_DIR=/app/voice_samples
      - CUDA_VISIBLE_DEVICES=0
    volumes:
      - episode_storage:/app/storage
      - ./voice_samples:/app/voice_samples
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    runtime: nvidia
    depends_on:
      - postgres
      - redis

  # Writer Service (GPU-optimized)
  writer:
    build: ./services/writer
    container_name: writer-service
    ports:
      - "8003:8003"
    environment:
      - OLLAMA_BASE_URL=http://ollama:11434
      - OLLAMA_MODEL=qwen3:latest
      - MAX_TOKENS_PER_REQUEST=5000
    depends_on:
      - ollama
      - postgres
      - redis

  # Presenter Service (CPU-optimized)
  presenter:
    build: ./services/presenter
    container_name: presenter-service
    ports:
      - "8013:8013"
    environment:
      - OLLAMA_BASE_URL=http://ollama-cpu:11434
      - OLLAMA_MODEL=qwen2:1.5b
      - USE_VIBEVOICE=false
      - TTS_BACKEND=vibevoice
    depends_on:
      - ollama-cpu
      - tts
      - postgres
      - redis

volumes:
  ollama_data:
  ollama_cpu_data:
  episode_storage:
  postgres_data:
  redis_data:
```

### **Phase 3: Model Deployment**

#### **3.1 Ollama Models**
```bash
# Start Ollama services
docker compose -f docker-compose.evo-x2.yml up -d ollama ollama-cpu

# Wait for services to start
sleep 30

# Pull required models
docker compose exec ollama ollama pull qwen3:latest
docker compose exec ollama ollama pull qwen2:1.5b
docker compose exec ollama-cpu ollama pull qwen2:0.5b
```

#### **3.2 VibeVoice Model**
```bash
# Start TTS service
docker compose -f docker-compose.evo-x2.yml up -d tts

# Monitor model loading
docker compose logs -f tts

# Verify VibeVoice is loaded
curl http://localhost:8015/health
```

#### **3.3 Voice Samples Preparation**
```bash
# Create voice samples directory
mkdir -p voice_samples

# Add custom voice samples (10-30 seconds each)
# Format: WAV, 16kHz, mono
cp presenter1.wav voice_samples/
cp presenter2.wav voice_samples/
cp guest_voice.wav voice_samples/
```

### **Phase 4: System Testing**

#### **4.1 Service Health Checks**
```bash
# Check all services
docker compose -f docker-compose.evo-x2.yml ps

# Test service endpoints
curl http://localhost:8000/health  # AI Overseer
curl http://localhost:8001/health  # API Gateway
curl http://localhost:8002/health  # Collections
curl http://localhost:8003/health  # Writer
curl http://localhost:8013/health  # Presenter
curl http://localhost:8015/health  # TTS
```

#### **4.2 VibeVoice Testing**
```bash
# Test VibeVoice generation
curl -X POST http://localhost:8015/generate-audio \
  -H "Content-Type: application/json" \
  -d '{
    "script": "Speaker 1: Hello, welcome to our podcast. Speaker 2: Thank you for having me.",
    "voice_settings": {
      "speaker_1": "presenter1",
      "speaker_2": "presenter2"
    }
  }'
```

#### **4.3 Full Workflow Testing**
```bash
# Generate test podcast
python generate_test_podcast.py

# Verify audio quality
# Check generation time
# Validate multi-speaker output
```

---

## 🔧 **Configuration Optimization**

### **Performance Tuning**

#### **Docker Resource Limits**
```yaml
# Add to each service in docker-compose.evo-x2.yml
deploy:
  resources:
    limits:
      cpus: '4.0'
      memory: 8G
    reservations:
      cpus: '2.0'
      memory: 4G
```

#### **Ollama Optimization**
```bash
# Environment variables for optimal performance
OLLAMA_KEEP_ALIVE=0
OLLAMA_NUM_THREADS=16
OLLAMA_GPU_LAYERS=32
OLLAMA_HOST=0.0.0.0
```

#### **VibeVoice Optimization**
```python
# services/tts/main.py
VIBEVOICE_CONFIG = {
    "torch_dtype": "float16",
    "device_map": "auto",
    "low_cpu_mem_usage": True,
    "use_cache": True,
    "max_memory": "90GB"  # Leave 6GB for system
}
```

### **Monitoring Setup**

#### **Prometheus Configuration**
```yaml
# monitoring/prometheus/prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'podcast-generator'
    static_configs:
      - targets: ['ai-overseer:8000', 'writer:8003', 'presenter:8013', 'tts:8015']
```

#### **Grafana Dashboards**
```bash
# Import dashboards
docker compose exec grafana grafana-cli admin reset-admin-password admin
# Access at http://localhost:3000
# Import dashboard JSON files
```

---

## 🚨 **Troubleshooting**

### **Common Issues**

#### **VRAM Allocation Problems**
```bash
# Check VRAM usage
nvidia-smi

# If VRAM not allocated correctly:
sudo nvidia-smi -pm 1
sudo nvidia-smi -lgc 2100,2100
```

#### **VibeVoice Loading Issues**
```bash
# Check TTS service logs
docker compose logs tts

# Common fixes:
# 1. Increase timeout in docker-compose
# 2. Check model download
# 3. Verify voice samples format
```

#### **Performance Issues**
```bash
# Monitor resource usage
docker stats

# Optimize based on usage:
# 1. Adjust CPU limits
# 2. Tune memory allocation
# 3. Optimize model parameters
```

### **Rollback Procedures**

#### **Quick Rollback to Coqui**
```bash
# Change environment variables
docker compose exec tts sh -c 'echo "USE_VIBEVOICE=false" >> .env'
docker compose exec presenter sh -c 'echo "TTS_BACKEND=coqui" >> .env'

# Restart services
docker compose restart tts presenter

# Verify rollback
curl http://localhost:8015/health
```

#### **Full System Rollback**
```bash
# Stop all services
docker compose -f docker-compose.evo-x2.yml down

# Start with original configuration
docker compose up -d

# Verify system health
python test_system_health.py
```

---

## 📊 **Performance Monitoring**

### **Key Metrics**

#### **System Metrics**
- **CPU Usage:** Target <80%
- **RAM Usage:** Target <90%
- **VRAM Usage:** Target <90%
- **Disk I/O:** Monitor for bottlenecks

#### **Service Metrics**
- **Response Times:** <5 seconds
- **Generation Times:** <2 minutes for 20-minute podcast
- **Error Rates:** <1%
- **Uptime:** >99.9%

#### **Quality Metrics**
- **Audio Quality:** Subjective assessment
- **Voice Clarity:** Technical analysis
- **Content Quality:** Human review
- **User Satisfaction:** Feedback collection

### **Monitoring Tools**

#### **Built-in Monitoring**
- **Prometheus** - Metrics collection
- **Grafana** - Visualization
- **Docker Stats** - Container monitoring
- **NVIDIA-SMI** - GPU monitoring

#### **Custom Monitoring**
- **Health Check Scripts** - Automated testing
- **Performance Benchmarks** - Regular testing
- **Quality Assessment** - Audio analysis
- **User Feedback** - Satisfaction tracking

---

## 🎯 **Success Criteria**

### **Deployment Complete When:**
- [ ] All services running and healthy
- [ ] VibeVoice generating audio successfully
- [ ] 15-30 minute podcasts completing in <2 minutes
- [ ] Voice cloning working with custom samples
- [ ] System stable for 24+ hours
- [ ] Performance metrics meeting targets

### **Performance Targets:**
- **Generation Speed:** <2 minutes for 20-minute podcast
- **Audio Quality:** 9/10 (vs current 7/10)
- **System Uptime:** 99.9%
- **Resource Usage:** <90% of available capacity

### **Quality Targets:**
- **Voice Clarity:** Professional broadcast quality
- **Content Depth:** In-depth analysis, not soundbites
- **Multi-speaker:** Distinct, natural-sounding voices
- **Emotional Range:** Appropriate tone and emphasis

---

## 📚 **Resources**

### **Hardware Documentation**
- [AMD Ryzen AI Max+ 395 Specs](https://www.amd.com/en/products/processors/laptop/ryzen/ai-300-series/amd-ryzen-ai-max-plus-395.html)
- [GMKtec EVO-X2 Product Page](https://www.gmktec.com/products/amd-ryzen%E2%84%A2-ai-max-395-evo-x2-ai-mini-pc)

### **Software Documentation**
- [VibeVoice GitHub](https://github.com/VibeVoice/VibeVoice)
- [Ollama Documentation](https://ollama.ai/docs)
- [Docker Compose Reference](https://docs.docker.com/compose/)

### **Troubleshooting Resources**
- [NVIDIA Docker Guide](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html)
- [Ubuntu 22.04 LTS Guide](https://ubuntu.com/server/docs)
- [Performance Tuning Guide](./PERFORMANCE_TUNING_GUIDE.md)

---

**Last Updated:** October 3, 2025  
**Deployment Version:** 1.0  
**Target Hardware:** AMD Ryzen AI Max+ 395 (96GB VRAM)  
**Status:** Ready for Deployment
