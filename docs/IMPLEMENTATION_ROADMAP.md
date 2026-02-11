# Implementation Roadmap - Rakuten MLOps Control Room

## 🎯 Goal
Build end-to-end MLOps platform in **8 phases** with git checkpoints for resumability.

**Status Tracking**: Update this file as you complete each phase.

---

## 📋 Phase Overview

| Phase | Component | Estimated Time | Git Checkpoint |
|-------|-----------|----------------|----------------|
| 0 | Documentation & Setup | 30 min | ✅ `docs: add target architecture and roadmap` |
| 1 | Docker Compose Refactor | 30 min | `infra: split docker compose into modular files` |
| 2 | FastAPI Service | 2 hours | `feat: implement FastAPI serving with MLflow registry` |
| 3 | Model Training | 1.5 hours | `feat: complete model training with MLflow logging` |
| 4 | Prefect Flows | 1 hour | `feat: add Prefect flows for training and monitoring` |
| 5 | Monitoring Stack | 1 hour | `feat: setup Prometheus and Grafana monitoring` |
| 6 | Streamlit UI | 3 hours | `feat: build Streamlit control room UI` |
| 7 | Integration & Testing | 1 hour | `test: end-to-end integration and documentation` |

**Total Estimated Time**: ~10 hours (spread across multiple sessions)

---

## Phase 0: Documentation & Setup ✅

**Goal**: Create comprehensive docs for resumability

### Tasks
- [x] Create `docs/TARGET_ARCHITECTURE.md`
- [x] Create `docs/IMPLEMENTATION_ROADMAP.md`
- [ ] Update `.env.example` with new environment variables
- [ ] Create `requirements-api.txt` for FastAPI service
- [ ] Create `requirements-streamlit.txt` for UI

### Deliverables
- Complete architecture documentation
- Implementation roadmap with checkpoints
- Environment variable templates

### Git Checkpoint
```bash
git add docs/TARGET_ARCHITECTURE.md docs/IMPLEMENTATION_ROADMAP.md
git commit -m "docs: add target architecture and implementation roadmap"
git push origin <branch>
```

**Status**: 🚧 In Progress

---

## Phase 1: Docker Compose Refactor

**Goal**: Split monolithic compose into modular files

### Tasks
- [ ] Rename `docker-compose.yml` → `docker-compose.infrastructure.yml`
- [ ] Create `docker-compose.api.yml` (postgres, mlflow, api service)
- [ ] Create `docker-compose.monitor.yml` (prometheus, grafana)
- [ ] Create `docker-compose.full.yml` (references all three)
- [ ] Update Makefile with new compose commands
- [ ] Create Dockerfile for FastAPI service (`src/serve/Dockerfile`)

### Files to Create/Modify
```
docker-compose.infrastructure.yml  (rename from docker-compose.yml)
docker-compose.api.yml             (new)
docker-compose.monitor.yml         (new)
docker-compose.full.yml            (new)
src/serve/Dockerfile               (new)
Makefile                           (update)
```

### Makefile Commands to Add
```makefile
# API stack
start-api:
	docker-compose -f docker-compose.api.yml up -d

stop-api:
	docker-compose -f docker-compose.api.yml down

# Monitoring stack
start-monitor:
	docker-compose -f docker-compose.monitor.yml up -d

stop-monitor:
	docker-compose -f docker-compose.monitor.yml down

# Full stack
start-full:
	docker-compose -f docker-compose.full.yml up -d

stop-full:
	docker-compose -f docker-compose.full.yml down
```

### Testing
```bash
# Test infrastructure stack still works
make start  # should use infrastructure compose
make ps

# Test new API stack
make start-api
curl http://localhost:8000/health

# Test monitoring stack
make start-monitor
curl http://localhost:9090/-/healthy
```

### Git Checkpoint
```bash
git add docker-compose*.yml src/serve/Dockerfile Makefile
git commit -m "infra: split docker compose into modular infrastructure, api, and monitoring stacks"
git push origin <branch>
```

