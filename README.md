# Rakuten MLOps Pipeline - Certification Project

A complete MLOps pipeline for product classification with incremental data loading, experiment tracking, model serving, and monitoring.

**Project**: DataScientest MLOps Certification (September 2025)

---

## 🎯 Overview

This project demonstrates a production-ready MLOps pipeline featuring:

- **Incremental Data Pipeline**: PostgreSQL database with audit trail (40% → 100% data progression)
- **Experiment Tracking**: MLflow for experiment versioning and model registry
- **Model Serving**: FastAPI service with health monitoring
- **Monitoring Stack**: Prometheus metrics + Grafana dashboards
- **Interactive UI**: Streamlit control room for pipeline management
- **Complete Versioning**: Database audit trail tracks all data changes for reproducibility

### Key MLOps Capabilities Demonstrated

✅ **Data Versioning**: Database tracks every data load with timestamps and batch IDs  
✅ **Experiment Tracking**: MLflow logs all training runs, parameters, and metrics  
✅ **Model Registry**: Versioned models with stage promotion (Staging → Production)  
✅ **Model Serving**: REST API with automatic model reloading  
✅ **Monitoring**: Prometheus metrics + Grafana dashboards for drift detection  
✅ **Reproducibility**: Complete lineage from data version → training → model → predictions

---

## 🏗️ Architecture

```
┌─────────────────┐
│  Streamlit UI   │  ← Interactive control room
└────────┬────────┘
         │
    ┌────▼────────────────────────────────┐
    │  Pipeline Orchestration (Manual)    │
    └────┬────────────────────────────────┘
         │
    ┌────▼──────┐  ┌───────────┐  ┌──────────┐
    │PostgreSQL │  │  MLflow   │  │  MinIO   │
    │ (+ Audit) │  │ Tracking  │  │ Storage  │
    └────┬──────┘  └─────┬─────┘  └────┬─────┘
         │               │              │
    ┌────▼───────────────▼──────────────▼─────┐
    │     FastAPI Model Serving (API)         │
    └────┬─────────────────────────────────────┘
         │
    ┌────▼──────────┐  ┌───────────┐
    │  Prometheus   │  │  Grafana  │
    └───────────────┘  └───────────┘
```

**Services**:
- **PostgreSQL**: Data storage with complete audit trail
- **MinIO**: S3-compatible object storage for MLflow artifacts
- **MLflow**: Experiment tracking and model registry
- **FastAPI**: Model serving API with Prometheus metrics
- **Prometheus**: Metrics collection and alerting
- **Grafana**: Visualization dashboards
- **Streamlit**: Interactive control room UI

---

## 🚀 Quick Start

### Prerequisites

- Docker Desktop running
- Training data in `data/raw/` (X_train.csv, Y_train.csv, X_test.csv)
- Python 3.11+ (for local Streamlit)

### 1. Initial Setup

```bash
# Clone and enter repository
cd sep25_cmlops_rakuten

# Setup environment and directories
make setup

# Edit .env file with your credentials (optional, defaults are fine for local)
```

### 2. Start All Services

```bash
# Start complete stack: PostgreSQL, MLflow, MinIO, API, Monitoring
make start

# Wait ~30 seconds for services to initialize
```

**Service URLs**:
- MLflow UI: http://localhost:5000
- API Docs: http://localhost:8000/docs
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (admin/admin)

### 3. Initialize Database (40% of data)

```bash
# Load initial 40% of training data into PostgreSQL
make init-db

# ✅ This loads ~33,966 products with complete audit trail
```

### 4. Launch Streamlit Control Room

```bash
# Install Streamlit dependencies
make install-streamlit

# Launch the control room
make run-streamlit
```

Open http://localhost:8501 in your browser.

---

## 📊 Using the Streamlit Control Room

The Streamlit interface provides 4 pages for the complete ML pipeline:

### Page 1: 📊 Database Pipeline
- View current data loading status (40% → 100%)
- Monitor class distribution
- Track data loading history
- View sample products

### Page 2: 🔄 Ingestion & Training
- **Load More Data**: Click button to load next 3% increment
- **Generate Balanced Dataset**: Create training dataset with oversampling
- **Train Model**: Configure and train TF-IDF + LogisticRegression
- View MLflow experiments and training metrics
- Explore model artifacts

