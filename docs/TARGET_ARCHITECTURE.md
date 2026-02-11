# Target Architecture - Rakuten MLOps Control Room

## 🎯 Project Vision

End-to-end MLOps platform for Rakuten product classification with:
- **Data Pipeline**: Airflow-orchestrated incremental data loading (40% → 100%)
- **ML Pipeline**: Prefect-orchestrated training and monitoring
- **Serving**: FastAPI with MLflow model registry integration
- **Observability**: Prometheus + Grafana + Evidently drift detection
- **Control Room**: Streamlit UI for full system management

---

## 📐 System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         STREAMLIT CONTROL ROOM                      │
│  Home | Infrastructure | Dataset | Training | Predictions | Monitor │
└────┬────────────────────────────────────────────────────────────┬───┘
     │                                                            │
     │                                                            │
     ▼                                                            ▼
┌─────────────────────────────────────┐    ┌──────────────────────────────┐
│  DATA PIPELINE (Airflow)            │    │  SERVING LAYER               │
│  ┌───────────────────────────────┐  │    │  ┌────────────────────────┐ │
│  │ PostgreSQL (Incremental Data) │  │    │  │ FastAPI Service        │ │
│  │ - products (40%→100%)         │  │    │  │ /health, /predict      │ │
│  │ - labels                      │  │    │  │ /metrics (Prometheus)  │ │
│  │ - audit trail                 │  │    │  │                        │ │
│  └───────┬───────────────────────┘  │    │  │ Loads model from:      │ │
│          │                           │    │  │ MLflow Registry        │ │
│          ▼                           │    │  │ (Production stage)     │ │
│  ┌───────────────────────────────┐  │    │  └────────┬───────────────┘ │
│  │ Airflow DAG (weekly)          │  │    │           │                 │
│  │ - Load +3% data               │  │    │           │ logs inferences │
│  │ - Generate balanced dataset   │  │    │           ▼                 │
│  │ - Log to MLflow               │  │    │  ┌────────────────────────┐ │
│  │ - Trigger Prefect training    │  │    │  │ inference_log.csv      │ │
│  └───────────────────────────────┘  │    │  │ (for drift detection)  │ │
└─────────────────────────────────────┘    │  └────────────────────────┘ │
                                           └──────────────────────────────┘
     │                                                  │
     │ dataset versioned                               │ scraped by
     ▼                                                  ▼
┌─────────────────────────────────────┐    ┌──────────────────────────────┐
│  MLFLOW (Tracking + Registry)       │    │  MONITORING STACK            │
│  ┌───────────────────────────────┐  │    │  ┌────────────────────────┐ │
│  │ Experiments:                  │  │    │  │ Prometheus (9090)      │ │
│  │ - rakuten_dataset_versioning  │  │    │  │ - rakuten_predictions_ │ │
│  │ - rakuten_model_training      │  │    │  │   total                │ │
│  │                               │  │    │  │ - rakuten_prediction_  │ │
│  │ Model Registry:               │  │    │  │   latency_seconds      │ │
│  │ - rakuten_classifier          │  │    │  │ - rakuten_text_len_    │ │
│  │   └─ Production (v1, v2...)   │  │    │  │   chars                │ │
│  │   └─ Staging                  │  │    │  └────────┬───────────────┘ │
│  └───────────────────────────────┘  │    │           │                 │
│                                     │    │           │ datasource      │
│  Artifacts (MinIO S3):              │    │           ▼                 │
│  - train_week_N.parquet             │    │  ┌────────────────────────┐ │
│  - test_df.parquet                  │    │  │ Grafana (3000)         │ │
│  - trained models                   │    │  │ - Predictions panel    │ │
│  - class distribution plots         │    │  │ - Latency panel        │ │
└─────────────────────────────────────┘    │  │ - Text length panel    │ │
                                           │  └────────────────────────┘ │
     ▲                                     └──────────────────────────────┘
     │ logs experiments
     │