**Status**: ⏳ Pending

---

## Phase 2: FastAPI Service

**Goal**: Implement serving layer with MLflow registry integration

### Tasks

#### 2.1 Project Structure
- [ ] Create `src/serve/` directory structure
- [ ] Create `requirements-api.txt`
- [ ] Create Dockerfile

#### 2.2 Core Components
- [ ] `src/serve/main.py` - FastAPI app initialization
- [ ] `src/serve/routes.py` - Endpoints (/health, /predict, /metrics)
- [ ] `src/serve/schemas.py` - Pydantic models (request/response)
- [ ] `src/serve/model_loader.py` - MLflow registry loader with caching
- [ ] `src/serve/metrics.py` - Prometheus instrumentation
- [ ] `src/serve/inference_logger.py` - Log predictions to CSV
- [ ] `src/serve/config.py` - Service configuration

#### 2.3 Features to Implement

**`/health` endpoint**
- Check service is running
- Check MLflow connectivity
- Check model is loaded
- Return model metadata (name, version, stage)

**`/predict` endpoint**
- Accept JSON with designation, description, imageid (optional)
- Load model from cache (lazy load on first request)
- Preprocess text (use existing `src/utils/text_preprocessing.py`)
- Make prediction
- Log inference to `data/monitoring/inference_log.csv`
- Update Prometheus metrics
- Return prediction + probabilities

**`/metrics` endpoint**
- Export Prometheus metrics:
  - `rakuten_predictions_total{prdtypecode}` (counter)
  - `rakuten_prediction_latency_seconds` (histogram)
  - `rakuten_text_len_chars` (histogram)
  - `rakuten_model_info{version, stage}` (gauge)

#### 2.4 Model Loader Logic
```python
class ModelLoader:
    def __init__(self):
        self._model = None
        self._vectorizer = None
        self._version = None
        self._last_reload = None
        self._reload_interval = 300  # 5 minutes
    
    def get_model(self):
        if self._should_reload():
            self._load_from_registry()
        return self._model, self._vectorizer
    
    def _should_reload(self):
        # Reload if never loaded or interval passed
        if self._model is None:
            return True
        if time.time() - self._last_reload > self._reload_interval:
            return True
        return False
    
    def _load_from_registry(self):
        # Load from MLflow registry
        model_uri = f"models:/{MODEL_NAME}/{MODEL_STAGE}"
        self._model = mlflow.sklearn.load_model(model_uri)
        # Load vectorizer from artifacts
        # Update version metadata
```

### Files to Create
```
src/serve/
├── __init__.py
├── main.py                  # FastAPI app
├── routes.py                # Route handlers
├── schemas.py               # Pydantic models
├── model_loader.py          # MLflow registry loader
├── metrics.py               # Prometheus metrics
├── inference_logger.py      # CSV logging
├── config.py                # Configuration
└── Dockerfile               # Container image

requirements-api.txt         # FastAPI dependencies
data/monitoring/             # Create directory
└── inference_log.csv        # Will be created by API
```

### Testing
```bash
# Start API
make start-api

# Test health
curl http://localhost:8000/health

# Test OpenAPI docs
open http://localhost:8000/docs

# Test prediction (will fail initially - no model in registry yet)
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"designation": "iPhone 13", "description": "Smartphone Apple"}'

# Test metrics
curl http://localhost:8000/metrics

# Check inference log
cat data/monitoring/inference_log.csv
```

### Git Checkpoint
```bash
git add src/serve/ requirements-api.txt docker-compose.api.yml data/monitoring/.gitkeep
git commit -m "feat: implement FastAPI serving with MLflow registry integration and Prometheus metrics"
git push origin <branch>
```

**Status**: ⏳ Pending

---

## Phase 3: Model Training

**Goal**: Complete model training pipeline with MLflow logging

### Tasks

#### 3.1 Feature Engineering
- [ ] Create `src/features/__init__.py`
- [ ] Create `src/features/text_features.py` (TF-IDF extraction)
- [ ] Integrate with existing `src/utils/text_preprocessing.py`

