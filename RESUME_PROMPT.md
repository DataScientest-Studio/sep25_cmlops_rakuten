# Resume Prompt for Next Session

Copy this prompt to start a fresh conversation and continue the implementation.

---

## Context

I'm building a **Rakuten MLOps Control Room** (school certification project) with end-to-end ML pipeline: data loading, training, serving, monitoring, and a Streamlit UI.

**Current Status**: ✅ **75% Complete (6/8 Phases Done)**

**Repository**: `sep25_cmlops_rakuten`  
**Branch**: `fix/universal-pipeline-improvements`  
**Last Commit**: Phase 5 complete (Monitoring Stack)

---

## What's Been Built (Working & Tested)

### ✅ Phase 0: Documentation & Setup
- Complete architecture docs: `docs/TARGET_ARCHITECTURE.md`
- Implementation roadmap: `docs/IMPLEMENTATION_ROADMAP.md`
- Environment configs: `env.example.txt`, requirements files

### ✅ Phase 1: Docker Compose Refactor
- Modular stacks: `docker-compose.infrastructure.yml`, `docker-compose.api.yml`, `docker-compose.monitor.yml`
- Updated Makefile with stack-specific commands
- Dockerfile for FastAPI service

### ✅ Phase 2: FastAPI Service
- Complete serving layer: `src/serve/`
- Endpoints: `/health`, `/predict`, `/metrics`
- MLflow registry integration (lazy loading, caching)
- Prometheus metrics export
- Inference logging to `data/monitoring/inference_log.csv`

### ✅ Phase 3: Model Training
- Feature engineering: `src/features/text_features.py` (TF-IDF)
- Training pipeline: `src/models/train.py` (TF-IDF + LogisticRegression)
- Evaluation: `src/models/evaluate.py` (metrics, confusion matrix)
- Model registry helpers: `src/models/model_registry.py`
- Standalone script: `scripts/train_baseline_model.py`

### ✅ Phase 4: Prefect Flows
- Training pipeline: `flows/pipeline_flow.py`
- Monitoring & retraining: `flows/monitor_and_retrain.py`
- Drift detection: `src/monitoring/drift_detector.py` (Evidently AI)
- Deployment config: `flows/prefect.yaml` (daily schedule at 09:00 UTC)

### ✅ Phase 5: Monitoring Stack
- Prometheus config: `monitoring/prometheus.yml`
- Grafana provisioning: `grafana/provisioning/`
- Pre-built dashboard with 7 panels (predictions, latency, model version, etc.)
- Comprehensive documentation in `monitoring/README.md` and `grafana/README.md`

### ✅ Testing
- All phases tested and verified working
- Test guide: `TESTING_GUIDE.md`
- Commands work: `make start-full`, `make start-api`, `make start-monitor`

---

## What's Remaining (25%)

### 🚧 Phase 6: Streamlit UI (In Progress)

**What's Done:**
- Directory structure created: `streamlit_app/pages/`, `streamlit_app/managers/`, `streamlit_app/components/`
- Config files: `.streamlit/config.toml`, `.streamlit/secrets.toml.example`
- Docker manager: `streamlit_app/managers/docker_manager.py` (health checks, container control)

**What's Needed:**

**Managers** (4 remaining):
1. `mlflow_manager.py` - Query MLflow (experiments, runs, models, registry)
2. `prediction_manager.py` - Call API predictions, get history
3. `training_manager.py` - Trigger Prefect flows, Airflow DAGs
4. `database_manager.py` - Query PostgreSQL (dataset stats, class distribution)

**Pages** (6 needed):
1. `Home.py` - Landing page with system overview, architecture diagram, quick links
2. `pages/2_Infrastructure.py` - Service health cards, Docker controls, logs viewer
3. `pages/3_Dataset.py` - Dataset explorer (query DB), class distribution chart, sample viewer
4. `pages/4_Training.py` - MLflow experiments browser, trigger training, promote models
5. `pages/5_Predictions.py` - Live prediction form (text inputs), results display, history table
6. `pages/6_Monitoring.py` - Embed Evidently report, drift metrics, Grafana/Prometheus links

**Components** (optional helpers):
- `components/metrics_display.py` - Reusable metric cards
- `components/charts.py` - Chart helpers

### ⏳ Phase 7: Integration & Testing

