# 🎓 MLOps Certification - Demo Script

**Project**: Rakuten Product Classification MLOps Pipeline  
**Presentation Time**: ~15-20 minutes  
**Audience**: MLOps Certification Evaluators

---

## 📋 Pre-Demo Checklist

**Before starting your presentation**, ensure:

```bash
# 1. Services are running
make start
sleep 30  # Wait for services to initialize

# 2. Database is initialized with 40% data
make init-db

# 3. Check all services are healthy
make check-health

# 4. Launch Streamlit (in separate terminal)
make run-streamlit
```

**Open these URLs in browser tabs**:
1. Streamlit: http://localhost:8501
2. MLflow: http://localhost:5000
3. API Docs: http://localhost:8000/docs
4. Grafana: http://localhost:3000 (login: admin/admin)

---

## 🎯 Demo Flow (5 Steps)

### **Step 1: Database & Data Versioning (3 min)**

**Navigate to**: Streamlit → Page 1 (📊 Database Pipeline)

**Show**:
- Current data state: 40% loaded (~33,966 products)
- Class distribution visualization
- Data loading history table
- Sample products

**Key Points to Mention**:
> "Our pipeline uses PostgreSQL with a complete audit trail. Every data load is tracked with:
> - Batch ID and timestamp
> - Percentage loaded (40% → 100%)
> - Complete history in `data_loads` table
> - Audit trail in `products_history` captures all changes
> 
> This means we can reproduce any training by querying the database state at a specific timestamp. No external versioning tools like DVC needed!"

**Demo Action**: Click "🔄 Refresh Data" to show live connection

---

### **Step 2: Incremental Data & Training (5 min)**

**Navigate to**: Streamlit → Page 2 (🔄 Ingestion & Training)

#### Part A: Load More Data (1 min)

**Action**: Click "📥 Load Next Data Increment (+3%)"

**While loading, explain**:
> "This button triggers the real Python script `loader.py` which:
> - Loads the next 3% of data (40% → 43%)
> - Updates the database with new products
> - Records the batch in the audit trail
> - All changes are tracked for reproducibility"

**Result**: Show success message with new percentage

#### Part B: Generate Balanced Dataset (1 min)

**Action**: Click "🔄 Generate Balanced Dataset"

**Explain**:
> "This creates a balanced training dataset using RandomOverSampling and logs it to MLflow:
> - Handles class imbalance
> - Saves as parquet file
> - Logs to MLflow experiment 'rakuten_dataset_versioning'
> - Includes metadata: class distribution, balancing strategy, timestamp"

**Result**: Show MLflow run ID

#### Part C: Train Model (3 min)

**Action**: 
1. Click the "⚙️ Training Config" popover
2. Show configuration options:
   - Max Features: 5000
   - C (Regularization): 1.0
   - Auto-promote: Check this box ✅
3. Click "🚀 Train Model"

**While training (~2-3 min), explain the architecture**:
> "The training pipeline:
> 1. Loads data from PostgreSQL (current 43% state)
> 2. Preprocesses text (clean, lowercase, remove special chars)
> 3. Trains TF-IDF + LogisticRegression
> 4. Logs everything to MLflow:
>    - All hyperparameters
>    - Metrics: accuracy, F1, precision, recall
>    - Artifacts: model, vectorizer, confusion matrix
>    - Data version: batch ID and percentage
> 5. Registers model in MLflow registry
> 6. Auto-promotes to Production if F1 > 0.70"

**Result**: Show training completion with run ID

