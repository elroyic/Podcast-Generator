# Prometheus Setup Fix Summary

## Issues Found

The Prometheus setup had multiple issues preventing proper metrics collection:

### 1. **API Gateway (HTTP 404)**
- **Problem**: Prometheus was trying to scrape `/metrics` but the endpoint didn't exist
- **Fix**: Added `/metrics` endpoint that exposes Prometheus-formatted metrics including:
  - Episode counts by status
  - Total podcast groups, presenters, writers, feeds, articles, collections

### 2. **Collections, Editor, Heavy-Reviewer, Light-Reviewer (Unsupported Content-Type)**
- **Problem**: Prometheus was scraping `/health` endpoints that returned JSON instead of Prometheus text format
- **Fix**: Added `/metrics/prometheus` endpoints to all services with proper Prometheus text format

### 3. **Missing Metrics Endpoints**
- **Services affected**: news-feed, text-generation, writer
- **Fix**: Added `/metrics/prometheus` endpoints to these services

## Changes Made

### Services Updated (Added `/metrics/prometheus` endpoints):
1. ✅ `services/api-gateway/main.py` - Added `/metrics` endpoint
2. ✅ `services/collections/main.py` - Added `/metrics/prometheus` endpoint
3. ✅ `services/editor/main.py` - Added `/metrics/prometheus` endpoint
4. ✅ `services/heavy-reviewer/main.py` - Added `/metrics/prometheus` endpoint
5. ✅ `services/light-reviewer/main.py` - Added `/metrics/prometheus` endpoint
6. ✅ `services/news-feed/main.py` - Added `/metrics/prometheus` endpoint
7. ✅ `services/text-generation/main.py` - Added `/metrics/prometheus` endpoint
8. ✅ `services/writer/main.py` - Added `/metrics/prometheus` endpoint

### Services Already Had Metrics:
- `services/ai-overseer/main.py` - Already had `/metrics/prometheus`
- `services/presenter/main.py` - Already had `/metrics/prometheus`
- `services/reviewer/main.py` - Already had `/metrics/prometheus`
- `services/publishing/main.py` - Already had `/metrics/prometheus`

### Configuration Updated:
- ✅ `monitoring/prometheus/prometheus.yml` - Updated all `metrics_path` values to use `/metrics/prometheus` (or `/metrics` for api-gateway)

## Metrics Exposed by Each Service

### API Gateway (`/metrics`)
- `api_gateway_episodes_total{status="..."}` - Episodes by status
- `api_gateway_podcast_groups_total` - Total podcast groups
- `api_gateway_presenters_total` - Total presenters
- `api_gateway_writers_total` - Total writers
- `api_gateway_active_feeds_total` - Active news feeds
- `api_gateway_articles_total` - Total articles
- `api_gateway_collections_total` - Total collections

### Collections Service (`/metrics/prometheus`)
- `collections_total{status="..."}` - Collections by status
- `collections_active_total` - Active collections in memory

### Editor Service (`/metrics/prometheus`)
- `editor_latency_seconds` - Average latency for script editing
- `editor_edits_total` - Total script edits processed

### Heavy Reviewer (`/metrics/prometheus`)
- `heavy_reviewer_latency_seconds` - Average review latency
- `heavy_reviewer_reviews_total` - Total reviews processed

### Light Reviewer (`/metrics/prometheus`)
- `light_reviewer_latency_seconds` - Average review latency
- `light_reviewer_reviews_total` - Total reviews processed

### News Feed Service (`/metrics/prometheus`)
- `news_feed_total` - Total news feeds
- `news_feed_active` - Active news feeds
- `news_feed_articles_total` - Total articles
- `news_feed_articles_by_reviewer{type="..."}` - Articles by reviewer type (light/heavy/unreviewed)

### Text Generation Service (`/metrics/prometheus`)
- `text_generation_service_up` - Service health status

### Writer Service (`/metrics/prometheus`)
- `writer_episodes_total` - Total episodes written
- `writer_service_up` - Service health status

## How to Apply Changes

### Option 1: Restart All Services (Recommended)
```bash
docker-compose down
docker-compose up -d --build
```

### Option 2: Restart Individual Services
```bash
# Restart services with new metrics endpoints
docker-compose restart api-gateway
docker-compose restart collections
docker-compose restart editor
docker-compose restart heavy-reviewer
docker-compose restart light-reviewer
docker-compose restart news-feed
docker-compose restart text-generation
docker-compose restart writer

# Restart Prometheus to reload config
docker-compose restart prometheus
```

### Option 3: Reload Prometheus Config Only (if services were already running)
```bash
# Restart Prometheus to pick up config changes
docker-compose restart prometheus

# Then restart the services that were updated
docker-compose restart api-gateway collections editor heavy-reviewer light-reviewer news-feed text-generation writer
```

## Verification

After restarting, verify the fix by:

1. **Check Prometheus Targets**: Navigate to `http://localhost:9090/targets`
   - All targets should show status "UP" (green)
   - No more 404 or Content-Type errors

2. **Test Metrics Endpoints Directly**:
   ```bash
   # API Gateway
   curl http://localhost:8000/metrics
   
   # Collections
   curl http://localhost:8014/metrics/prometheus
   
   # Editor
   curl http://localhost:8009/metrics/prometheus
   
   # Heavy Reviewer
   curl http://localhost:8011/metrics/prometheus
   
   # Light Reviewer
   curl http://localhost:8007/metrics/prometheus
   ```

3. **View Metrics in Grafana**: `http://localhost:3000`
   - Dashboards should now populate with data

## Notes

- All metrics endpoints return Prometheus text format (not JSON)
- Metrics are scraped every 15 seconds (configurable in `prometheus.yml`)
- Services that already had metrics endpoints were not modified
- The `/health` endpoints remain unchanged and still return JSON for internal health checks

