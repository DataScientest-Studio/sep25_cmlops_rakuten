# Monitoring - Prometheus Configuration

Prometheus configuration for scraping Rakuten API metrics.

## Configuration

`prometheus.yml` - Main Prometheus configuration file.

### Scrape Targets

1. **rakuten-api** (port 8000)
   - Scrapes `/metrics` endpoint from FastAPI service
   - Interval: 15s
   - Target: `api:8000` (Docker service name)

2. **prometheus** (port 9090)
   - Self-monitoring
   - Target: `localhost:9090`

## Usage

### Start Prometheus

```bash
# Using Docker Compose
make start-monitor

# Access Prometheus UI
open http://localhost:9090
```

### Verify Targets

1. Open Prometheus UI: http://localhost:9090
2. Go to Status → Targets
3. Verify `rakuten-api` target is UP

## Useful PromQL Queries

### Prediction Metrics

```promql
# Total predictions
sum(rakuten_predictions_total)

# Prediction rate (predictions/sec)
rate(rakuten_predictions_total[5m])

# Predictions by class
sum by (prdtypecode) (rakuten_predictions_total)

# Top 5 predicted classes
topk(5, sum by (prdtypecode) (rakuten_predictions_total))
```

### Latency Metrics

```promql
# P50 latency
histogram_quantile(0.50, rate(rakuten_prediction_latency_seconds_bucket[5m]))

# P95 latency
histogram_quantile(0.95, rate(rakuten_prediction_latency_seconds_bucket[5m]))

# P99 latency
histogram_quantile(0.99, rate(rakuten_prediction_latency_seconds_bucket[5m]))

# Average latency
avg(rate(rakuten_prediction_latency_seconds_sum[5m]) / rate(rakuten_prediction_latency_seconds_count[5m]))
```

### Text Length Metrics

```promql
# Average text length
avg(rakuten_text_len_chars)

# Text length percentiles
histogram_quantile(0.95, rate(rakuten_text_len_chars_bucket[5m]))
```

### Model Metrics

```promql
# Current model version
rakuten_model_version

# Model load timestamp (last reload)
rakuten_model_load_timestamp
```

### Error Metrics

```promql
# API errors rate
rate(rakuten_api_errors_total[5m])

# Errors by type
sum by (error_type) (rakuten_api_errors_total)
```

## Troubleshooting

### Target Down

If `rakuten-api` target shows as DOWN:

1. Check API is running:
   ```bash
   curl http://localhost:8000/health
   ```

2. Check API metrics endpoint:
   ```bash
   curl http://localhost:8000/metrics
   ```

3. Check Docker network:
   ```bash
   docker network inspect rakuten_monitor_network
   ```

### No Metrics Showing

1. Make predictions to generate metrics:
   ```bash
   curl -X POST http://localhost:8000/predict \
     -H "Content-Type: application/json" \
     -d '{"designation": "Test Product", "description": "Test"}'
   ```

2. Wait 15-30 seconds for Prometheus to scrape

3. Check Prometheus logs:
   ```bash
   docker logs rakuten_prometheus
   ```

## Configuration Customization

### Change Scrape Interval

Edit `prometheus.yml`:

```yaml
global:
  scrape_interval: 30s  # Change from 15s to 30s
```

### Add Alert Rules

Create `alerts/rules.yml`:

```yaml
groups:
  - name: rakuten_alerts
    rules:
      - alert: HighLatency
        expr: histogram_quantile(0.95, rate(rakuten_prediction_latency_seconds_bucket[5m])) > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High prediction latency"
```

Add to `prometheus.yml`:

```yaml
rule_files:
  - "alerts/*.yml"
```

## Next Steps

- View metrics in Grafana: http://localhost:3000
- Setup alerting (Alertmanager)
- Export metrics to external systems
