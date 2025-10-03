# Comprehensive Testing Guide

## Overview

This guide provides comprehensive testing procedures for the Podcast AI system. The testing suite includes component health checks, reviewer pipeline tests, collections service tests, full workflow tests, and performance/load tests.

## 🧪 Test Suite Components

### 1. System Validation (`validate_system.py`)
**Purpose**: Verify all services are running and accessible
**Scope**: All system components and dependencies

**What it tests**:
- Port availability for all services
- HTTP health endpoints
- Docker service status
- Service connectivity

**Usage**:
```bash
python Tests/Current/validate_system.py
```

### 2. Component Health Tests (`test_component_health.py`)
**Purpose**: Test individual service health and basic functionality
**Scope**: All microservices

**What it tests**:
- Service health endpoints
- API Gateway endpoints
- Database connectivity
- Redis connectivity
- Basic service responses

**Usage**:
```bash
python Tests/Current/test_component_health.py
```

### 3. Reviewer Pipeline Tests (`test_reviewer_pipeline.py`)
**Purpose**: Test the two-tier review architecture
**Scope**: Light Reviewer, Heavy Reviewer, Reviewer Orchestrator

**What it tests**:
- Light reviewer performance (~250ms target)
- Heavy reviewer performance (~1200ms target)
- Confidence-based routing
- Reviewer configuration
- Metrics collection
- Performance benchmarks

**Usage**:
```bash
python Tests/Current/test_reviewer_pipeline.py
```

### 4. Collections Service Tests (`test_collections_service.py`)
**Purpose**: Test feed grouping and collection management
**Scope**: Collections service functionality

**What it tests**:
- Collection creation and management
- Feed addition to collections
- Collection lifecycle (building → ready → used)
- Collection statistics
- Cleanup functionality

**Usage**:
```bash
python Tests/Current/test_collections_service.py
```

### 5. Full Workflow Tests (`test_full_workflow.py`)
**Purpose**: Test complete end-to-end podcast generation workflow
**Scope**: Entire system workflow

**What it tests**:
- News feed processing
- Collection creation and management
- Episode generation
- Audio file creation
- Dashboard functionality
- Complete workflow from RSS to published podcast

**Usage**:
```bash
python Tests/Current/test_full_workflow.py
```

### 6. Performance and Load Tests (`test_performance_load.py`)
**Purpose**: Test system performance under various loads
**Scope**: Performance benchmarks and load testing

**What it tests**:
- Reviewer performance under load
- API Gateway load handling
- Collections service performance
- Memory usage patterns
- Concurrent workflow execution
- Performance benchmarks

**Usage**:
```bash
python Tests/Current/test_performance_load.py
```

## 🚀 Running Tests

### Quick Start
```bash
# Run all tests with automatic service management
python run_comprehensive_tests.py

# Run only system validation
python run_comprehensive_tests.py --validation-only

# Run only component tests
python run_comprehensive_tests.py --component-only

# Run only workflow tests
python run_comprehensive_tests.py --workflow-only

# Run only performance tests
python run_comprehensive_tests.py --performance-only
```

### Manual Test Execution
```bash
# 1. Start services
docker-compose up -d

# 2. Wait for services to be ready (30 seconds)
sleep 30

# 3. Run system validation
python Tests/Current/validate_system.py

# 4. Run individual tests
python Tests/Current/test_component_health.py
python Tests/Current/test_reviewer_pipeline.py
python Tests/Current/test_collections_service.py
python Tests/Current/test_full_workflow.py
python Tests/Current/test_performance_load.py

# 5. Run comprehensive test suite
python Tests/Current/run_all_tests.py

# 6. Stop services
docker-compose down
```

### Test with RSS Feed Setup
```bash
# Set up RSS feeds before testing
python run_comprehensive_tests.py --setup-feeds
```

## 📊 Test Results and Reporting

### Automatic Reports
All tests generate comprehensive reports including:
- **Summary Reports**: High-level test results and statistics
- **Detailed Reports**: Full test output and error details
- **JSON Results**: Machine-readable test results
- **Performance Metrics**: Response times, success rates, and benchmarks

### Report Files
Reports are saved with timestamps:
- `test_summary_YYYYMMDD_HHMMSS.txt`
- `test_detailed_YYYYMMDD_HHMMSS.txt`
- `test_results_YYYYMMDD_HHMMSS.json`

### Performance Benchmarks
- **Light Reviewer**: <500ms average response time
- **Heavy Reviewer**: <2000ms average response time
- **API Gateway**: >95% success rate under load
- **Collections Service**: <100ms average response time

## 🔧 Test Configuration

