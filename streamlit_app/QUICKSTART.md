# Quick Start Guide

## 🚀 Get Started in 3 Steps

### Step 1: Setup (First time only)

```bash
cd streamlit_app
./setup.sh
```

This will:
- Create/verify virtual environment
- Install all dependencies
- Create `.env` configuration file

### Step 2: Start Docker Services

Make sure your Docker containers are running:

```bash
cd ..
docker-compose up -d
```

Verify services are running:
```bash
docker-compose ps
```

You should see:
- `rakuten_postgres` (PostgreSQL database)
- `rakuten_mlflow` (MLflow tracking server)
- `rakuten_api` (FastAPI prediction service)
- `rakuten_prometheus` (Metrics collection)
- `rakuten_grafana` (Monitoring dashboards)

### Step 3: Launch Control Room

```bash
cd streamlit_app
./run.sh
```

The app will open at `http://localhost:8501`

## 📊 Available Pages

### 🏠 Home
- System overview
- Container status
- Quick links

### 📊 Database Pipeline
- Data state monitoring
- Class distribution
- Sample products
- Load history

### 🔄 Ingestion & Training
- MLflow experiments
- Training runs & metrics
- Model artifacts
- Pipeline triggers

### 🚀 Model Promotion
- Model registry
- Stage transitions
- Prediction simulator
- API health

### 📈 Drift & Monitoring
- Grafana dashboards
- Prometheus metrics
- Inference logs
- System health

## 🔧 Configuration

Edit `.env` file if needed:

```bash
# For local access (Streamlit running outside Docker)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
MLFLOW_TRACKING_URI=http://localhost:5000
API_URL=http://localhost:8000
```

## 🐛 Troubleshooting

### Services not connecting?

**Check Docker containers:**
```bash
docker-compose ps
docker-compose logs <service_name>
```

**Test connections:**
```bash
# PostgreSQL
psql -h localhost -p 5432 -U rakuten_user -d rakuten_db

# MLflow
curl http://localhost:5000/health

# API
curl http://localhost:8000/health

# Prometheus
curl http://localhost:9090/-/healthy

# Grafana
curl http://localhost:3000/api/health
```

### Python dependencies missing?

```bash
cd streamlit_app
../.venv/bin/pip install -r ../requirements-streamlit.txt
```

### Port already in use?

Change Streamlit port:
```bash
../.venv/bin/streamlit run Home.py --server.port 8502
```

### Docker status showing all red?

Make sure Docker daemon is running and accessible:
```bash
docker ps
```

## 📚 More Information

See [README.md](README.md) for complete documentation.

## 🎯 Next Steps

1. **Load data**: Use Database Pipeline page to monitor data ingestion
2. **Train model**: Check Ingestion & Training page for MLflow experiments
3. **Test predictions**: Use Model Promotion page to test the API
4. **Monitor system**: Visit Drift & Monitoring page for system health

---

**Need help?** Check the main project documentation or Docker logs.