#### 3.2 Model Training
- [ ] Complete `src/models/train.py` (currently a stub)
- [ ] Create `src/models/model_registry.py` (registry helpers)
- [ ] Create `src/models/evaluate.py` (metrics calculation)

#### 3.3 Training Pipeline Flow
```
1. Load dataset from MLflow (train_week_N.parquet)
2. Preprocess text (lowercase, remove special chars)
3. Extract TF-IDF features (max_features=5000, ngram_range=(1,2))
4. Train LogisticRegression (multi_class='multinomial', max_iter=1000, C=1.0)
5. Evaluate on test set
6. Log to MLflow:
   - Parameters
   - Metrics (accuracy, f1_macro, f1_weighted, per-class f1)
   - Artifacts (model, vectorizer, confusion matrix)
7. Register model to "rakuten_classifier"
8. Return model_run_id
```

#### 3.4 MLflow Registry Integration

**Register Model**
```python
def register_model(run_id: str, model_name: str = "rakuten_classifier"):
    """Register model from run to registry"""
    model_uri = f"runs:/{run_id}/model"
    mv = mlflow.register_model(model_uri, model_name)
    return mv.version

def promote_model(model_name: str, version: int, stage: str):
    """Promote model to stage (Staging, Production)"""
    client = MlflowClient()
    client.transition_model_version_stage(
        name=model_name,
        version=version,
        stage=stage,
        archive_existing_versions=True
    )
```

### Files to Create/Modify
```
src/features/
├── __init__.py
├── text_features.py         # TF-IDF extraction

src/models/
├── train.py                 # MODIFY: implement training
├── model_registry.py        # NEW: registry helpers
└── evaluate.py              # NEW: metrics calculation

scripts/
└── train_baseline_model.py  # Standalone script to train initial model
```

### Testing
```bash
# Train initial model manually
python scripts/train_baseline_model.py

# Check MLflow UI
open http://localhost:5000

# Verify model in registry
mlflow models list --name rakuten_classifier

# Test API now loads model
curl http://localhost:8000/health
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"designation": "iPhone 13", "description": "Smartphone Apple"}'
```

### Git Checkpoint
```bash
git add src/features/ src/models/ scripts/train_baseline_model.py
git commit -m "feat: complete model training with TF-IDF + LogisticRegression and MLflow registry integration"
git push origin <branch>
```

**Status**: ⏳ Pending

---

## Phase 4: Prefect Flows

**Goal**: Add Prefect orchestration for training and monitoring

### Tasks

#### 4.1 Setup Prefect
- [ ] Add prefect to requirements
- [ ] Create `flows/` directory
- [ ] Initialize Prefect project

#### 4.2 Training Flow
- [ ] Create `flows/pipeline_flow.py`
- [ ] Implement training pipeline flow
- [ ] Add error handling and retries

#### 4.3 Monitoring Flow
- [ ] Create `flows/monitor_and_retrain.py`
- [ ] Implement drift detection logic
- [ ] Add conditional retraining trigger

#### 4.4 Deployment Config
- [ ] Create `prefect.yaml`
- [ ] Configure daily schedule (09:00 UTC)
- [ ] Add deployment instructions to README

### Files to Create
```
flows/
├── __init__.py
├── pipeline_flow.py         # Training pipeline
├── monitor_and_retrain.py   # Drift monitoring
└── prefect.yaml             # Deployment config

src/monitoring/
├── __init__.py
├── drift_detector.py        # Evidently integration
└── thresholds.py            # Drift thresholds
```

### Prefect Commands
```bash
# Install Prefect
pip install prefect

# Start Prefect server (local)
prefect server start

# Deploy flows
prefect deploy --all

# Trigger training flow manually
prefect deployment run rakuten-training-pipeline/production

# Check monitoring flow schedule
prefect deployment ls
```