┌─────────────────────────────────────┐
│  ML PIPELINE (Prefect)              │
│  ┌───────────────────────────────┐  │
│  │ Flow: pipeline_flow.py        │  │
│  │ - Load dataset from MLflow    │  │
│  │ - Feature engineering         │  │
│  │ - Train model                 │  │
│  │ - Register to MLflow registry │  │
│  │ - Promote to Production       │  │
│  └───────────────────────────────┘  │
│                                     │
│  ┌───────────────────────────────┐  │
│  │ Flow: monitor_and_retrain.py  │  │
│  │ - Load inference log          │  │
│  │ - Generate Evidently report   │  │
│  │ - Check drift threshold       │  │
│  │ - Trigger retrain if needed   │  │
│  └───────────────────────────────┘  │
│                                     │
│  Scheduled: Daily @ 09:00 UTC       │
└─────────────────────────────────────┘

     │ generates
     ▼
┌─────────────────────────────────────┐
│  DRIFT REPORTS                      │
│  reports/evidently/                 │
│  - evidently_report.html            │
│  - drift_metrics.json               │
└─────────────────────────────────────┘
```

---

## 🗂️ Directory Structure

```
sep25_cmlops_rakuten/
├── docker-compose.infrastructure.yml  # Postgres, MLflow, MinIO, Airflow
├── docker-compose.api.yml             # FastAPI service (minimal)
├── docker-compose.monitor.yml         # Prometheus + Grafana
├── docker-compose.full.yml            # All services together
├── .env
├── .env.example
├── Makefile
├── README.md
├── requirements.txt
│
├── docs/
│   ├── ARCHITECTURE_PLAN.md           # Original incremental pipeline doc
│   ├── TARGET_ARCHITECTURE.md         # This file (full system vision)
│   └── IMPLEMENTATION_ROADMAP.md      # Phased implementation plan
│
├── data/
│   ├── raw/                           # (gitignored)
│   │   ├── X_train.csv
│   │   ├── Y_train.csv
│   │   ├── X_test.csv
│   │   └── images/
│   ├── processed/
│   │   └── processed_products.csv.dvc
│   └── monitoring/
│       └── inference_log.csv          # NEW: API inference logs
│
├── dags/                              # EXISTING: Airflow DAGs
│   ├── data_pipeline.py
│   └── weekly_ml_pipeline_dag.py
│
├── flows/                             # NEW: Prefect flows
│   ├── pipeline_flow.py               # Training pipeline
│   ├── monitor_and_retrain.py         # Drift monitoring + retrain
│   └── prefect.yaml                   # Deployment config
│
├── src/
│   ├── config.py                      # EXISTING: Config management
│   │
│   ├── data/                          # EXISTING: Data pipeline
│   │   ├── db_init.py
│   │   ├── loader.py
│   │   ├── dataset_generator.py
│   │   └── schema.sql
│   │
│   ├── features/                      # NEW: Feature engineering
│   │   ├── __init__.py
│   │   ├── text_features.py           # TF-IDF, text preprocessing
│   │   └── image_features.py          # Basic image features (optional)
│   │
│   ├── models/                        # ENHANCE: Complete model training
│   │   ├── __init__.py
│   │   ├── train.py                   # Train + register to MLflow
│   │   └── model_registry.py          # Registry helpers (promote, load)
│   │
│   ├── serve/                         # NEW: FastAPI service
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI app
│   │   ├── routes.py                  # /health, /predict, /metrics
│   │   ├── schemas.py                 # Pydantic models
│   │   ├── model_loader.py            # Lazy load from registry
│   │   └── metrics.py                 # Prometheus instrumentation
│   │
│   ├── monitoring/                    # NEW: Drift detection
│   │   ├── __init__.py
│   │   ├── drift_detector.py          # Evidently report generator
│   │   └── thresholds.py              # Drift thresholds config
│   │
│   └── utils/
│       ├── __init__.py
│       └── text_preprocessing.py      # EXISTING
│
├── streamlit_app/                     # NEW: Control room UI
│   ├── Home.py                        # Landing page
│   │
│   ├── pages/
│   │   ├── 2_Infrastructure.py        # Service health + Docker controls
│   │   ├── 3_Dataset.py               # Dataset explorer + stats
│   │   ├── 4_Training.py              # MLflow experiments + trigger training
│   │   ├── 5_Predictions.py           # Live prediction UI
│   │   └── 6_Monitoring.py            # Evidently reports + Grafana links
│   │
│   ├── components/                    # Reusable UI components
│   │   ├── __init__.py
│   │   ├── metrics_display.py
│   │   └── charts.py
│   │
│   ├── managers/                      # Business logic managers
│   │   ├── __init__.py
│   │   ├── docker_manager.py          # Docker health checks + controls
│   │   ├── mlflow_manager.py          # MLflow queries
│   │   ├── prediction_manager.py      # API predictions
│   │   └── training_manager.py        # Trigger Prefect flows
│   │
│   └── .streamlit/
│       └── secrets.toml.example
│
├── monitoring/                        # NEW: Prometheus config
│   ├── prometheus.yml                 # Scrape config
│   └── README.md
│
├── grafana/                           # NEW: Grafana config
│   ├── provisioning/
│   │   ├── datasources/
│   │   │   └── prometheus.yml
│   │   └── dashboards/
│   │       ├── dashboards.yml
│   │       └── rakuten_dashboard.json
│   └── README.md
│
└── reports/                           # NEW: Generated reports
    └── evidently/
        ├── evidently_report.html
        └── drift_metrics.json