### Page 3: 🚀 Model Promotion & Prediction
- View registered models and versions
- **Promote Models**: Move models between stages (Staging → Production)
- **Test Predictions**: Send test requests to the API
- Monitor API health

### Page 4: 📈 Drift & Monitoring
- View Grafana dashboards
- Check Prometheus metrics
- Analyze inference logs
- Monitor system health

---

## 📋 Common Commands

```bash
# === Infrastructure ===
make start              # Start all services
make stop               # Stop all services
make restart            # Restart all services
make ps                 # Show running containers
make check-health       # Check service health

# === Data Pipeline ===
make init-db            # Initialize with 40% data
make load-data          # Load next +3% increment
make status             # Show current data status
make generate-dataset   # Generate balanced dataset

# === Model Training ===
make train-model        # Train model from database
make train-model-promote # Train + auto-promote if F1 > 0.70

# === Monitoring ===
make logs               # View all logs
make logs-api           # View API logs
make logs-mlflow        # View MLflow logs
make test-api           # Test API endpoints

# === Development ===
make run-streamlit      # Launch Streamlit UI
make install-local      # Install Python dependencies
make shell-postgres     # Open PostgreSQL shell

# === Quick Demo ===
make demo               # Complete setup for demo (setup + start + init-db)
```

---

## 🔄 Complete Workflow Example

### Scenario: Train a Model on 40% Data, Promote, and Predict

```bash
# 1. Start services and initialize database
make demo

# 2. Launch Streamlit
make run-streamlit

# 3. In Streamlit (Page 2 - Ingestion & Training):
#    - Click "Generate Balanced Dataset"
#    - Click "Train Model" (configure as needed)
#    - Wait for training to complete (~2-3 minutes)

# 4. In Streamlit (Page 3 - Model Promotion):
#    - View the new model version
#    - Promote to "Production"
#    - Test prediction with sample text

# 5. View in MLflow UI (http://localhost:5000):
#    - Check experiment runs
#    - View metrics and artifacts
#    - Compare model versions

# 6. Monitor API (Page 4 - Drift Monitoring):
#    - View inference logs
#    - Check Grafana dashboards
#    - Monitor prediction distribution
```

---

## 🗄️ Data Versioning & Reproducibility

### How Versioning Works

The pipeline uses **PostgreSQL audit tables** for complete data lineage:

```sql
-- data_loads: Tracks each data loading batch
- batch_name (e.g., "week_1", "week_2")
- percentage (40%, 43%, 46%...)
- total_rows
- started_at, completed_at
- metadata (JSON with context)

-- products_history: Audit trail of all changes
- operation_type (INSERT/UPDATE)
- operation_date
- load_batch_id (links to data_loads)
- product details (designation, description, etc.)
```

### To Reproduce a Training

Given an MLflow run_id, you can reproduce the exact training:

```python
# 1. Get training metadata from MLflow
run = mlflow.get_run(run_id)
training_date = run.info.start_time

# 2. Query database for exact data state at that time
SELECT * FROM products WHERE created_at <= training_date

# 3. Use same hyperparameters from MLflow
params = run.data.params  # max_features, C, ngram_range, etc.

# 4. Retrain with identical setup
```

**No external versioning tools needed!** The database audit trail provides complete lineage.

---

## 📈 Model Training

### TF-IDF + Logistic Regression Pipeline

```python
# What gets trained:
- Text Preprocessing (clean, lowercase, remove special chars)
- TF-IDF Vectorization (max_features=5000, ngram_range=(1,2))
- Logistic Regression (C=1.0, max_iter=1000)

# Tracked in MLflow:
- All hyperparameters
- Metrics: accuracy, F1, precision, recall, per-class metrics
- Artifacts: model pipeline, TF-IDF vectorizer, confusion matrix
- Data version: batch_id and percentage
```

### Training Methods

**Option 1: Via Streamlit** (Recommended for demo)
- Navigate to Page 2
- Click "Train Model"
- Configure parameters in popover
- Watch progress in real-time

