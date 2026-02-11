# Quick Start with Virtual Environment

**For colleagues**: Follow these steps to get the project running locally using the virtual environment.

---

## Prerequisites

- Docker Desktop running
- Python 3.11+ installed
- Data files in `data/raw/` (or use DVC: `dvc pull`)

---

## 1. Setup Virtual Environment (One-Time)

```bash
# Activate existing venv
source .venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies (with binary psycopg2 to avoid pg_config issues)
pip install --only-binary :all: psycopg2-binary
pip install -r requirements.txt

# Verify installation
pip list | grep -E "(mlflow|sklearn|fastapi|streamlit)"
```

**Expected output**:
```
fastapi                            0.121.3
mlflow                             2.10.2
scikit-learn                       1.5.2
streamlit                          (if installed)
```

---

## 2. Start Infrastructure

```bash
# Start Postgres, MLflow, MinIO, Airflow
make start

# Wait 60 seconds for services to initialize
sleep 60

# Check health
make check-health
# Should show: PostgreSQL OK, MLflow OK, Airflow OK

# Initialize database (40% data)
make init-db
```

**Access UIs**:
- Airflow: http://localhost:8080 (admin/admin)
- MLflow: http://localhost:5000
- MinIO: http://localhost:9001 (minio_admin/minio_password)

---

## 3. Train Baseline Model

```bash
# Ensure venv is activated
source .venv/bin/activate

# Set MLflow URI
export MLFLOW_TRACKING_URI=http://localhost:5000

# Train model (takes 2-5 minutes)
python scripts/train_baseline_model.py --auto-promote

# Expected output:
# ================================================================================
# ✅ Baseline Model Training Complete!
#    MLflow Run ID: abc123...
#    MLflow UI: http://localhost:5000
# ================================================================================
```

**Verify in MLflow**:
1. Open http://localhost:5000
2. Click "Experiments" → "rakuten_model_training" (should show 1 run)
3. Click "Models" → "rakuten_classifier" (should show version 1 in Production)

---

## 4. Run API Locally (Alternative to Docker)

If Docker API build fails (network timeout), run locally:

```bash
# Install API dependencies
source .venv/bin/activate
pip install -r requirements-api.txt

# Start API
cd src/serve
export MLFLOW_TRACKING_URI=http://localhost:5000
export MODEL_NAME=rakuten_classifier
export MODEL_STAGE=Production
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Test in another terminal
curl http://localhost:8000/health
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"designation": "iPhone 13", "description": "Smartphone Apple"}'
```

**OR** use Docker (if build succeeds):
```bash
make start-api
```

---

## 5. Start Monitoring

```bash
# Start Prometheus + Grafana
make start-monitor

# Generate test predictions (creates metrics)
for i in {1..20}; do
  curl -s -X POST http://localhost:8000/predict \
    -H "Content-Type: application/json" \
    -d "{\"designation\": \"Product $i\", \"description\": \"Test product\"}" \
    > /dev/null
  echo "Prediction $i sent"
done

# View monitoring
open http://localhost:9090  # Prometheus
open http://localhost:3000  # Grafana (login: admin/admin)
```

---

## 6. Run Streamlit UI (When Implemented)

```bash
source .venv/bin/activate
pip install -r requirements-streamlit.txt

# Create secrets file
cp streamlit_app/.streamlit/secrets.toml.example streamlit_app/.streamlit/secrets.toml
# Edit secrets.toml with your service URLs

# Run Streamlit
streamlit run streamlit_app/Home.py

# Opens automatically at http://localhost:8501
```

---

## Common Issues & Solutions

### Issue: `ModuleNotFoundError` when running scripts

**Solution**: Always activate venv first
```bash
source .venv/bin/activate
```

### Issue: `psycopg2` build fails with "pg_config not found"

**Solution**: Use pre-built binary
```bash
pip install --only-binary :all: psycopg2-binary
```

### Issue: API Docker build timeout

**Solution A**: Run API locally (see step 4)

**Solution B**: Use cached Docker layers
```bash
export DOCKER_BUILDKIT=1
docker build --build-arg PIP_DEFAULT_TIMEOUT=300 -f src/serve/Dockerfile .
```

### Issue: Model not loading in API

**Solution**: Ensure model is trained and in Production stage
```bash
# Check MLflow
open http://localhost:5000
# Navigate to Models → rakuten_classifier

# If no model, train one
python scripts/train_baseline_model.py --auto-promote
```

### Issue: Ports already in use

**Solution**: Stop conflicting services
```bash
# Find what's using the port
lsof -i :5000  # MLflow
lsof -i :8000  # API
lsof -i :8080  # Airflow

# Stop all Docker services
make stop
# OR stop specific stack
make stop-api
```

---

## Environment Variables

Create `.env` if it doesn't exist:
```bash
cp env.example.txt .env
```

**Key variables**:
```bash
# MLflow
MLFLOW_TRACKING_URI=http://localhost:5000

# API
MODEL_NAME=rakuten_classifier
MODEL_STAGE=Production

# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=rakuten_db
POSTGRES_USER=rakuten_user
POSTGRES_PASSWORD=rakuten_pass
```

**For scripts**: Export before running
```bash
export MLFLOW_TRACKING_URI=http://localhost:5000
python scripts/train_baseline_model.py
```

---

## Full Stack Commands

```bash
# Start everything (infrastructure + API + monitoring)
make start-full

# Check all services
make check-health

# View all containers
docker ps

# Stop everything
make stop-full
```

---

## Testing Workflow

**Complete Test (15 minutes)**:

```bash
# 1. Setup
source .venv/bin/activate
make start
sleep 60
make init-db

# 2. Train
export MLFLOW_TRACKING_URI=http://localhost:5000
python scripts/train_baseline_model.py --auto-promote

# 3. Start services
make start-api  # or run locally if build fails
make start-monitor

# 4. Test prediction
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"designation": "iPhone 13", "description": "Smartphone"}'

# 5. View monitoring
open http://localhost:5000  # MLflow
open http://localhost:9090  # Prometheus
open http://localhost:3000  # Grafana

# 6. Success! ✅
```

---

## Help & Documentation

- **Architecture**: `docs/TARGET_ARCHITECTURE.md`
- **Implementation**: `docs/IMPLEMENTATION_ROADMAP.md`
- **Testing**: `TESTING_GUIDE.md`
- **Resume Work**: `RESUME_PROMPT.md`
- **Issues**: `TEST_RESULTS_PHASE_6.md`

---

**Questions?** Check the documentation files above or review git commit messages for context.

**Ready to continue?** See `RESUME_PROMPT.md` for Phase 6 (Streamlit UI) continuation.