```

---

## 🔧 Component Details

### 1. Docker Compose Architecture

#### `docker-compose.infrastructure.yml` (Existing + Renamed)
- **postgres**: Data storage + MLflow backend
- **minio**: S3-compatible artifact storage
- **mlflow**: Tracking server + model registry
- **airflow-***: Webserver, scheduler (data pipeline orchestration)

#### `docker-compose.api.yml` (New)
```yaml
services:
  postgres:  # Shared with infrastructure
  mlflow:    # Shared with infrastructure
  api:       # NEW: FastAPI service
    build: ./src/serve
    ports: ["8000:8000"]
    environment:
      MLFLOW_TRACKING_URI: http://mlflow:5000
      MODEL_NAME: rakuten_classifier
      MODEL_STAGE: Production
    volumes:
      - ./data/monitoring:/app/data/monitoring
```

#### `docker-compose.monitor.yml` (New)
```yaml
services:
  prometheus:
    image: prom/prometheus:latest
    ports: ["9090:9090"]
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'

  grafana:
    image: grafana/grafana:latest
    ports: ["3000:3000"]
    volumes:
      - ./grafana/provisioning:/etc/grafana/provisioning
      - grafana_data:/var/lib/grafana
```

---

### 2. FastAPI Service (`src/serve/`)

#### Endpoints

**`GET /health`**
```json
{
  "status": "healthy",
  "model": {
    "name": "rakuten_classifier",
    "version": "3",
    "stage": "Production",
    "loaded": true
  },
  "mlflow": {
    "reachable": true,
    "uri": "http://mlflow:5000"
  }
}
```

**`POST /predict`**
```json
// Request
{
  "designation": "iPhone 13 Pro",
  "description": "Smartphone Apple 128GB...",
  "imageid": 1234567890  // optional
}

// Response
{
  "predicted_class": 2280,
  "probabilities": {
    "2280": 0.87,
    "40": 0.08,
    "2403": 0.03,
    ...
  },
  "confidence": 0.87,
  "prediction_id": "pred_20260211_143022_xyz"
}
```

**`GET /metrics`** (Prometheus format)
```
# HELP rakuten_predictions_total Total predictions by class
# TYPE rakuten_predictions_total counter
rakuten_predictions_total{prdtypecode="2280"} 145
rakuten_predictions_total{prdtypecode="40"} 89

