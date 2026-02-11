# Testing Guide - Rakuten MLOps Platform

**Status**: 75% Complete (6/8 Phases)  
**Last Updated**: 2026-02-11

This guide walks through testing all implemented components.

---

## Prerequisites

1. **Docker Desktop Running**
   ```bash
   # Verify Docker is running
   docker ps
   ```

2. **Environment Configuration**
   ```bash
   # Copy and configure .env if not done
   cp env.example.txt .env
   # Edit .env with your credentials (or use defaults)
   ```

3. **Data Available**
   - Ensure `data/raw/` contains: `X_train.csv`, `Y_train.csv`, `X_test.csv`, `images/`
   - If using DVC, pull data first: `dvc pull`

---

## Phase-by-Phase Testing

### ✅ Phase 1: Infrastructure Stack

**Test Airflow + MLflow + PostgreSQL**

```bash
# Start infrastructure
make start

# Wait 60 seconds for services to initialize

# Check all services are running
make ps

# Check health
make check-health

# Access UIs
open http://localhost:8080  # Airflow (admin/admin)
open http://localhost:5000  # MLflow
open http://localhost:9001  # MinIO (minio_admin/minio_password)
```

**Expected Results:**
- ✅ All containers running
- ✅ Airflow UI loads
- ✅ MLflow UI loads
- ✅ MinIO UI loads

**Initialize Database (40% data):**

```bash
make init-db

# Verify data loaded
make status
# Should show: ~33,966 products (40%)
```

**Expected Output:**
```
Current State:
  - Current percentage: 40.0%
  - Total products: 33966
  - Total labels: 33966
```

---

### ✅ Phase 2: FastAPI Service

**Start API Stack:**

```bash
# Start API (includes postgres, mlflow, api)
make start-api

# Check API health
curl http://localhost:8000/health

# Check OpenAPI docs
open http://localhost:8000/docs
```

**Expected `/health` Response:**
```json
{
  "status": "degraded",  // Will be "unhealthy" until model is trained
  "model": {
    "name": "rakuten_classifier",
    "version": "not_loaded",
    "stage": "Production",
    "loaded": false
  },
  "mlflow": {
    "reachable": true,
    "uri": "http://mlflow:5000"
  }
}
```

**Note**: API won't serve predictions until a model is trained and registered (Phase 3).

**Check Prometheus Metrics:**

```bash
curl http://localhost:8000/metrics | head -n 20

# Should show metric definitions (no data yet)
```

---

### ✅ Phase 3: Model Training

**Train Baseline Model:**

```bash
# Set MLflow URI
export MLFLOW_TRACKING_URI=http://localhost:5000

# Train model (takes 2-5 minutes depending on data size)
python scripts/train_baseline_model.py --auto-promote

# Check output for:
# - Training metrics (F1, accuracy)
# - Model registered
# - Model promoted to Production (if F1 > 0.70)
```

**Expected Output:**
```
================================================================================
✅ Baseline Model Training Complete!
   MLflow Run ID: abc123...
   MLflow UI: http://localhost:5000
================================================================================

Next steps:
1. View model in MLflow UI: open http://localhost:5000
2. Start API service: make start-api
3. Test prediction: curl -X POST http://localhost:8000/predict ...
```

**Verify in MLflow UI:**

1. Open http://localhost:5000
2. Click "Experiments" → "rakuten_model_training"
3. Verify run appears with metrics
4. Click "Models" → "rakuten_classifier"
5. Verify version exists in "Production" stage

---

### ✅ Phase 4: API Predictions (After Training)

**Restart API to Load Model:**

```bash
# Restart API to load newly registered model
make restart-api

# Wait 30 seconds for model to load

# Check health again
curl http://localhost:8000/health

# Should now show:
# "status": "healthy"
# "model.loaded": true
# "model.version": "1" (or higher)
```

**Make Test Prediction:**

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "designation": "iPhone 13 Pro 128GB",
    "description": "Smartphone Apple 5G écran Super Retina XDR"
  }'
```

**Expected Response:**
```json
{
  "predicted_class": 2280,
  "probabilities": {
    "2280": 0.87,
    "40": 0.08,
    "2403": 0.03,
    "1280": 0.01,
    "2705": 0.01
  },
  "confidence": 0.87,
  "prediction_id": "pred_20260211_143022_abc123"
}
```

**Verify Inference Logging:**

```bash
# Check inference log was created
cat data/monitoring/inference_log.csv | head -n 5

# Should show:
# - Header row
# - Prediction entries with timestamp, predicted_class, confidence, etc.
```

**Generate More Predictions (for metrics):**

```bash
# Generate 20 predictions
for i in {1..20}; do
  curl -X POST http://localhost:8000/predict \
    -H "Content-Type: application/json" \
    -d "{\"designation\": \"Product $i\", \"description\": \"Test description\"}" \
    -s > /dev/null
  echo "Prediction $i done"
done
```

**Check Metrics:**

```bash
curl http://localhost:8000/metrics | grep rakuten_predictions_total
# Should show counts by class
```

---

### ✅ Phase 5: Monitoring Stack

**Start Monitoring:**

```bash
make start-monitor