### Environment Variables
```bash
# Service URLs (defaults to localhost)
export API_GATEWAY_URL="http://localhost:8000"
export LIGHT_REVIEWER_URL="http://localhost:8007"
export HEAVY_REVIEWER_URL="http://localhost:8008"
export REVIEWER_URL="http://localhost:8009"
export COLLECTIONS_URL="http://localhost:8011"

# Test Configuration
export TEST_TIMEOUT=600  # 10 minutes per test
export PERFORMANCE_REQUESTS=15  # Number of concurrent requests
```

### Docker Compose Requirements
Ensure all services are defined in `docker-compose.yml`:
- postgres (port 5432)
- redis (port 6379)
- api-gateway (port 8000)
- news-feed (port 8001)
- text-generation (port 8002)
- writer (port 8003)
- presenter (port 8004)
- publishing (port 8005)
- ai-overseer (port 8006)
- light-reviewer (port 8007)
- heavy-reviewer (port 8008)
- reviewer (port 8009)
- collections (port 8011)
- podcast-host (port 8012)
- vllm (port 8000)
- ollama (port 11434)
- nginx (port 8095)

## 🐛 Troubleshooting

### Common Issues

**Services not starting**:
```bash
# Check Docker status
docker-compose ps

# Check logs
docker-compose logs [service-name]

# Restart specific service
docker-compose restart [service-name]
```

**Test timeouts**:
```bash
# Increase timeout in test files
# Check service health manually
curl http://localhost:8000/health
```

**Database connection issues**:
```bash
# Check PostgreSQL
docker-compose exec postgres psql -U podcast_user -d podcast_ai -c "SELECT 1;"

# Check Redis
docker-compose exec redis redis-cli ping
```

**Reviewer service issues**:
```bash
# Check reviewer health
curl http://localhost:8009/health

# Check configuration
curl http://localhost:8009/config

# Check metrics
curl http://localhost:8009/metrics
```

### Test-Specific Issues

**Component Health Tests**:
- Ensure all services are running
- Check port availability
- Verify health endpoints

**Reviewer Pipeline Tests**:
- Check vLLM service availability
- Verify model loading
- Check Redis connectivity

**Collections Service Tests**:
- Ensure database connectivity
- Check reviewer service integration
- Verify collection lifecycle

**Full Workflow Tests**:
- Ensure all services are healthy
- Check RSS feed availability
- Verify audio generation

**Performance Tests**:
- Monitor system resources
- Check for memory leaks
- Verify concurrent request handling

## 📈 Performance Monitoring

### Key Metrics
- **Response Times**: Track service response times
- **Success Rates**: Monitor service availability
- **Throughput**: Measure requests per second
- **Resource Usage**: Monitor CPU and memory usage
- **Error Rates**: Track failure rates

### Monitoring Commands
```bash
# Check service health
curl http://localhost:8000/health

# Check reviewer metrics
curl http://localhost:8009/metrics

# Check collections stats
curl http://localhost:8011/collections/stats

# Monitor Docker resources
docker stats
```

## 🎯 Test Success Criteria

### System Validation
- ✅ All services healthy and accessible
- ✅ All ports available
- ✅ All health endpoints responding

### Component Tests
- ✅ All services responding within expected timeframes
- ✅ Database and Redis connectivity working
- ✅ API endpoints functional

### Reviewer Pipeline
- ✅ Light reviewer <500ms average response time
- ✅ Heavy reviewer <2000ms average response time
- ✅ Confidence-based routing working
- ✅ Metrics collection functional

### Collections Service
- ✅ Collection creation and management working
- ✅ Feed addition and lifecycle functional
- ✅ Statistics and cleanup working

### Full Workflow
- ✅ Complete RSS to podcast workflow functional
- ✅ Audio generation working
- ✅ Dashboard accessible
- ✅ All components integrated

### Performance Tests
- ✅ System handles expected load
- ✅ Performance benchmarks met
- ✅ No memory leaks or resource issues
- ✅ Concurrent operations working

## 📚 Additional Resources

- **System Architecture**: See `README_COMPLETE_SYSTEM.md`
- **API Documentation**: Available at `/docs` on each service
- **Docker Compose**: See `docker-compose.yml`
- **Service Logs**: Use `docker-compose logs [service-name]`

## 🤝 Contributing

When adding new tests:
1. Follow the existing test structure
2. Add comprehensive error handling
3. Include performance benchmarks
4. Update this documentation
5. Ensure tests are deterministic and repeatable

---

**Test Suite Status**: ✅ **COMPREHENSIVE TESTING IMPLEMENTED**

All components have been thoroughly tested with automated test suites covering health checks, functionality, performance, and end-to-end workflows.