**Option 2: Via Command Line**
```bash
# Train with defaults
make train-model

# Train with auto-promotion (if F1 > 0.70)
make train-model-promote

# Or directly with custom parameters
python scripts/train_baseline_model.py --max-features 10000 --C 0.5 --auto-promote
```

---

## 🔍 Monitoring & Drift Detection

### Prometheus Metrics

The API exposes metrics for monitoring:

```
rakuten_predictions_total - Total number of predictions
rakuten_prediction_latency_seconds - Prediction latency
rakuten_text_len_chars - Input text length distribution
rakuten_model_version - Current model version
```

### Grafana Dashboards

Pre-configured dashboards available at http://localhost:3000:

- **Model Performance**: Prediction counts, latency, error rates
- **Data Drift**: Input text length distribution over time
- **System Health**: API uptime, resource usage

### Inference Logging

All predictions are logged to `data/monitoring/inference_log.csv`:

```csv
timestamp,designation,description,predicted_class,confidence,model_version
2026-02-14 10:30:15,"Product title","Description",10,0.89,1
```

View logs in Streamlit (Page 4) for drift analysis.

---

## 🧹 Cleanup

```bash
# Stop services (keep data)
make stop

# Complete cleanup (deletes all data and volumes)
make clean

# Remove backup files
rm -f backup_*.sql
```

---

## 📚 Project Structure

```
sep25_cmlops_rakuten/
├── src/
│   ├── data/               # Data loading and preprocessing
│   │   ├── schema.sql      # Database schema with audit trail
│   │   ├── loader.py       # Incremental data loader
│   │   ├── dataset_generator.py  # Balanced dataset creation
│   │   └── db_init.py      # Database initialization
│   ├── features/           # Feature extraction
│   │   └── text_features.py
│   ├── models/             # Model training and evaluation
│   │   ├── train.py
│   │   ├── evaluate.py
│   │   └── model_registry.py
│   ├── serve/              # FastAPI serving
│   │   ├── main.py
│   │   ├── routes.py
│   │   ├── model_loader.py
│   │   └── inference_logger.py
│   └── monitoring/         # Drift detection
│       └── drift_detector.py
├── streamlit_app/          # Interactive UI
│   ├── Home.py
│   ├── pages/              # 4 pipeline pages
│   ├── managers/           # Pipeline executors
│   └── components/         # Reusable components
├── scripts/
│   └── train_baseline_model.py  # Training script
├── monitoring/             # Prometheus config
├── grafana/                # Grafana dashboards
├── docker-compose.yml      # Simplified stack (no orchestration)
├── Makefile                # Convenient commands
└── requirements.txt        # Python dependencies
```

---

## 🎓 Certification Presentation Points

### What This Project Demonstrates

1. **Data Management**
   - Incremental loading with audit trail
   - Complete data lineage and reproducibility
   - Database-based versioning (no external tools needed)

2. **Experiment Tracking**
   - MLflow for all experiments
   - Parameterized runs
   - Artifact storage in MinIO

3. **Model Registry**
   - Versioned models
   - Stage-based promotion workflow
   - Automated promotion based on metrics

4. **Model Serving**
   - REST API with FastAPI
   - Health checks and monitoring
   - Automatic model reloading

5. **Monitoring & Observability**
   - Prometheus metrics collection
   - Grafana visualization
   - Inference logging for drift detection

6. **Reproducibility**
   - All training runs are reproducible via MLflow run_id
   - Database audit trail enables exact data state recovery
   - Hyperparameters and artifacts fully tracked

---

## 🐛 Troubleshooting

| Problem | Solution |
|---------|----------|
| Services don't start | `make check-health` then `make restart` |
| PostgreSQL not accessible | `make logs-postgres` then `docker compose restart postgres` |
| API not responding | Check if model exists in MLflow registry |
| Streamlit import errors | `make install-streamlit` |
| "No data in database" error | Run `make init-db` first |

**Complete reset:**
```bash
make stop && make clean
make demo
```

---

## 📞 Support

For questions about this MLOps certification project:
- Review the code documentation in `src/`
- Check Makefile commands with `make help`
- View logs with `make logs`

---

**🎓 DataScientest MLOps Certification - September 2025**