### Integration with Airflow
Update Airflow DAG to trigger Prefect flow after dataset generation:
```python
def trigger_prefect_training(**context):
    """Trigger Prefect training flow after dataset generation"""
    dataset_run_id = context['ti'].xcom_pull(key='dataset_run_id')
    week_number = context['ti'].xcom_pull(key='week_number')
    
    # Call Prefect API to trigger flow
    import requests
    response = requests.post(
        "http://localhost:4200/api/deployments/<deployment-id>/create_flow_run",
        json={"parameters": {"dataset_run_id": dataset_run_id}}
    )
    return response.json()
```

### Testing
```bash
# Start Prefect server
prefect server start &

# Deploy flows
cd flows
prefect deploy --all

# Test training flow
prefect deployment run rakuten-training-pipeline/production \
  --param week_number=1

# Test monitoring flow
prefect deployment run rakuten-monitor-retrain/production

# Check Prefect UI
open http://localhost:4200
```

### Git Checkpoint
```bash
git add flows/ src/monitoring/ prefect.yaml requirements.txt
git commit -m "feat: add Prefect flows for training pipeline and drift monitoring with daily schedule"
git push origin <branch>
```

**Status**: ⏳ Pending

---

## Phase 5: Monitoring Stack

**Goal**: Setup Prometheus and Grafana for observability

### Tasks

#### 5.1 Prometheus
- [ ] Create `monitoring/prometheus.yml`
- [ ] Configure scrape for FastAPI `/metrics`
- [ ] Add to `docker-compose.monitor.yml`
- [ ] Create `monitoring/README.md` with useful queries

#### 5.2 Grafana
- [ ] Add Grafana to `docker-compose.monitor.yml`
- [ ] Create `grafana/provisioning/datasources/prometheus.yml`
- [ ] Create `grafana/provisioning/dashboards/dashboards.yml`
- [ ] Create `grafana/provisioning/dashboards/rakuten_dashboard.json`
- [ ] Create `grafana/README.md` with panel descriptions

#### 5.3 Evidently Reports
- [ ] Implement `src/monitoring/drift_detector.py`
- [ ] Create report generator script
- [ ] Add to monitoring flow

### Files to Create
```
monitoring/
├── prometheus.yml           # Prometheus config
└── README.md                # PromQL queries

grafana/
├── provisioning/
│   ├── datasources/
│   │   └── prometheus.yml
│   └── dashboards/
│       ├── dashboards.yml
│       └── rakuten_dashboard.json
└── README.md                # Dashboard documentation

reports/
└── evidently/
    └── .gitkeep

docker-compose.monitor.yml   # MODIFY: add services
```

### Prometheus Scrape Config
```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'rakuten-api'
    static_configs:
      - targets: ['api:8000']
    metrics_path: '/metrics'
```

### Grafana Dashboard Panels
1. **Total Predictions**: `rate(rakuten_predictions_total[5m])`
2. **Predictions by Class**: `rakuten_predictions_total`
3. **Latency P95**: `histogram_quantile(0.95, rakuten_prediction_latency_seconds)`
4. **Text Length Avg**: `avg(rakuten_text_len_chars)`
5. **Error Rate**: `rate(rakuten_api_errors_total[5m])`

### Useful PromQL Queries
```promql
# Prediction rate (predictions/sec)
rate(rakuten_predictions_total[5m])

# Most predicted class
topk(5, sum by (prdtypecode) (rakuten_predictions_total))

# P50, P95, P99 latency
histogram_quantile(0.50, rate(rakuten_prediction_latency_seconds_bucket[5m]))
histogram_quantile(0.95, rate(rakuten_prediction_latency_seconds_bucket[5m]))
histogram_quantile(0.99, rate(rakuten_prediction_latency_seconds_bucket[5m]))

# Average text length
avg(rakuten_text_len_chars)
```