# HELP rakuten_prediction_latency_seconds Prediction latency
# TYPE rakuten_prediction_latency_seconds histogram
rakuten_prediction_latency_seconds_bucket{le="0.1"} 120
rakuten_prediction_latency_seconds_bucket{le="0.5"} 180

# HELP rakuten_text_len_chars Input text length
# TYPE rakuten_text_len_chars histogram
rakuten_text_len_chars_bucket{le="100"} 50
rakuten_text_len_chars_bucket{le="500"} 120
```

#### Model Loading Strategy
```python
# Lazy loading + caching
class ModelLoader:
    def __init__(self):
        self._model = None
        self._version = None
        self._last_check = None
    
    def get_model(self):
        # Check registry every 5 minutes
        if self._should_reload():
            self._load_from_registry()
        return self._model
```

---

### 3. ML Training (`src/models/train.py`)

#### Baseline Model: TF-IDF + LogisticRegression

```python
def train_model(dataset_run_id: str, week_number: int):
    """
    1. Load dataset from MLflow (train_week_N.parquet)
    2. Feature engineering:
       - TF-IDF on designation + description (max_features=5000)
       - Optional: basic image features (if image path exists)
    3. Train LogisticRegression (multi_class='multinomial', max_iter=1000)
    4. Evaluate on test set
    5. Log to MLflow:
       - Parameters: n_features, max_iter, C, class_weight
       - Metrics: accuracy, f1_macro, f1_weighted, per_class_f1
       - Artifacts: model, feature_names, class_names, confusion_matrix.png
    6. Register model to registry as "rakuten_classifier"
    7. Return model_run_id
    """
```

**MLflow Logging Structure:**
```
Experiment: rakuten_model_training
  Run: run_abc123
    Params:
      - dataset_run_id: xyz789
      - week_number: 2
      - n_features: 5000
      - max_iter: 1000
      - C: 1.0
      - class_weight: balanced
    Metrics:
      - accuracy: 0.82
      - f1_macro: 0.78
      - f1_weighted: 0.81
      - class_2280_f1: 0.89
      - class_40_f1: 0.76
      ...
    Artifacts:
      - model/ (sklearn model)
      - vectorizer.pkl
      - class_names.json
      - confusion_matrix.png
    Tags:
      - dataset_run_id: xyz789
      - week: 2
      - model_type: tfidf_logreg
```

---

### 4. Prefect Flows (`flows/`)

#### `pipeline_flow.py` - Training Pipeline

```python
@flow(name="rakuten-training-pipeline")
def training_pipeline(
    week_number: int = None,
    dataset_run_id: str = None
):
    """
    Full training pipeline flow
    """
    # Load dataset from MLflow
    dataset = load_dataset_from_mlflow(dataset_run_id)
    
    # Feature engineering
    features = engineer_features(dataset)
    
    # Train model
    model, metrics = train_model(features)
    
    # Log to MLflow
    run_id = log_model_to_mlflow(model, metrics, dataset_run_id)
    
    # Register model
    model_version = register_model(run_id, model_name="rakuten_classifier")
    
    # Promote to Production if metrics pass threshold
    if metrics['f1_weighted'] > 0.75:
        promote_model_to_production(model_name, model_version)
    
    return model_version
```

#### `monitor_and_retrain.py` - Drift Monitoring

```python
@flow(name="rakuten-monitor-retrain")
def monitor_and_retrain():
    """
    Daily monitoring flow with conditional retraining
    """
    # Load inference log
    inference_df = load_inference_log()
    
    # Generate Evidently report
    drift_metrics = generate_drift_report(
        reference_df=load_training_data(),
        current_df=inference_df
    )
    
    # Check thresholds
    if drift_metrics['dataset_drift'] > 0.3:
        logger.warning("Drift detected! Triggering retrain...")
        
        # Trigger retraining
        training_pipeline.apply_async()
        
        # Send notification
        send_slack_notification(f"Drift detected: {drift_metrics}")
    
    return drift_metrics
```

#### `prefect.yaml` - Deployment

```yaml
name: rakuten-mlops
version: 1.0

