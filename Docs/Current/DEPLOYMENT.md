# Deployment Guide

## Overview

This guide covers deployment strategies for the Podcast AI Generation system, including zero-downtime deployments and production considerations.

## Deployment Methods

### 1. Standard Deployment
```bash
# Start all services
docker compose up -d

# Check health
docker compose ps
curl http://localhost:8000/health
```

### 2. Zero-Downtime Blue-Green Deployment
```bash
# Deploy to green environment
./deploy/deploy.sh green api-gateway

# Deploy all services to green
./deploy/deploy.sh green all

# Switch traffic (after validation)
./deploy/deploy.sh switch green
```

### 3. Rolling Deployment
```bash
# Scale up new instances
docker compose up -d --scale light-reviewer=3

# Health check new instances
for i in {1..3}; do
  curl http://localhost:800$i/health
done

# Scale down old instances
docker compose up -d --scale light-reviewer=2
```

## Pre-Deployment Checklist

### Security Verification
- [ ] All images scanned with Trivy
- [ ] No critical vulnerabilities present
- [ ] Images signed with Cosign
- [ ] Dependencies up to date

### Testing Verification
- [ ] All unit tests passing
- [ ] Integration tests passing
- [ ] Complete workflow test successful
- [ ] Performance benchmarks meet requirements

### Configuration Verification
- [ ] Environment variables configured
- [ ] Database migrations ready
- [ ] Redis configuration updated
- [ ] Network policies configured

### Backup Verification
- [ ] Database backup completed
- [ ] Configuration backup completed
- [ ] Audio files backup completed
- [ ] Recovery procedures tested

## Production Deployment Steps

### 1. Pre-Deployment
```bash
# Create backup
docker compose exec postgres pg_dump -U podcast_user podcast_ai > backup_$(date +%Y%m%d_%H%M%S).sql

# Pull latest images
docker compose pull

# Run security scans
./scripts/security-scan.sh
```

### 2. Deployment
```bash
# Deploy with health checks
docker compose up -d --remove-orphans

# Wait for services to be ready
./scripts/wait-for-services.sh

# Run smoke tests
./scripts/smoke-test.sh
```

### 3. Post-Deployment
```bash
# Verify all services
curl http://localhost:8000/health

# Test complete workflow
curl -X POST http://localhost:8000/api/test-complete-workflow

# Check metrics
curl http://localhost:8000/api/reviewer/metrics
```

## Rollback Procedures

### Immediate Rollback
```bash
# Rollback to previous version
docker compose down
docker compose up -d --force-recreate

# Restore from backup if needed
docker compose exec postgres psql -U podcast_user -d podcast_ai < backup_file.sql
```

### Blue-Green Rollback
```bash
# Switch traffic back to blue
./deploy/deploy.sh blue

# Cleanup failed green deployment
docker compose -f deploy/blue-green-deploy.yml down api-gateway-green
```

## Monitoring After Deployment

### Health Monitoring
```bash
# Check all service health
curl http://localhost:8000/health

# Check specific service health
curl http://localhost:8001/health  # news-feed
curl http://localhost:8007/health  # reviewer
curl http://localhost:8003/health  # writer
```

### Performance Monitoring
```bash
# Check Prometheus metrics
curl http://localhost:8007/metrics/prometheus  # reviewer
curl http://localhost:8006/metrics/prometheus  # overseer
curl http://localhost:8004/metrics/prometheus  # presenter
```

### Error Monitoring
```bash
# Check logs for errors
docker compose logs --tail=100 api-gateway
docker compose logs --tail=100 ai-overseer
docker compose logs --tail=100 reviewer
```

## Scaling Services

### Manual Scaling
```bash
# Scale reviewer services
docker compose up -d --scale light-reviewer=3
docker compose up -d --scale heavy-reviewer=2

# Scale presenter service
docker compose up -d --scale presenter=2
```

### Auto-scaling (via API)
```bash
# Scale light reviewers via API
curl -X POST http://localhost:8000/api/reviewer/scale/light \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -d '{"workers": 3}'

# Check scaling status
curl http://localhost:8000/api/reviewer/scale/status
```

## Environment Variables

### Required Environment Variables
```bash
# Database
DATABASE_URL=postgresql://podcast_user:podcast_pass@postgres:5432/podcast_ai

# Redis
REDIS_URL=redis://redis:6379/0

# Authentication
JWT_SECRET_KEY=your-super-secret-key-change-in-production
ADMIN_PASSWORD=secure-admin-password

# Models
OLLAMA_BASE_URL=http://ollama:11434
USE_VIBEVOICE=true

# Thresholds
REVIEWER_CONF_THRESHOLD=0.85
MIN_FEEDS_THRESHOLD=5
```

### Optional Environment Variables
```bash
# Performance tuning
REVIEWER_LIGHT_MODEL=qwen2:0.5b
REVIEWER_HEAVY_MODEL=qwen3:4b
PRESENTER_WORKERS=5

# Features
REVIEWER_HEAVY_ENABLED=true
USE_WRITER_FOR_SCRIPT=true

# Storage
AUDIO_STORAGE_PATH=/app/storage
LOCAL_SERVER_URL=http://nginx:8080
```

## Troubleshooting

### Common Issues

#### Services Not Starting
```bash
# Check logs
docker compose logs service-name

# Check resource usage
docker stats

# Check disk space
df -h
```

#### Database Connection Issues
```bash
# Check PostgreSQL status
docker compose exec postgres pg_isready

# Check database connections
docker compose exec postgres psql -U podcast_user -c "\conninfo"
```

#### Memory Issues
```bash
# Check memory usage
docker stats --no-stream

# Scale down resource-intensive services
docker compose up -d --scale heavy-reviewer=1
```

#### Network Issues
```bash
# Check service connectivity
docker compose exec api-gateway ping news-feed
docker compose exec api-gateway ping reviewer

# Check port conflicts
netstat -tulpn | grep 8000
```

## Performance Optimization

### Database Optimization
```sql
-- Add indexes for common queries
CREATE INDEX idx_articles_feed_id_date ON articles(feed_id, publish_date);
CREATE INDEX idx_episodes_group_id_status ON episodes(group_id, status);
CREATE INDEX idx_audio_files_episode_id ON audio_files(episode_id);
```

### Redis Optimization
```bash
# Configure Redis for better performance
redis-cli CONFIG SET maxmemory 1gb
redis-cli CONFIG SET maxmemory-policy allkeys-lru
```

### Service Optimization
```bash
# Optimize resource allocation
docker compose up -d --scale light-reviewer=3  # More light reviewers
docker compose up -d --scale heavy-reviewer=1  # Fewer heavy reviewers
```

## Security Best Practices

### 1. Regular Updates
- Update base images monthly
- Update dependencies weekly
- Monitor security advisories

### 2. Access Control
- Rotate JWT secrets regularly
- Use strong admin passwords
- Limit network exposure

### 3. Monitoring
- Monitor security metrics
- Set up security alerts
- Regular security audits

### 4. Backup Strategy
- Daily database backups
- Weekly configuration backups
- Monthly full system backups

## Contact Information

For deployment issues:
- **Technical Lead**: Lead Developer
- **DevOps**: DevOps Engineer  
- **Security**: Security Team
- **Emergency**: On-call rotation