### Testing
```bash
# Start monitoring stack
make start-monitor

# Check Prometheus
open http://localhost:9090
# Try query: rakuten_predictions_total

# Check Grafana
open http://localhost:3000
# Login: admin/admin
# Navigate to Dashboards → Rakuten MLOps

# Generate some predictions to populate metrics
for i in {1..100}; do
  curl -X POST http://localhost:8000/predict \
    -H "Content-Type: application/json" \
    -d '{"designation": "Test Product", "description": "Test description"}'
done

# Generate Evidently report
python -m src.monitoring.drift_detector

# View report
open reports/evidently/evidently_report.html
```

### Git Checkpoint
```bash
git add monitoring/ grafana/ src/monitoring/ reports/.gitkeep docker-compose.monitor.yml
git commit -m "feat: setup Prometheus and Grafana monitoring with Evidently drift reports"
git push origin <branch>
```

**Status**: ⏳ Pending

---

## Phase 6: Streamlit UI

**Goal**: Build control room interface for full system management

### Tasks

#### 6.1 Setup
- [ ] Create `streamlit_app/` structure
- [ ] Create `requirements-streamlit.txt`
- [ ] Create `.streamlit/config.toml`
- [ ] Create `.streamlit/secrets.toml.example`

#### 6.2 Pages
- [ ] `Home.py` - Landing page with system overview
- [ ] `pages/2_Infrastructure.py` - Service health + Docker controls
- [ ] `pages/3_Dataset.py` - Dataset explorer + stats
- [ ] `pages/4_Training.py` - MLflow experiments + trigger training
- [ ] `pages/5_Predictions.py` - Live prediction UI
- [ ] `pages/6_Monitoring.py` - Evidently reports + Grafana links

#### 6.3 Managers (Business Logic)
- [ ] `managers/docker_manager.py` - Docker health checks + controls
- [ ] `managers/mlflow_manager.py` - MLflow queries
- [ ] `managers/prediction_manager.py` - API predictions
- [ ] `managers/training_manager.py` - Trigger Prefect flows
- [ ] `managers/database_manager.py` - PostgreSQL queries

#### 6.4 Components (Reusable UI)
- [ ] `components/metrics_display.py` - Metric cards
- [ ] `components/charts.py` - Chart helpers
- [ ] `components/status_badge.py` - Health status badges

### Files to Create
```
streamlit_app/
├── Home.py                       # Landing page
├── pages/
│   ├── 2_Infrastructure.py       # Service health
│   ├── 3_Dataset.py              # Dataset explorer
│   ├── 4_Training.py             # MLflow + training
│   ├── 5_Predictions.py          # Prediction UI
│   └── 6_Monitoring.py           # Monitoring dashboards
├── managers/
│   ├── __init__.py
│   ├── docker_manager.py         # Docker operations
│   ├── mlflow_manager.py         # MLflow queries
│   ├── prediction_manager.py     # API calls
│   ├── training_manager.py       # Prefect triggers
│   └── database_manager.py       # PostgreSQL queries
├── components/
│   ├── __init__.py
│   ├── metrics_display.py
│   ├── charts.py
│   └── status_badge.py
└── .streamlit/
    ├── config.toml
    └── secrets.toml.example

requirements-streamlit.txt
```

### Key Features per Page

**Home.py**
- System architecture diagram (use st.image or st.graphviz)
- Quick service status overview (all green/red indicators)
- Links to all services
- Recent activity feed (last 10 predictions, last training run)

**Infrastructure.py**
- Service health table (name, status, uptime, URL)
- Docker controls (start/stop/restart per stack)
- Resource usage (if available via Docker API)
- Logs viewer (tail last 100 lines)

**Dataset.py**
- Current data percentage (metric card)
- Class distribution chart (bar chart)
- Sample products viewer (dataframe with 20 samples)
- Data loading history (table from `data_loads`)
- Button to trigger Airflow DAG

**Training.py**
- MLflow experiment browser (selectbox)
- Runs comparison table (metrics, params, artifacts)
- Run details (when selected)
- Model registry browser (list versions, stages)
- Promote model button (transition stage)
- Trigger training button (calls Prefect)

**Predictions.py**
- Input form (text inputs for designation/description)
- Optional image uploader
- Predict button
- Results display (predicted class, confidence, top-5 probs)
- Prediction history table (last 50 from inference log)