deployments:
  - name: monitor-and-retrain
    entrypoint: flows/monitor_and_retrain.py:monitor_and_retrain
    schedule:
      cron: "0 9 * * *"  # Daily at 09:00 UTC
      timezone: UTC
    work_pool:
      name: default
```

---

### 5. Streamlit Control Room (`streamlit_app/`)

#### Page: `Home.py`
- System architecture diagram
- Quick links to all services
- Current system status overview
- Recent activity feed

#### Page: `2_Infrastructure.py`
```python
# Service health checks
services = {
    "PostgreSQL": check_postgres_health(),
    "MLflow": check_mlflow_health(),
    "Airflow": check_airflow_health(),
    "FastAPI": check_api_health(),
    "Prometheus": check_prometheus_health(),
    "Grafana": check_grafana_health()
}

# Docker controls
if st.button("Start API Stack"):
    DockerManager.start_stack("docker-compose.api.yml")

if st.button("Restart Monitoring"):
    DockerManager.restart_stack("docker-compose.monitor.yml")
```

#### Page: `3_Dataset.py`
```python
# Query PostgreSQL for current state
state = get_current_state()
st.metric("Current Data Loaded", f"{state['percentage']}%")
st.metric("Total Products", state['total_rows'])

# Class distribution chart
dist = get_class_distribution()
st.bar_chart(dist)

# Sample viewer
st.dataframe(get_sample_products(limit=20))
```

#### Page: `4_Training.py`
```python
# MLflow experiments browser
experiments = MLflowManager.list_experiments()
selected_exp = st.selectbox("Experiment", experiments)

# Runs comparison table
runs = MLflowManager.search_runs(selected_exp)
st.dataframe(runs[['run_id', 'metrics.f1_weighted', 'params.week_number']])

# Trigger training
if st.button("Train New Model"):
    run_id = TrainingManager.trigger_prefect_flow(
        flow="training_pipeline",
        params={"week_number": state['week_number']}
    )
    st.success(f"Training started! Run ID: {run_id}")

# Promote model
if st.button("Promote to Production"):
    MLflowManager.transition_model_stage(
        name="rakuten_classifier",
        version=selected_version,
        stage="Production"
    )
```

#### Page: `5_Predictions.py`
```python
# Live prediction UI
designation = st.text_input("Product Name")
description = st.text_area("Description")
image = st.file_uploader("Image (optional)")

if st.button("Predict"):
    result = PredictionManager.predict(designation, description, image)
    
    st.metric("Predicted Class", result['predicted_class'])
    st.metric("Confidence", f"{result['confidence']:.2%}")
    
    # Top 5 probabilities
    st.bar_chart(result['top_5_probs'])

# Prediction history
history = PredictionManager.get_history(limit=50)
st.dataframe(history)
```

#### Page: `6_Monitoring.py`
```python
# Evidently report
if os.path.exists("reports/evidently/evidently_report.html"):
    st.components.v1.html(open(report_path).read(), height=800)

# Prometheus status
st.metric("Prometheus Status", check_prometheus())
st.link_button("Open Prometheus", "http://localhost:9090")

# Grafana dashboard
st.metric("Grafana Status", check_grafana())
st.link_button("Open Dashboard", "http://localhost:3000/d/rakuten")

# Drift metrics summary
drift_metrics = load_drift_metrics()
col1, col2, col3 = st.columns(3)
col1.metric("Dataset Drift", f"{drift_metrics['dataset_drift']:.2%}")
col2.metric("Feature Drift", f"{drift_metrics['feature_drift']:.2%}")
col3.metric("Prediction Drift", f"{drift_metrics['prediction_drift']:.2%}")
```

---

### 6. Monitoring Stack

#### Prometheus (`monitoring/prometheus.yml`)
```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'rakuten-api'
    static_configs:
      - targets: ['api:8000']
    metrics_path: '/metrics'
