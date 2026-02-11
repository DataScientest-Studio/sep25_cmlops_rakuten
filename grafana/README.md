# Grafana - MLOps Dashboards

Grafana configuration with pre-provisioned datasources and dashboards.

## Dashboard: Rakuten MLOps

Pre-configured dashboard showing:
- Total predictions
- Prediction rate (predictions/sec)
- Latency percentiles (P50, P95, P99)
- Average text length
- Model version
- Top 10 predicted classes
- Latency trends

## Access Grafana

```bash
# Start monitoring stack
make start-monitor

# Open Grafana UI
open http://localhost:3000

# Default credentials
Username: admin
Password: admin
```

## Dashboard Panels

### 1. Total Predictions
**Type:** Stat  
**Query:** `sum(rakuten_predictions_total)`  
Shows total number of predictions made.

### 2. Prediction Rate
**Type:** Time Series  
**Query:** `rate(rakuten_predictions_total[5m])`  
Shows predictions per second over time.

### 3. Latency P95
**Type:** Stat  
**Query:** `histogram_quantile(0.95, rate(rakuten_prediction_latency_seconds_bucket[5m]))`  
Shows 95th percentile latency (95% of predictions complete faster).

### 4. Average Text Length
**Type:** Stat  
**Query:** `avg(rakuten_text_len_chars)`  
Shows average combined text length (designation + description).

### 5. Model Version
**Type:** Stat  
**Query:** `rakuten_model_version`  
Shows current production model version number.

### 6. Top 10 Predicted Classes
**Type:** Time Series  
**Query:** `topk(10, sum by (prdtypecode) (rakuten_predictions_total))`  
Shows most frequently predicted product categories.

### 7. Latency Percentiles
**Type:** Time Series  
**Queries:**
- P50: `histogram_quantile(0.50, rate(rakuten_prediction_latency_seconds_bucket[5m]))`
- P95: `histogram_quantile(0.95, rate(rakuten_prediction_latency_seconds_bucket[5m]))`
- P99: `histogram_quantile(0.99, rate(rakuten_prediction_latency_seconds_bucket[5m]))`

Shows latency distribution over time.

## Provisioning

Dashboard is automatically loaded from:
```
grafana/provisioning/dashboards/rakuten_dashboard.json
```

Datasource (Prometheus) is automatically configured from:
```
grafana/provisioning/datasources/prometheus.yml
```

## Customization

### Modify Dashboard

1. Open dashboard in Grafana UI
2. Click "Dashboard settings" (gear icon)
3. Make changes
4. Click "Save dashboard"
5. Export JSON: Dashboard settings → JSON Model
6. Save to `grafana/provisioning/dashboards/rakuten_dashboard.json`

### Add New Panel

1. Click "Add panel" in dashboard
2. Configure query and visualization
3. Save
4. Export updated dashboard JSON

### Useful Queries to Add

**Error Rate:**
```promql
rate(rakuten_api_errors_total[5m])
```

**Predictions by Model Version:**
```promql
sum by (model_version) (rate(rakuten_predictions_total[5m]))
```

**Text Length Distribution:**
```promql
histogram_quantile(0.50, rate(rakuten_text_len_chars_bucket[5m]))
histogram_quantile(0.95, rate(rakuten_text_len_chars_bucket[5m]))
```

## Alerting

### Setup Alert Rules

1. Open panel
2. Click "Alert" tab
3. Create alert rule:
   - Name: "High Latency"
   - Condition: `histogram_quantile(0.95, rate(rakuten_prediction_latency_seconds_bucket[5m])) > 1`
   - Evaluate: every 1m for 5m
   - Actions: Send notification

### Contact Points

Configure notification channels:
1. Go to Alerting → Contact points
2. Add contact point (email, Slack, webhook, etc.)
3. Test contact point

## Troubleshooting

### Dashboard Not Showing Data

1. **Check Prometheus datasource:**
   - Go to Configuration → Data sources
   - Click "Prometheus"
   - Click "Test" button
   - Should show "Data source is working"

2. **Check Prometheus is scraping:**
   - Open Prometheus: http://localhost:9090
   - Go to Status → Targets
   - Verify `rakuten-api` is UP

3. **Check API has metrics:**
   ```bash
   curl http://localhost:8000/metrics
   ```

4. **Generate some predictions:**
   ```bash
   for i in {1..10}; do
     curl -X POST http://localhost:8000/predict \
       -H "Content-Type: application/json" \
       -d '{"designation": "Test", "description": "Product"}'
   done
   ```

5. **Wait 15-30 seconds for metrics to appear**

### "No data" Error

- Check time range (top right): Set to "Last 1 hour"
- Ensure API has received predictions
- Check Prometheus is scraping successfully

### Dashboard Won't Load

```bash
# Restart Grafana
docker restart rakuten_grafana

# Check logs
docker logs rakuten_grafana
```

## Advanced Configuration

### Enable Anonymous Access

Already configured in `docker-compose.monitor.yml`:
```yaml
GF_AUTH_ANONYMOUS_ENABLED: true
GF_AUTH_ANONYMOUS_ORG_ROLE: Viewer
```

Allows embedding dashboards in Streamlit without authentication.

### Change Admin Password

Edit `.env`:
```
GRAFANA_ADMIN_PASSWORD=your_secure_password
```

Restart:
```bash
make restart-monitor
```

## Next Steps

- Setup alert rules for high latency / errors
- Create additional dashboards for training metrics
- Export dashboards for sharing
- Integrate with Streamlit UI