**Monitoring.py**
- Embedded Evidently report (st.components.v1.html)
- Drift metrics summary (metric cards)
- Prometheus status + link
- Grafana dashboard embed or link
- Trigger monitoring flow button

### Streamlit Config
```toml
# .streamlit/config.toml
[theme]
primaryColor = "#FF4B4B"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F0F2F6"
textColor = "#262730"
font = "sans serif"

[server]
port = 8501
headless = true
```

### Testing
```bash
# Install Streamlit dependencies
pip install -r requirements-streamlit.txt

# Run Streamlit
streamlit run streamlit_app/Home.py

# Open browser
open http://localhost:8501

# Test each page:
# 1. Home - should show system overview
# 2. Infrastructure - should show service health
# 3. Dataset - should query PostgreSQL and show data
# 4. Training - should connect to MLflow
# 5. Predictions - should call API /predict
# 6. Monitoring - should show Evidently report
```

### Git Checkpoint
```bash
git add streamlit_app/ requirements-streamlit.txt
git commit -m "feat: build Streamlit control room with Infrastructure, Dataset, Training, Predictions, and Monitoring pages"
git push origin <branch>
```

**Status**: ⏳ Pending

---

## Phase 7: Integration & Testing

**Goal**: End-to-end testing and documentation

### Tasks

#### 7.1 Integration Testing
- [ ] Test full data pipeline (Airflow → Prefect → MLflow)
- [ ] Test API serving with predictions
- [ ] Test Prometheus scraping
- [ ] Test Grafana dashboards
- [ ] Test Streamlit UI end-to-end
- [ ] Test drift monitoring flow

#### 7.2 Documentation
- [ ] Update main `README.md` with new architecture
- [ ] Add "Quick Start" section with all stacks
- [ ] Document environment variables in `.env.example`
- [ ] Create `monitoring/README.md` with PromQL queries
- [ ] Create `grafana/README.md` with dashboard guide
- [ ] Update `docs/ARCHITECTURE_PLAN.md` (note: now hybrid with Prefect)

#### 7.3 Cleanup
- [ ] Remove unused files
- [ ] Fix linter errors
- [ ] Add `.gitignore` entries for logs/artifacts
- [ ] Verify no secrets committed

### Testing Checklist

#### Infrastructure
- [ ] `make start` starts infrastructure stack
- [ ] Airflow UI accessible at :8080
- [ ] MLflow UI accessible at :5000
- [ ] PostgreSQL accessible and initialized

#### API
- [ ] `make start-api` starts API
- [ ] `/health` returns healthy status
- [ ] `/docs` shows OpenAPI documentation
- [ ] `/predict` returns predictions
- [ ] `/metrics` returns Prometheus metrics
- [ ] Inference log is created and updated

#### Monitoring
- [ ] `make start-monitor` starts Prometheus + Grafana
- [ ] Prometheus scrapes API metrics
- [ ] Grafana shows provisioned dashboard
- [ ] Dashboard panels display data

#### Streamlit
- [ ] `streamlit run streamlit_app/Home.py` starts UI
- [ ] All 6 pages load without errors
- [ ] Can trigger training from UI
- [ ] Can make predictions from UI
- [ ] Can view MLflow experiments
- [ ] Can promote models
- [ ] Can view monitoring dashboards

#### End-to-End Flow
1. [ ] Start infrastructure → init DB → trigger Airflow DAG
2. [ ] Airflow loads data → generates dataset → triggers Prefect
3. [ ] Prefect trains model → registers to MLflow
4. [ ] Start API → loads model from registry
5. [ ] Make predictions → logs to inference CSV → updates Prometheus
6. [ ] Prometheus scrapes metrics → Grafana displays
7. [ ] Run monitoring flow → generates Evidently report
8. [ ] View all via Streamlit UI