```

#### Grafana Dashboard Panels
1. **Predictions Over Time**: Time series of total predictions
2. **Predictions by Class**: Pie chart or bar chart
3. **Prediction Latency**: Histogram, P50/P95/P99
4. **Text Length Distribution**: Histogram
5. **Errors Rate**: Error responses over time
6. **Model Version**: Current production model version

---

## 🔄 Data Flow

### Training Flow (Weekly)
```
1. Airflow DAG runs (Monday 00:00)
   ├─ Load +3% data to PostgreSQL
   ├─ Generate balanced dataset
   ├─ Log dataset to MLflow
   └─ Trigger Prefect training flow

2. Prefect training_pipeline()
   ├─ Load dataset from MLflow
   ├─ Engineer features (TF-IDF)
   ├─ Train LogisticRegression
   ├─ Log model to MLflow
   ├─ Register to model registry
   └─ Promote to Production if metrics pass

3. FastAPI auto-reloads model
   └─ Serves new Production version
```

### Inference Flow (Real-time)
```
1. User/Streamlit → POST /predict
   ├─ API loads model from registry (cached)
   ├─ Preprocesses text
   ├─ Makes prediction
   ├─ Logs to inference_log.csv
   └─ Returns prediction

2. Prometheus scrapes /metrics
   └─ Updates Grafana dashboards

3. Daily Prefect monitor_and_retrain()
   ├─ Reads inference_log.csv
   ├─ Generates Evidently report
   ├─ Checks drift threshold
   └─ Triggers retrain if drift > 30%
```

---

## 🚀 Quick Start Commands

```bash
# 1. Start infrastructure (Postgres, MLflow, Airflow)
docker-compose -f docker-compose.infrastructure.yml up -d

# 2. Initialize database with 40% data
make init-db

# 3. Trigger initial training via Airflow
make trigger-dag  # or wait for Monday 00:00

# 4. Start API service
docker-compose -f docker-compose.api.yml up -d

# 5. Start monitoring stack
docker-compose -f docker-compose.monitor.yml up -d

# 6. Launch Streamlit Control Room
streamlit run streamlit_app/Home.py

# Access services:
# - Airflow: http://localhost:8080 (admin/admin)
# - MLflow: http://localhost:5000
# - API: http://localhost:8000/docs
# - Prometheus: http://localhost:9090
# - Grafana: http://localhost:3000 (admin/admin)
# - Streamlit: http://localhost:8501
```

---

## 📊 Success Metrics

### Technical Metrics
- ✅ All services healthy and accessible
- ✅ API response time < 500ms (P95)
- ✅ Model F1-score > 0.75
- ✅ Drift detection running daily
- ✅ Zero downtime during model updates

### Functional Metrics
- ✅ Can trigger training from Streamlit UI
- ✅ Can make predictions via UI and API
- ✅ Can view MLflow experiments and promote models
- ✅ Can monitor Grafana dashboards
- ✅ Can view Evidently drift reports

### Educational Metrics (School Project)
- ✅ Demonstrates full MLOps lifecycle
- ✅ Shows orchestration (Airflow + Prefect)
- ✅ Shows model registry and versioning
- ✅ Shows monitoring and observability
- ✅ Runnable on localhost (Docker Compose)

---

## 🔮 Future Enhancements (Out of Scope)

- Multi-model ensembles (TF-IDF + image CNN)
- A/B testing framework
- Kubernetes deployment
- CI/CD pipelines (GitHub Actions)
- Model performance regression tests
- Advanced feature engineering (BERT embeddings)
- Real-time streaming inference (Kafka)
- Multi-user authentication (OAuth)

---

## 📝 Notes

- **Simplicity First**: School project, keep it robust but simple
- **Localhost First**: Everything runs on Docker Compose
- **Modular Design**: Can swap components without breaking UI
- **Documentation**: Code should be self-documenting with clear comments
- **Testing**: Basic tests for critical paths, not exhaustive
- **No Secrets**: Use `.env` file, never commit credentials

---

**Last Updated**: 2026-02-11  
**Status**: 🚧 In Progress (Target Architecture)