- End-to-end system test with Streamlit
- Final documentation updates
- README.md overhaul with complete quick start
- Verification checklist

---

## Task for This Session

**Continue Phase 6: Complete Streamlit Control Room**

1. **Implement remaining managers** (4 files)
   - Follow pattern from `docker_manager.py`
   - Use `@st.cache_data` for performance
   - Handle errors gracefully with user-friendly messages

2. **Implement all 6 pages**
   - Reference architecture in `docs/TARGET_ARCHITECTURE.md`
   - Use managers for business logic (no direct API calls in pages)
   - Include error handling and loading states
   - Style consistently

3. **Test Streamlit app**
   - Run: `streamlit run streamlit_app/Home.py`
   - Verify all pages load without errors
   - Test key workflows: view health, make prediction, view experiments

4. **Phase 7: Integration testing**
   - Update `TESTING_GUIDE.md` with Streamlit tests
   - Update main `README.md` with Streamlit quick start
   - Final verification checklist

---

## Important Files to Reference

**Architecture & Planning:**
- `docs/TARGET_ARCHITECTURE.md` - Complete system design, UX mockups
- `docs/IMPLEMENTATION_ROADMAP.md` - Detailed phase breakdowns
- `TESTING_GUIDE.md` - Testing all implemented components

**Configuration:**
- `.env` - Environment variables (DATABASE, MLFLOW, etc.)
- `streamlit_app/.streamlit/secrets.toml.example` - Streamlit secrets template

**Existing Implementations to Reference:**
- `src/serve/routes.py` - API endpoints structure
- `src/models/train.py` - Training flow
- `flows/pipeline_flow.py` - Prefect flow structure
- `streamlit_app/managers/docker_manager.py` - Manager pattern

---

## Key Design Principles (Keep These)

1. **Managers pattern**: All business logic in `managers/`, pages only render UI
2. **Error handling**: User-friendly messages, no crashes on service unavailable
3. **Caching**: Use `@st.cache_data(ttl=X)` for API/DB calls
4. **Modular**: Each page independent, can work with services down
5. **Simple**: School project - prioritize working over perfect

---

## Quick Start Commands (For Testing)

```bash
# Start full stack
make start-full

# Train baseline model
python scripts/train_baseline_model.py --auto-promote

# Test API
curl http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"designation": "iPhone 13", "description": "Smartphone"}'

# Run Streamlit (once implemented)
streamlit run streamlit_app/Home.py
```

---

## Expected Deliverables

By end of session:

1. ✅ All 4 managers implemented
2. ✅ All 6 Streamlit pages working
3. ✅ Streamlit app runnable with `streamlit run streamlit_app/Home.py`
4. ✅ Updated `README.md` with Streamlit quick start
5. ✅ Git commit for Phase 6: "feat: complete Streamlit control room with 6 pages"
6. ✅ Git commit for Phase 7: "test: end-to-end integration and final documentation"
7. ✅ Final push to branch

---

## Git Checkpoint Pattern

Each phase gets a commit:

```bash
git add <files>
git commit -m "feat: <description>

Phase N Complete: <Name>

<bullet points of what was added>

Next Phase: <Next phase name>"

git push origin fix/universal-pipeline-improvements
```

---

## Success Criteria

✅ Streamlit app starts without errors  
✅ All 6 pages accessible via sidebar  
✅ Can view service health  
✅ Can make predictions via UI  
✅ Can view MLflow experiments  
✅ Can trigger training  
✅ Can view Grafana dashboards  
✅ README.md has complete "Quick Start" section  

---

## Start Here

**Prompt for AI Assistant:**

"I need to complete Phase 6 (Streamlit UI) and Phase 7 (Testing) for the Rakuten MLOps project.

Current status: 75% complete (6/8 phases done). Phase 6 is partially started with docker_manager.py implemented.

Please:
1. Implement remaining 4 managers following the docker_manager.py pattern
2. Implement all 6 Streamlit pages (Home + 5 pages in pages/)
3. Test the Streamlit app end-to-end
4. Update README.md with Streamlit quick start
5. Complete Phase 7 integration testing
6. Commit and push with appropriate messages

Reference `docs/TARGET_ARCHITECTURE.md` for UX design and `docs/IMPLEMENTATION_ROADMAP.md` for detailed tasks.

Let's prioritize working end-to-end over perfect polish (school project deadline)."

---

**Ready to Resume!** 🚀
