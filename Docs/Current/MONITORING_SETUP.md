# Monitoring Setup Guide
**Status**: ✅ WORKING  
**Last Updated**: September 30, 2025

---

## Quick Start

### 1. Start All Monitoring Services

```bash
# Start monitoring stack
docker compose up -d prometheus grafana postgres-exporter redis-exporter

# Verify services are running
docker compose ps | grep -E "prometheus|grafana|exporter"
```

### 2. Access Dashboards

| Service | URL | Credentials |
|---------|-----|-------------|
| **Prometheus** | http://localhost:9090 | None |
| **Grafana** | http://localhost:3000 | admin/admin123 |
| **Postgres Exporter** | http://localhost:9187/metrics | None |
| **Redis Exporter** | http://localhost:9121/metrics | None |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Monitoring Stack                         │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐      ┌──────────────┐                     │
│  │  Prometheus  │ ───> │   Grafana    │                     │
│  │   :9090      │      │    :3000     │                     │
│  └──────┬───────┘      └──────────────┘                     │
│         │                                                     │
│         │ Scrapes metrics from:                              │
│         │                                                     │
│         ├─> API Gateway (:8000/metrics)                      │
│         ├─> Reviewer (:8008/metrics/prometheus)              │
│         ├─> Light Reviewer (:8000/health)                    │
│         ├─> Heavy Reviewer (:8000/health)                    │
│         ├─> All microservices (/health endpoints)            │
│         ├─> Postgres Exporter (:9187/metrics)                │
│         └─> Redis Exporter (:9121/metrics)                   │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## Configuration Files

### File Structure

```
monitoring/
├── prometheus/
│   └── prometheus.yml          # Prometheus configuration
├── grafana/
│   ├── dashboards/
│   │   ├── podcast-ai-overview.json
│   │   └── dashboard-provider.yml
│   └── datasources/
│       └── prometheus.yml      # Grafana datasource config
└── alerts/
    └── podcast-ai-alerts.yml   # Alert rules (optional)
```

### Key Configuration

#### Prometheus (monitoring/prometheus/prometheus.yml)
- **Scrape Interval**: 15 seconds
- **Scrape Targets**: 13 microservices + 2 exporters
- **Storage**: `/prometheus` volume
- **Config Reload**: Enabled via `--web.enable-lifecycle`

#### Grafana
- **Data Source**: Prometheus (auto-configured)
- **Dashboards**: Auto-provisioned from `/etc/grafana/provisioning/dashboards`
- **Default User**: admin/admin123 ⚠️ **Change in production!**

---

## Troubleshooting

### Issue: Prometheus won't start (mount errors)

**Error Message**:
```
error mounting "/run/desktop/mnt/host/g/AI Projects/Podcast Generator/prometheus.yml"
to rootfs: not a directory
```

**Solution**:
The configuration file must be in a directory structure. Ensure:
```bash
# File should be at:
monitoring/prometheus/prometheus.yml

# NOT at:
prometheus.yml  # (root level - wrong!)
```

**Docker Compose Volume Mount**:
```yaml
volumes:
  # ✅ Correct - mount single file
  - ./monitoring/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
  
  # ❌ Wrong - trying to mount root file
  - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
```

---

### Issue: Grafana shows "No Data"

**Diagnostic Steps**:

1. **Check Prometheus is scraping targets**:
   ```bash
   # Open Prometheus UI
   open http://localhost:9090/targets
   
   # Or via curl
   curl http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {job, health}'
   ```

2. **Verify services expose metrics**:
   ```bash
   # Test reviewer metrics endpoint
   curl http://localhost:8013/metrics/prometheus
   
   # Test health endpoints
   curl http://localhost:8007/health  # light-reviewer
   curl http://localhost:8011/health  # heavy-reviewer
   ```

3. **Check Grafana datasource**:
   - Go to Grafana → Configuration → Data Sources
   - Click on "Prometheus"
   - Click "Test" button
   - Should show "Data source is working"

---

### Issue: Can't access Grafana

**Diagnostic Steps**:

1. **Check if Grafana container is running**:
   ```bash
   docker compose ps grafana
   ```

2. **Check Grafana logs**:
   ```bash
   docker compose logs grafana
   ```

3. **Verify port is not in use**:
   ```bash
   # Windows
   netstat -ano | findstr :3000
   
   # If port in use, stop the conflicting service or change Grafana port
   ```