**Switch to MLflow UI** (http://localhost:5000):
- Show experiments list
- Open latest run
- Show metrics (accuracy, F1, etc.)
- Show artifacts (model, plots)
- Show parameters logged
- Navigate to "Models" → "rakuten_classifier" → Show versions

---

### **Step 3: Model Promotion & Versioning (3 min)**

**Navigate to**: Streamlit → Page 3 (🚀 Model Promotion)

**Show**:
- Registered Models table with version and stage
- Current Production model (if auto-promoted)

**Key Points**:
> "MLflow Model Registry provides:
> - Versioned models (v1, v2, v3...)
> - Stage-based workflow: None → Staging → Production
> - Lineage: Each version links to its training run
> - Automatic or manual promotion
> 
> For reproducibility, given a model version, we can trace back to:
> - Exact hyperparameters
> - Training date/time
> - Data version (via database timestamp)
> - All metrics and artifacts"

**Demo Action** (if not auto-promoted):
1. Enter model name: `rakuten_classifier`
2. Enter version: `1`
3. Select stage: `Production`
4. Click "🚀 Promote Model"
5. Show success with confetti 🎉

#### Part B: Test Prediction

**Scroll down to Prediction Simulator**

**Action**:
1. Use example text or create custom:
   - Designation: "Chaise de bureau ergonomique"
   - Description: "Chaise confortable avec dossier réglable, accoudoirs..."
2. Click "🔮 Predict"

**Show**:
- Predicted class
- Confidence score
- Top 10 class probabilities
- Full response JSON

**Explain**:
> "The API:
> - Loads the Production model from MLflow
> - Applies same text preprocessing as training
> - Returns predictions with confidence scores
> - Logs every inference for monitoring
> - Exposes Prometheus metrics"

---

### **Step 4: API & Model Serving (2 min)**

**Show API Health Status** (bottom of Page 3):
- Status: healthy
- Model loaded: ✅
- Model version
- Timestamp

**Switch to API Docs** (http://localhost:8000/docs):
- Show available endpoints:
  - `GET /health` - Service health
  - `POST /predict` - Product classification
  - `GET /metrics` - Prometheus metrics
- Optionally: Execute a prediction via Swagger UI

**Key Points**:
> "The FastAPI service:
> - Automatically loads the Production model from MLflow
> - Reloads every 5 minutes (configurable)
> - Provides health checks for Kubernetes/monitoring
> - Logs all predictions to CSV for drift detection
> - Exposes Prometheus metrics for observability"

---

### **Step 5: Monitoring & Drift Detection (2 min)**

**Navigate to**: Streamlit → Page 4 (📈 Drift & Monitoring)

**Show**:
- Service status indicators
- Quick links to Prometheus and Grafana
- Inference logs table (if any predictions made)

**Open Grafana** (http://localhost:3000):
- Show pre-configured dashboards
- Navigate to "Rakuten MLOps" dashboard (if available)
- Show Prometheus metrics:
  - Prediction counts
  - API latency
  - Text length distribution

**Explain**:
> "Monitoring setup:
> - Prometheus scrapes metrics from the API every 15s
> - Grafana visualizes trends and alerts
> - Inference logs capture: input text, predictions, confidence, model version
> - Drift detection compares current input distribution vs training data
> 
> For production, we would add:
> - Alerting rules in Prometheus
> - Automated retraining triggers
> - A/B testing between model versions"

---

## 🎤 Key Messages to Emphasize

### 1. Complete Versioning Without External Tools

> "We don't need DVC or other external versioning tools because:
> - PostgreSQL audit trail (`data_loads`, `products_history`) tracks all data changes
> - MLflow tracks all experiments, parameters, and artifacts
> - Database timestamps enable exact state reproduction
> - Complete lineage: data version → experiment → model → predictions"

### 2. Reproducibility Story

> "To reproduce any training:
> 1. Get MLflow run_id
> 2. Query database: `SELECT * FROM products WHERE created_at <= training_timestamp`
> 3. Get hyperparameters from MLflow
> 4. Retrain with identical setup
> 
> Everything is traceable and reproducible!"

### 3. Production-Ready Components

> "This isn't just a demo - it includes production patterns:
> - Health checks for orchestration
> - Prometheus metrics for observability  
> - Automated model reloading
> - Inference logging for drift detection
> - Stage-based model promotion
> - Database audit trail for compliance"

### 4. Simplified Architecture

> "We removed orchestration complexity (Airflow/Prefect) to focus on core MLOps:
> - Manual triggering via Streamlit for demo clarity
> - In production, add scheduler or event-driven triggers
> - The pipeline components are production-ready
> - Easy to integrate with Kubernetes, Airflow, or Prefect later"

---

## 📊 Data to Show During Demo

Have these ready to reference:

### Database State
```bash
# Run before demo to get stats
make status
```

Expected output:
```json
{
  "current_percentage": 43.0,
  "total_rows": 36437,
  "last_load_date": "2026-02-14 10:30:00"
}
```

### Model Metrics (after training)
- Accuracy: ~0.75-0.80
- F1 Score: ~0.70-0.75
- Classes: 27
- Training samples: ~36,000

### Service Health
All services should show ✅:
- PostgreSQL
- MLflow  
- API
- Prometheus
- Grafana

---

## ❓ Anticipated Questions & Answers

### Q: "Why not use Airflow for orchestration?"

**A**: "For this demo, I focused on the core MLOps components. The pipeline is designed to be orchestration-agnostic - you can easily add Airflow, Prefect, or Kubernetes CronJobs. The Streamlit UI provides manual triggering for demonstration clarity, but in production, these same Python functions would be called by a scheduler."

### Q: "How do you handle data drift?"

**A**: "We log all inferences to CSV with input features and predictions. Drift detection compares current input distributions against training data using the Evidently library (in `src/monitoring/drift_detector.py`). Prometheus metrics track text length and prediction distributions over time. Grafana dashboards visualize these trends for alerting."

### Q: "Can you scale this pipeline?"

**A**: "Yes! Each component is containerized and independently scalable:
- PostgreSQL: Can use read replicas or managed service (RDS)
- MLflow: Backend is PostgreSQL, artifacts in S3 (MinIO)
- API: Stateless, can run multiple replicas behind load balancer
- Monitoring: Prometheus supports federation for large deployments"

### Q: "How do you ensure model reproducibility?"

**A**: "Three-level versioning:
1. **Data**: PostgreSQL audit trail with timestamps
2. **Code**: Git commits (linked via MLflow tags)
3. **Models**: MLflow registry with lineage to data + parameters

Given any model version, I can trace back to exact data state, code version, and hyperparameters."

### Q: "What about model testing before promotion?"

**A**: "The auto-promotion threshold (F1 > 0.70) is a simple example. In production, I'd add:
- Validation set performance checks
- A/B testing in Staging
- Business metric validation (precision/recall trade-offs)
- Model explainability checks
- Manual approval workflow for critical models"

### Q: "Why PostgreSQL instead of a data lake?"

**A**: "For this project size (~85K products), PostgreSQL is sufficient and provides:
- ACID guarantees
- Built-in audit trail (triggers)
- SQL query simplicity
- Easy local development

For larger scale, I'd migrate to data lake (S3/Delta Lake) with catalog (Hive/Glue), but keep PostgreSQL for metadata and audit trail."

---

## 🎬 Demo Timing Breakdown

| Section | Time | Activity |
|---------|------|----------|
| **Introduction** | 1 min | Project overview, architecture diagram |
| **Step 1: Data** | 3 min | Database state, versioning explanation |
| **Step 2: Training** | 5 min | Load data, generate dataset, train model |
| **Step 3: Promotion** | 3 min | Show registry, promote model, test prediction |
| **Step 4: Serving** | 2 min | API demo, health checks |
| **Step 5: Monitoring** | 2 min | Grafana dashboards, drift detection |
| **Q&A Buffer** | 4 min | Answer questions, show additional details |
| **Total** | 20 min | Complete presentation |

---

## 🔧 Troubleshooting During Demo

### If services are down:
```bash
make restart
sleep 30
make check-health
```

### If database is empty:
```bash
make init-db
```

### If Streamlit shows import errors:
```bash
make install-streamlit
```

### If training fails:
- Check MLflow is accessible: `curl http://localhost:5000/health`
- Check database has data: `make status`
- Check logs: `make logs-api`

### If API can't load model:
- Ensure model is promoted to Production in MLflow
- Check API logs: `make logs-api`
- Restart API: `docker compose restart api`

---

## 📸 Screenshots to Prepare (Optional)

For backup slides, prepare screenshots of:
1. Streamlit home page with service status
2. Database Pipeline page with data distribution
3. MLflow experiments page
4. MLflow model registry
5. API prediction response
6. Grafana dashboard

---

## 🎯 Success Criteria

After your demo, evaluators should understand:

✅ **Data Versioning**: How audit trail provides complete reproducibility  
✅ **Experiment Tracking**: How MLflow captures all training runs  
✅ **Model Registry**: How models are versioned and promoted  
✅ **Model Serving**: How API serves predictions with monitoring  
✅ **Monitoring**: How drift detection and metrics work  
✅ **Reproducibility**: How to recreate any training from scratch

---

## 📝 Post-Demo: What to Highlight in Report

In your written report, emphasize:

1. **Architecture Decisions**
   - Why PostgreSQL for audit trail
   - Why no external orchestrator (for demo simplicity)
   - Why MLflow over alternatives

2. **MLOps Best Practices Demonstrated**
   - Experiment tracking
   - Model versioning and registry
   - Automated testing (metric thresholds)
   - Model promotion workflow
   - Inference logging
   - Monitoring and alerting

3. **Scalability Considerations**
   - Each component can scale independently
   - Stateless API design
   - Use of object storage (MinIO/S3)

4. **Production Gaps & Next Steps**
   - Add automated orchestration
   - Implement proper CI/CD
   - Add model performance monitoring
   - Implement online learning pipeline

---

## 🚀 Final Checklist Before Presentation

- [ ] All services running (`make check-health`)
- [ ] Database initialized with 40% data
- [ ] Browser tabs open (Streamlit, MLflow, API, Grafana)
- [ ] Streamlit running without errors
- [ ] At least one model trained and in registry
- [ ] API health check returns "healthy"
- [ ] You understand the complete data flow
- [ ] You can answer questions about versioning strategy
- [ ] You have backup slides ready (optional)
- [ ] You're confident and ready! 💪

---

**Good luck with your certification! 🎓**

You've built a solid MLOps pipeline that demonstrates production-ready practices. Be proud of the work and confidently explain your design decisions!
