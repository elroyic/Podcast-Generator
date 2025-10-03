# Worker Metrics Implementation Guide

## Quick Start

### 1. View All Worker Metrics
```bash
# News Feed
curl http://localhost:8001/metrics/prometheus | grep workers_active

# Reviewer (all three)
curl http://localhost:8013/metrics/prometheus | grep workers_active
curl http://localhost:8007/metrics/prometheus | grep workers_active
curl http://localhost:8011/metrics/prometheus | grep workers_active

# AI Services
curl http://localhost:8000/metrics/prometheus | grep workers_active  # AI Overseer
curl http://localhost:8004/metrics/prometheus | grep workers_active  # Presenter
curl http://localhost:8003/metrics/prometheus | grep workers_active  # Writer
curl http://localhost:8009/metrics/prometheus | grep workers_active  # Editor

# Support Services
curl http://localhost:8014/metrics/prometheus | grep workers_active  # Collections
curl http://localhost:8005/metrics/prometheus | grep workers_active  # Publishing
```

### 2. Verify All Metrics
```bash
# Run the verification script
python verify_metrics.py
```

### 3. View in Prometheus
```bash
# Open Prometheus UI
http://localhost:9090

# Example queries:
sum(rate(news_feed_articles_per_hour[5m]))
sum(reviewer_workers_active + presenter_workers_active + writer_workers_active + editor_workers_active)
```

---

## System Flow Diagram Metrics Mapping

### Component: News Feed (Articles/hr)
- **Metric:** `news_feed_articles_per_hour`
- **Workers:** `news_feed_workers_active`
- **Query:** `news_feed_articles_per_hour`

### Component: Reviewer (Workers Active) (Reviews/hr)
- **Workers:** `reviewer_workers_active`
- **Reviews/Hr:** `reviewer_light_total + reviewer_heavy_total`
- **Query:** `sum(reviewer_light_total + reviewer_heavy_total)`

### Component: AI Overseer (Workers Active) (Reviews/hr)
- **Workers:** `overseer_workers_active`
- **Reviews/Hr:** `overseer_episodes_generated_last_24h`
- **Query:** `overseer_workers_active`

### Component: Presenter Reviews Collection (Reviews/Hr)
- **Reviews/Hr:** `presenter_reviews_per_hour`
- **Workers:** `presenter_workers_active`
- **Query:** `presenter_reviews_per_hour`

### Component: Writer produces script (Scripts/Hr)
- **Scripts/Hr:** `writer_scripts_per_hour`
- **Workers:** `writer_workers_active`
- **Query:** `writer_scripts_per_hour`

### Component: Editor (Scripts/Day)
- **Scripts/Day:** `editor_scripts_per_hour`
- **Workers:** `editor_workers_active`
- **Query:** `editor_scripts_per_hour * 24`

---

## Scaling Workers

### Method 1: Environment Variable (Recommended)
Edit `docker-compose.yml`:

```yaml
presenter:
  environment:
    - WORKERS_ACTIVE=5  # Scale to 5 workers
  cpus: "5.0"           # Allocate 5 CPUs
```

Then restart:
```bash
docker-compose up -d presenter
```

### Method 2: Runtime Scaling (Future)
Create an admin API endpoint to dynamically scale workers:

```python
@app.post("/admin/scale/{service}")
async def scale_service(service: str, workers: int):
    # Update environment variable
    # Restart service container
    pass
```

---

## Monitoring Best Practices

### 1. Alert on Low Workers
```yaml
# Prometheus alert rule
- alert: LowWorkerCount
  expr: sum(reviewer_workers_active + presenter_workers_active + writer_workers_active) < 3
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "Low worker count detected"
```

### 2. Alert on Low Throughput
```yaml
- alert: LowArticleThroughput
  expr: news_feed_articles_per_hour < 10
  for: 1h
  labels:
    severity: warning
  annotations:
    summary: "Article ingestion rate is low"
```

### 3. Alert on High Queue Length
```yaml
- alert: HighReviewQueue
  expr: reviewer_queue_length > 100
  for: 10m
  labels:
    severity: critical
  annotations:
    summary: "Review queue is backing up"
```

---

## Grafana Dashboard Setup

### Import Dashboard
1. Open Grafana: `http://localhost:3000`
2. Go to Dashboards → Import
3. Upload `monitoring/grafana/dashboards/system-flow-metrics.json`
4. Select Prometheus datasource
5. Click Import

### Key Panels
- **Total Workers Active** - Shows system-wide worker count
- **Articles Per Hour** - RSS feed ingestion rate
- **Reviews Per Hour** - Combined review throughput
- **Scripts Per Hour** - Writer output rate
- **Workers by Service** - Bar chart of worker distribution
- **Collection Status** - Pie chart of collection states
- **Service Latency** - Response time tracking
- **Episode Pipeline** - Draft → Voiced → Published flow

---

## Performance Benchmarks

Based on your system flow requirements:

| Stage | Target Rate | Current Metric | Status |
|-------|-------------|----------------|--------|
| Article Ingestion | 10-50/hr | `news_feed_articles_per_hour` | ✅ Tracked |
| Article Review | 30-100/hr | `reviewer_light_total + reviewer_heavy_total` | ✅ Tracked |
| Collection Building | 1-5/day | `collections_total{status="ready"}` | ✅ Tracked |
| Presenter Review | 1-10/hr | `presenter_reviews_per_hour` | ✅ Tracked |
| Script Generation | 1-5/hr | `writer_scripts_per_hour` | ✅ Tracked |
| Script Editing | 1-3/day | `editor_scripts_per_hour * 24` | ✅ Tracked |
| Audio Generation | 1-3/day | `presenter_audio_generated_total` | ✅ Tracked |
| Publishing | 0-1/day | `publishing_success_total` | ✅ Tracked |

---

## Troubleshooting

### Metrics Not Showing
1. Check service health:
   ```bash
   curl http://localhost:8001/health
   ```

2. Check Prometheus targets:
   - Open `http://localhost:9090/targets`
   - All targets should show "UP"

3. Check service logs:
   ```bash
   docker-compose logs news-feed | grep metrics
   ```

### Workers Showing 0
1. Verify environment variable:
   ```bash
   docker-compose exec news-feed env | grep WORKERS
   ```

2. Update docker-compose.yml if missing
3. Restart service:
   ```bash
   docker-compose restart news-feed
   ```

### Metrics Not Updating
1. Check scrape interval (15s default)
2. Verify service is processing requests
3. Check Prometheus storage:
   ```bash
   docker-compose logs prometheus
   ```

---

## Summary

✅ **All services now expose:**
- Worker count metrics
- Throughput metrics (Articles/Hr, Reviews/Hr, Scripts/Hr)
- Latency metrics
- Status/health metrics

✅ **Prometheus configured** to scrape all services every 15s

✅ **Grafana dashboard** ready for visualization

✅ **100% alignment** with System Flow diagram requirements

Your monitoring infrastructure is now production-ready!