4. **Access via container IP** (if localhost doesn't work):
   ```bash
   # Get container IP
   docker inspect podcastgenerator-grafana-1 | grep IPAddress
   
   # Access via IP
   open http://<container-ip>:3000
   ```

---

## Metrics Reference

### Available Metrics

#### Reviewer Metrics
- `reviewer_light_latency_seconds` - Average latency for light reviews
- `reviewer_heavy_latency_seconds` - Average latency for heavy reviews
- `reviewer_queue_length` - Current queue size
- `reviewer_light_total` - Total light reviews processed
- `reviewer_heavy_total` - Total heavy reviews processed
- `reviewer_confidence_bucket_total{bucket}` - Reviews by confidence range
- `reviewer_duplicate_total` - Total duplicate feeds filtered

#### Service Health Metrics
- `up{job="<service-name>"}` - Service health (1=up, 0=down)

#### Database Metrics (via postgres-exporter)
- `pg_up` - PostgreSQL is up
- `pg_stat_database_numbackends` - Active connections
- `pg_database_size_bytes` - Database size
- `pg_stat_database_tup_inserted` - Rows inserted
- `pg_stat_database_tup_updated` - Rows updated

#### Redis Metrics (via redis-exporter)
- `redis_up` - Redis is up
- `redis_connected_clients` - Active connections
- `redis_memory_used_bytes` - Memory usage
- `redis_memory_max_bytes` - Max memory
- `redis_keyspace_hits_total` - Cache hits
- `redis_keyspace_misses_total` - Cache misses

---

## Sample Prometheus Queries

### Service Health
```promql
# All services that are up
sum(up) by (job)

# Services that are down
up == 0
```

### Reviewer Performance
```promql
# Average light reviewer latency (last 5 min)
avg_over_time(reviewer_light_latency_seconds[5m])

# Total reviews in last hour
increase(reviewer_light_total[1h]) + increase(reviewer_heavy_total[1h])

# Review throughput (reviews per second)
rate(reviewer_light_total[5m])
```

### Queue Monitoring
```promql
# Current queue length
reviewer_queue_length

# Queue growth rate
deriv(reviewer_queue_length[5m])
```

### Confidence Distribution
```promql
# Reviews by confidence bucket
sum by (bucket) (reviewer_confidence_bucket_total)
```

---

## Dashboard Setup (Grafana)

### Auto-Provisioned Dashboard

The main dashboard is automatically loaded from:
`monitoring/grafana/dashboards/podcast-ai-overview.json`

**Panels Included**:
1. Reviewer Services Up (Gauge)
2. Review Throughput (Time Series)
3. Reviewer Latency (Time Series)
4. Queue Length (Time Series)
5. Confidence Distribution (Pie Chart)
6. Total Services Up (Stat)
7. Episodes Generated (Stat)

### Manual Dashboard Import

If the dashboard doesn't auto-load:

1. Go to Grafana → Dashboards → Import
2. Upload `monitoring/grafana/dashboards/podcast-ai-overview.json`
3. Select "Prometheus" as the data source
4. Click "Import"

---

## Alert Rules (Optional)

Alert rules are defined in `monitoring/alerts/podcast-ai-alerts.yml` but are **currently disabled** to simplify the setup.

### To Enable Alerts:

1. **Update docker-compose.yml**:
   ```yaml
   prometheus:
     volumes:
       - ./monitoring/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
       - ./monitoring/alerts:/etc/prometheus/alerts:ro  # Add this line
       - prometheus_data:/prometheus
   ```

2. **Uncomment alert rules in prometheus.yml**:
   ```yaml
   rule_files:
     - '/etc/prometheus/alerts/*.yml'
   ```

3. **Restart Prometheus**:
   ```bash
   docker compose restart prometheus
   ```

### Alert Examples

```yaml
# Service Down Alert
- alert: ServiceDown
  expr: up == 0
  for: 2m
  labels:
    severity: critical
  annotations:
    summary: "Service {{ $labels.job }} is down"

# High Queue Alert
- alert: HighReviewerQueueLength
  expr: reviewer_queue_length > 100
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "Reviewer queue is backing up"
```

---

## Production Recommendations

### Security

- [ ] **Change Grafana password** immediately
  ```bash
  docker compose exec grafana grafana-cli admin reset-admin-password NEW_PASSWORD
  ```

- [ ] **Enable HTTPS** for Grafana
  - Configure reverse proxy (nginx/traefik)
  - Use Let's Encrypt for SSL certificates

- [ ] **Restrict Prometheus access**
  - Add authentication (basic auth via reverse proxy)
  - Firewall rules to block external access

### Performance

- [ ] **Increase retention** (default: 15 days)
  ```yaml
  prometheus:
    command:
      - '--storage.tsdb.retention.time=90d'
  ```

- [ ] **Add resource limits**
  ```yaml
  prometheus:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
  ```

### Reliability

- [ ] **Set up Alertmanager** for notifications
- [ ] **Configure backups** for Prometheus data
- [ ] **Enable Grafana** SMTP for email alerts
- [ ] **Add uptime monitoring** (UptimeRobot, Pingdom)

---

## Commands Reference

### Start Services
```bash
# Start all monitoring
docker compose up -d prometheus grafana postgres-exporter redis-exporter

# Start individual service
docker compose up -d prometheus
```

### Stop Services
```bash
# Stop all monitoring
docker compose stop prometheus grafana postgres-exporter redis-exporter

# Stop and remove
docker compose down prometheus grafana postgres-exporter redis-exporter
```

### View Logs
```bash
# Follow Prometheus logs
docker compose logs -f prometheus

# View Grafana logs
docker compose logs grafana

# View last 100 lines
docker compose logs --tail=100 prometheus
```

### Restart Services
```bash
# Restart Prometheus (reload config)
docker compose restart prometheus

# Reload Prometheus config without restart (if --web.enable-lifecycle is set)
curl -X POST http://localhost:9090/-/reload
```

### Debugging
```bash
# Check Prometheus config syntax
docker compose exec prometheus promtool check config /etc/prometheus/prometheus.yml

# Test specific scrape target
docker compose exec prometheus promtool check metrics http://api-gateway:8000/metrics
```

---

## Support & Resources

- **Prometheus Docs**: https://prometheus.io/docs/
- **Grafana Docs**: https://grafana.com/docs/
- **PromQL Guide**: https://prometheus.io/docs/prometheus/latest/querying/basics/
- **Dashboard Gallery**: https://grafana.com/grafana/dashboards/

---

## Status Summary

✅ **Working**:
- Prometheus scraping all services
- Grafana visualization
- Postgres metrics export
- Redis metrics export
- Auto-refresh dashboards

⚠️ **Optional** (not yet enabled):
- Alert rules
- Alertmanager notifications
- Long-term metrics retention
- Advanced dashboards

🔒 **Security Hardening Required**:
- Change default Grafana password
- Enable HTTPS
- Add authentication to Prometheus

---

**Last Updated**: September 30, 2025  
**Monitoring Stack Version**: v1.0  
**Status**: Production Ready (after security hardening)