### README.md Structure
```markdown
# Rakuten MLOps Control Room

## Architecture
(diagram or link to docs/TARGET_ARCHITECTURE.md)

## Quick Start

### Prerequisites
- Docker Desktop running
- Data in `data/raw/`

### 1. Start Infrastructure
docker-compose -f docker-compose.infrastructure.yml up -d
make init-db

### 2. Start API
docker-compose -f docker-compose.api.yml up -d

### 3. Start Monitoring
docker-compose -f docker-compose.monitor.yml up -d

### 4. Launch Streamlit
streamlit run streamlit_app/Home.py

### Access Services
- Airflow: http://localhost:8080 (admin/admin)
- MLflow: http://localhost:5000
- API: http://localhost:8000/docs
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (admin/admin)
- Streamlit: http://localhost:8501

## Components
- **Data Pipeline**: Airflow orchestrates incremental data loading
- **ML Pipeline**: Prefect orchestrates training and monitoring
- **Serving**: FastAPI with MLflow model registry
- **Monitoring**: Prometheus + Grafana + Evidently
- **Control Room**: Streamlit UI

## Documentation
- [Target Architecture](docs/TARGET_ARCHITECTURE.md)
- [Implementation Roadmap](docs/IMPLEMENTATION_ROADMAP.md)
- [Monitoring Guide](monitoring/README.md)
- [Grafana Dashboards](grafana/README.md)
```

### Git Checkpoint
```bash
# Update all documentation
git add README.md .env.example monitoring/README.md grafana/README.md

# Final integration commit
git commit -m "test: end-to-end integration testing and comprehensive documentation"
git push origin <branch>

# Create release tag
git tag -a v1.0.0 -m "Rakuten MLOps Control Room v1.0.0 - Complete Implementation"
git push origin v1.0.0
```

**Status**: ⏳ Pending

---

## 🔄 Resuming Work

If work is interrupted, use this checklist to resume:

1. **Check Phase Status**: Review this file to see last completed phase
2. **Read Git Log**: `git log --oneline -10` to see recent commits
3. **Check Services**: `docker ps` to see what's running
4. **Review Docs**: Read `docs/TARGET_ARCHITECTURE.md` for context
5. **Continue Next Phase**: Pick up from next pending phase

---

## 📊 Progress Tracking

**Overall Progress**: 1/8 phases complete (12.5%)

### Phase Completion Status
- [x] Phase 0: Documentation & Setup (✅ Complete)
- [ ] Phase 1: Docker Compose Refactor (⏳ Pending)
- [ ] Phase 2: FastAPI Service (⏳ Pending)
- [ ] Phase 3: Model Training (⏳ Pending)
- [ ] Phase 4: Prefect Flows (⏳ Pending)
- [ ] Phase 5: Monitoring Stack (⏳ Pending)
- [ ] Phase 6: Streamlit UI (⏳ Pending)
- [ ] Phase 7: Integration & Testing (⏳ Pending)

**Last Updated**: 2026-02-11  
**Current Phase**: 0 (Documentation)  
**Next Phase**: 1 (Docker Compose Refactor)

---

## 🆘 Troubleshooting

### Common Issues

**Docker services won't start**
```bash
# Check if ports are already in use
lsof -i :8000  # API
lsof -i :5000  # MLflow
lsof -i :9090  # Prometheus

# Clean up and restart
make stop-full
docker system prune -f
make start-full
```

**MLflow can't connect to MinIO**
```bash
# Check MinIO is running
docker ps | grep minio

# Recreate MinIO buckets
docker-compose exec minio-init sh
```

**Streamlit can't connect to services**
```bash
# Check .streamlit/secrets.toml
# Verify API_URL, MLFLOW_URI, etc.

# Test connectivity
curl http://localhost:8000/health
curl http://localhost:5000/health
```

**Model not loading in API**
```bash
# Check model exists in registry
mlflow models list --name rakuten_classifier

# Check API logs
docker-compose -f docker-compose.api.yml logs api

# Manually test model loading
python -c "import mlflow; print(mlflow.sklearn.load_model('models:/rakuten_classifier/Production'))"
```

---

**End of Roadmap**