# Check services
curl http://localhost:9090/-/healthy  # Prometheus
curl http://localhost:3000/api/health  # Grafana
```

**Test Prometheus:**

1. Open http://localhost:9090
2. Go to Status → Targets
3. Verify `rakuten-api` target is **UP** (green)
4. Go to Graph tab
5. Run query: `sum(rakuten_predictions_total)`
   - Should show total predictions made

**Test Grafana:**

1. Open http://localhost:3000
2. Login: admin/admin (set new password or skip)
3. Go to Dashboards → Browse
4. Click "Rakuten MLOps Dashboard"
5. Verify panels show data:
   - Total Predictions
   - Prediction Rate
   - Latency P95
   - Model Version
   - Top 10 Predicted Classes

**If no data in Grafana:**
- Make more predictions (see above)
- Wait 30 seconds for Prometheus to scrape
- Refresh Grafana dashboard

---

### ✅ Phase 6: Prefect Flows (Optional)

**Note**: Prefect requires separate setup. Testing is optional.

**Start Prefect Server:**

```bash
# In a separate terminal
prefect server start

# Access UI: http://localhost:4200
```

**Deploy Flows:**

```bash
# In project root
prefect deploy --all

# Verify deployments
prefect deployment ls
```

**Trigger Training Flow:**

```bash
prefect deployment run rakuten-mlops/training-pipeline

# Monitor in UI: http://localhost:4200
```

**Test Monitoring Flow:**

```bash
# Generate enough predictions for drift detection (>100)
for i in {1..150}; do
  curl -X POST http://localhost:8000/predict \
    -H "Content-Type: application/json" \
    -d "{\"designation\": \"Product $i\", \"description\": \"Description $i\"}" \
    -s > /dev/null
done

# Trigger monitoring flow
prefect deployment run rakuten-mlops/monitor-and-retrain

# Check for Evidently report
ls -la reports/evidently/
# Should see evidently_report.html
open reports/evidently/evidently_report.html
```

---

## Comprehensive System Test

**Full Stack Test (All Services Running):**

```bash
# Start everything
make start-full

# Wait 2 minutes for all services to initialize

# Check all services
make check-health

# Expected output (all should be OK):
# PostgreSQL: OK
# MLflow: OK
# Airflow: OK
# API: OK
# Prometheus: OK
# Grafana: OK
```

**Test Workflow End-to-End:**

1. ✅ **Data Pipeline**: `make init-db` (40% data loaded)
2. ✅ **Training**: `python scripts/train_baseline_model.py --auto-promote`
3. ✅ **Model Registry**: Verify in MLflow UI (Production stage)
4. ✅ **Inference**: `curl` predictions via API
5. ✅ **Metrics**: View in Prometheus/Grafana
6. ✅ **Logging**: Check `data/monitoring/inference_log.csv`
7. ✅ **Orchestration**: Trigger Airflow DAG (optional)
8. ✅ **Monitoring**: Generate Evidently report (optional)

---

## Troubleshooting

### Services Won't Start

```bash
# Check Docker resources
docker system df

# Check if ports are in use
lsof -i :5000  # MLflow
lsof -i :8000  # API
lsof -i :8080  # Airflow
lsof -i :9090  # Prometheus
lsof -i :3000  # Grafana

# Clean restart
make stop-full
docker system prune -f
make start-full
```

### Model Won't Load in API

```bash
# Check model exists in registry
curl http://localhost:5000/api/2.0/mlflow/registered-models/get?name=rakuten_classifier

# Check API logs
docker logs rakuten_api

# Restart API
make restart-api
```

### No Metrics in Grafana

```bash
# 1. Generate predictions
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"designation": "Test", "description": "Product"}'

# 2. Check Prometheus is scraping
open http://localhost:9090/targets

# 3. Wait 30 seconds and refresh Grafana
```

### Database Connection Errors

```bash
# Check PostgreSQL is running
docker logs rakuten_postgres

# Test connection
docker exec -it rakuten_postgres psql -U rakuten_user -d rakuten_db -c "SELECT COUNT(*) FROM products;"

# Reinitialize if needed
make clean  # WARNING: deletes data
make start
make init-db
```

---

## Success Criteria

All tests pass if:

✅ **Infrastructure**: All services start and are healthy  
✅ **Database**: 40% data loaded (~34k products)  
✅ **Training**: Model trained and registered to Production  
✅ **API**: Health check returns "healthy" with model loaded  
✅ **Predictions**: `/predict` endpoint returns valid predictions  
✅ **Metrics**: Prometheus collects metrics from API  
✅ **Dashboards**: Grafana shows real-time prediction metrics  
✅ **Logging**: Inferences written to CSV  

---

## Current Limitations

**What's Not Implemented Yet:**

1. **Streamlit UI** (Phase 6 - In Progress)
   - No web control room
   - Must use CLI/curl for operations

2. **Advanced Monitoring** (Phase 7)
   - No automatic drift alerts
   - No Slack/email notifications
   - Manual Evidently report generation

3. **Features**
   - Image features not used (text-only model)
   - No model ensembles
   - No A/B testing

---

## Next Session Resume Point

**Start Here**: Phase 6 - Streamlit UI Implementation

**Files Created So Far in Phase 6:**
- `streamlit_app/.streamlit/config.toml`
- `streamlit_app/.streamlit/secrets.toml.example`
- `streamlit_app/managers/docker_manager.py`

**Remaining Work:**
1. Complete managers (4 more: MLflow, Prediction, Training, Database)
2. Implement 6 pages (Home, Infrastructure, Dataset, Training, Predictions, Monitoring)
3. Phase 7: Integration testing and final documentation

See `docs/IMPLEMENTATION_ROADMAP.md` for detailed continuation guide.

---

**Testing Complete!** 🎉

All implemented phases are working. Ready to continue with Streamlit UI in next session.
