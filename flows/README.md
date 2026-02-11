# Prefect Flows

Orchestration flows for training and monitoring.

## Flows

### 1. Training Pipeline (`pipeline_flow.py`)

Orchestrates model training from dataset to model registration.

**Flow:** `training_pipeline`

**Steps:**
1. Load dataset (from MLflow or database)
2. Train TF-IDF + LogisticRegression model
3. Log metrics and artifacts to MLflow
4. Register model to Model Registry
5. (Optional) Auto-promote to Production if F1 > threshold

**Usage:**

```python
from flows.pipeline_flow import training_pipeline

result = training_pipeline(
    dataset_run_id=None,  # Load from database
    week_number=1,
    max_features=5000,
    C=1.0,
    auto_promote_threshold=0.75
)
```

**Command Line:**

```bash
python flows/pipeline_flow.py
```

---

### 2. Monitoring & Retraining (`monitor_and_retrain.py`)

Daily monitoring flow that checks for data drift and triggers retraining if threshold exceeded.

**Flow:** `monitor_and_retrain`

**Steps:**
1. Load inference log from production API
2. Load reference data (training data)
3. Generate Evidently drift report
4. Check drift score against threshold
5. Trigger retraining if drift detected
6. Send notification (log/Slack/email)

**Usage:**

```python
from flows.monitor_and_retrain import monitor_and_retrain

result = monitor_and_retrain(
    inference_log_path="./data/monitoring/inference_log.csv",
    force_retrain=False
)
```

**Command Line:**

```bash
python flows/monitor_and_retrain.py
```

---

## Prefect Deployment

### Prerequisites

```bash
# Install Prefect
pip install prefect

# Start Prefect server (local)
prefect server start
```

### Deploy Flows

```bash
# Navigate to project root
cd /path/to/sep25_cmlops_rakuten

# Deploy all flows
prefect deploy --all

# Or deploy specific flow
prefect deploy -n monitor-and-retrain
```

### View Deployments

```bash
# List deployments
prefect deployment ls

# View deployment details
prefect deployment inspect rakuten-mlops/monitor-and-retrain
```

### Trigger Flows

```bash
# Trigger training pipeline
prefect deployment run rakuten-mlops/training-pipeline

# Trigger monitoring flow
prefect deployment run rakuten-mlops/monitor-and-retrain

# Trigger with parameters
prefect deployment run rakuten-mlops/training-pipeline \
  --param max_features=10000 \
  --param C=0.5
```

### Monitor Flows

Open Prefect UI:

```bash
# UI is at http://localhost:4200
open http://localhost:4200
```

---

## Scheduling

The monitoring flow is scheduled to run **daily at 09:00 UTC**.

Edit `prefect.yaml` to change the schedule:

```yaml
schedule:
  cron: "0 9 * * *"  # Daily at 09:00 UTC
  timezone: UTC
```

---

## Configuration

### Environment Variables

```bash
# MLflow
MLFLOW_TRACKING_URI=http://localhost:5000

# Inference Log
INFERENCE_LOG_PATH=./data/monitoring/inference_log.csv

# Drift Threshold
DRIFT_THRESHOLD=0.3  # Trigger retrain if drift > 30%

# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=rakuten_db
POSTGRES_USER=rakuten_user
POSTGRES_PASSWORD=rakuten_pass
```

### Drift Thresholds

Edit `src/monitoring/thresholds.py`:

```python
DATASET_DRIFT_THRESHOLD = 0.3  # 30%
MIN_SAMPLES_FOR_DRIFT = 100
```

---

## Integration with Airflow

The Airflow DAG (`dags/weekly_ml_pipeline_dag.py`) can trigger Prefect flows after dataset generation:

```python
def trigger_prefect_training(**context):
    """Trigger Prefect training flow"""
    import requests
    
    response = requests.post(
        "http://localhost:4200/api/deployments/<deployment-id>/create_flow_run",
        json={"parameters": {"week_number": context['week']}}
    )
    return response.json()
```

---

## Troubleshooting

### Flow Fails: "No module named 'src'"

Make sure to run from project root:

```bash
cd /path/to/sep25_cmlops_rakuten
python flows/pipeline_flow.py
```

### Drift Detection Fails: "Insufficient samples"

Increase inference volume or lower `MIN_SAMPLES_FOR_DRIFT`:

```python
# src/monitoring/thresholds.py
MIN_SAMPLES_FOR_DRIFT = 50  # Lower threshold
```

### Retraining Not Triggered

Check drift score in logs. If below threshold, retraining won't trigger.

Force retrain:

```python
monitor_and_retrain(force_retrain=True)
```

---

## Next Steps

1. Start Prefect server: `prefect server start`
2. Deploy flows: `prefect deploy --all`
3. View UI: `open http://localhost:4200`
4. Trigger training: `prefect deployment run rakuten-mlops/training-pipeline`
5. Wait for daily monitoring (or trigger manually)
