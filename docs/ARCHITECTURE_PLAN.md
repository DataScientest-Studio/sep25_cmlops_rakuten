# Incremental Data Pipeline Architecture

## Overview

Create a PostgreSQL database in Docker that simulates time-evolving data, starting with 40% of CSV/image data and incrementally adding 3% weekly via Apache Airflow orchestration until reaching 100%. Each week, balanced training datasets are generated from the database and versioned in MLflow for reproducible model training. The system includes complete audit trails to track data evolution over time.

## Key Architectural Principles

This architecture follows a **simplified data-centric MLOps approach** where:

1. **Raw Data is Fixed**: CSV files and images are immutable source data stored locally
2. **Database Simulates Incremental Growth**: PostgreSQL tracks the evolution of training data (40% → 100%)
3. **Test Data Remains Separate**: `X_test.csv` is loaded once as a DataFrame, versioned in MLflow (not in database)
4. **Training Datasets are Versioned in MLflow**: Balanced datasets are saved as parquet files and tracked in MLflow
5. **Full Lineage via MLflow**: All datasets and models are tracked in MLflow with clear lineage

### Pipeline Flow

**Raw CSV (40% → 100%) → PostgreSQL → Balanced Dataset → MLflow → Model**

- **Training data** evolves incrementally in PostgreSQL (simulates production growth)
- **Test data** stays fixed in `X_test.csv` (loaded to DataFrame, versioned in MLflow once)
- **Balanced datasets** are generated weekly and versioned in MLflow
- **Models** are trained from MLflow-versioned datasets and logged back to MLflow

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                Raw Data (Fixed, Local)                      │
│  - data/raw/X_train.csv, Y_train.csv                        │
│  - data/raw/X_test.csv (loaded to DataFrame, versioned)     │
│  - data/raw/images/ (filesystem)                            │
└─────────────┬───────────────────────────────────────────────┘
              │ initial load (40%)
              ▼
┌─────────────────────────────────────────────────────────────┐
│          PostgreSQL Database (Docker)                       │
│  - products (current state, 40% → 100%)                     │
│  - labels (productid → prdtypecode)                         │
│  - products_history (audit trail)                           │
│  - data_loads (batch tracking)                              │
└─────────────┬───────────────────────────────────────────────┘
              │ weekly increment
              ▲
┌─────────────┴───────────────────────────────────────────────┐
│         Apache Airflow (Docker Compose)                     │
│  DAG: weekly_ml_pipeline                                    │
│  Task 1: Increment data (40% → 43% → 46%...)                │
│  Task 2: Generate balanced dataframe (random oversampling)  │
│  Task 3: Log dataset to MLflow                              │
│  Task 4: Trigger model training                             │
└─────────────────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────┐
│         Balanced Dataset Generation                         │
│  - Query PostgreSQL for current data                        │
│  - Apply random oversampling for class balance              │
│  - Save as train_week_N.parquet                             │
│  - Verify balanced distribution                             │
└─────────────┬───────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────┐
│              MLflow Tracking Server (Docker)                │
│  Artifacts (local storage):                                 │
│  - test_df.parquet (fixed, versioned once)                  │
│  - train_week_1.parquet, train_week_2.parquet, ...          │
│  - trained models                                           │
│  Tracking:                                                  │
│  - Dataset runs (parameters, metrics, artifacts)            │
│  - Training runs (hyperparameters, metrics, models)         │
│  - Lineage: dataset_run_id → model_run_id                   │
└─────────────┬───────────────────────────────────────────────┘
              │ load versioned dataset
              ▼
┌─────────────────────────────────────────────────────────────┐
│              Model Training Pipeline                        │
│  - Load train_week_N.parquet from MLflow                    │
│  - Train model                                              │
│  - Log model, metrics to MLflow                             │
│  - Evaluate on test_df.parquet                              │
└─────────────────────────────────────────────────────────────┘
```

## Components Breakdown

### 1. Docker Infrastructure

**docker-compose.yml** will define:
- **PostgreSQL container** (postgres:15-alpine)
  - Persistent volume for database data
  - Exposed port 5432
  - Environment variables for credentials
  - Health checks
  
- **Airflow containers** (apache/airflow:2.8.0)
  - Webserver, scheduler, worker
  - Postgres as metadata backend
  - Persistent volumes for DAGs and logs
  - Network connectivity to PostgreSQL

### 2. Database Schema (Simplified)

**PostgreSQL tables:**

```sql
-- Main products table (current state)
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    designation TEXT,
    description TEXT,
    productid BIGINT UNIQUE NOT NULL,
    imageid BIGINT,
    image_path TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_products_productid ON products(productid);

-- Labels/targets table
CREATE TABLE labels (
    id SERIAL PRIMARY KEY,
    productid BIGINT UNIQUE NOT NULL,
    prdtypecode INTEGER NOT NULL
);

CREATE INDEX idx_labels_productid ON labels(productid);

-- Audit trail for products
CREATE TABLE products_history (
    history_id SERIAL PRIMARY KEY,
    product_id INTEGER,
    productid BIGINT NOT NULL,
    designation TEXT,
    description TEXT,
    imageid BIGINT,
    image_path TEXT,
    operation_type VARCHAR(10) NOT NULL,  -- 'INSERT' or 'UPDATE'
    operation_date TIMESTAMP DEFAULT NOW(),
    load_batch_id INTEGER
);

CREATE INDEX idx_products_history_date ON products_history(operation_date);
CREATE INDEX idx_products_history_batch ON products_history(load_batch_id);

-- Track each data loading batch
CREATE TABLE data_loads (
    id SERIAL PRIMARY KEY,
    batch_name VARCHAR(100) UNIQUE,
    percentage DECIMAL(5,2) NOT NULL,
    total_rows INTEGER NOT NULL,
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    status VARCHAR(20) NOT NULL,  -- 'running', 'completed', 'failed'
    metadata JSONB
);

CREATE INDEX idx_data_loads_date ON data_loads(completed_at);

-- Trigger to automatically populate products_history
CREATE OR REPLACE FUNCTION audit_products()
RETURNS TRIGGER AS $$
DECLARE
    current_batch_id INTEGER;
BEGIN
    SELECT id INTO current_batch_id 
    FROM data_loads 
    WHERE status = 'running'
    ORDER BY started_at DESC 
    LIMIT 1;
    
    IF (TG_OP = 'INSERT') THEN
        INSERT INTO products_history 
        (product_id, productid, designation, description, imageid, 
         image_path, operation_type, load_batch_id)
        VALUES 
        (NEW.id, NEW.productid, NEW.designation, NEW.description, 
         NEW.imageid, NEW.image_path, 'INSERT', current_batch_id);
        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER products_audit_trigger
AFTER INSERT ON products
FOR EACH ROW EXECUTE FUNCTION audit_products();
```

**Notes:**
- Test data (`X_test.csv`) is NOT stored in database - loaded as DataFrame and versioned in MLflow once
- Datasets and models are tracked entirely in MLflow (no database tables for them)
- Audit trail captures data evolution for time-travel queries

### 3. Data Loader Service

**src/data/loader.py** - Main data loading logic:
- Read CSV files using pandas
- Calculate target row count: `total_rows × current_percentage`
- Use deterministic sampling (seeded=42) to ensure consistency
- Map imageid to actual file paths in `images/image_train/`
- Insert data into PostgreSQL using sqlalchemy
- Create batch entry in `data_loads` table
- Triggers automatically populate `products_history`

**src/data/db_init.py** - Database initialization:
- Create all tables and triggers
- Initialize with 40% of training data

**Key concept for incremental loading:**
- Week 1: Load 40% of data (deterministic sample with seed=42)
- Week 2: Load 43% of data (same seed, cumulative approach)
- ...
- Week 20: Reach 100% of data
- Cumulative strategy ensures idempotency (re-run reaches correct state)

### 4. Balanced Dataset Generation Service

**src/data/dataset_generator.py** - Generate balanced training datasets from database

**Key Concepts:**

1. **Class Imbalance Problem**: 
   - E-commerce data has imbalanced product categories
   - Some categories may have 10x more samples than others
   - Training on imbalanced data leads to biased models

2. **Balancing Strategy (Selected: Random Oversampling)**:
   - Simple approach: duplicate minority class samples until balanced
   - Works well with text and image data (no synthetic generation needed)
   - Maintains original data distribution characteristics

**Process:**

1. Extract current data from PostgreSQL (all products loaded so far)
2. Apply random oversampling to balance classes (using imbalanced-learn library)
3. Save as `train_week_N.parquet` file
4. Log to MLflow as artifact with metadata:
   - Parameters: week_number, balancing_strategy, total_rows
   - Metrics: class distribution counts
   - Artifacts: parquet file, class distribution plot
5. Verify balanced distribution (all classes should have similar counts)

### 5. Airflow DAG

**dags/weekly_ml_pipeline_dag.py:**

Schedule: Every Monday at midnight (or configurable)

**Tasks:**
1. **check_current_state**: Determine current week and percentage from `data_loads` table
2. **load_increment**: Load next 3% of data into PostgreSQL (skip if already at 100%)
3. **validate_data_load**: Verify row counts match expected percentage
4. **generate_balanced_dataset**: Create balanced dataframe using random oversampling
5. **log_to_mlflow**: Save parquet + log to MLflow with metadata
6. **trigger_model_training**: Automatically start model training
7. **send_notification**: Log completion status

**Task Flow:**
```
check_current_state → load_increment → validate_data_load 
→ generate_balanced_dataset → log_to_mlflow 
→ trigger_model_training → send_notification
```

**Behavior:**
- Increments data weekly until reaching 100%
- Automatically triggers model training after each dataset generation
- Handles failures with retries (configured in Airflow)

### 6. MLflow Integration

**MLflow Setup:**
- Deployed as Docker container alongside PostgreSQL and Airflow
- Backend: PostgreSQL (stores experiment metadata)
- Artifacts: Local volume storage (can migrate to MinIO/S3 later)
- UI accessible at `http://localhost:5000`

**Experiments:**
1. **rakuten_dataset_versioning**: Tracks dataset generation runs
2. **rakuten_model_training**: Tracks model training runs

**What gets logged:**

**For Datasets:**
- Artifact: `train_week_N.parquet` file
- Parameters: week_number, balancing_strategy, total_rows
- Metrics: class distribution counts (class_10_count, class_40_count, etc.)
- Additional: class distribution plot, dataset_stats.json

**For Models:**
- Artifact: Trained model file
- Parameters: hyperparameters (n_estimators, max_depth, etc.)
- Metrics: accuracy, f1_score, precision, recall
- Tags: dataset_name, dataset_run_id (links model to source dataset)

**Test Data:**
- `test_df.parquet` is logged once to MLflow at initialization
- Remains fixed throughout the project (no updates)

**Lineage Tracking:**
- Each model run references its source dataset via `dataset_run_id` tag
- Enables reproducibility: know exactly which data version trained which model

### 7. Configuration Management

**.env** file:
```
# PostgreSQL
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=rakuten_db
POSTGRES_USER=rakuten_user
POSTGRES_PASSWORD=<secure_password>

# MLflow
MLFLOW_TRACKING_URI=http://mlflow:5000
MLFLOW_BACKEND_STORE_URI=postgresql://mlflow_user:password@postgres:5432/mlflow_db
MLFLOW_ARTIFACT_ROOT=/mlflow/artifacts

# Data Pipeline
INITIAL_PERCENTAGE=40
INCREMENT_PERCENTAGE=3
MAX_PERCENTAGE=100
DATA_PATH=/opt/airflow/data/raw
RANDOM_SEED=42
BALANCING_STRATEGY=random_oversampling

# Airflow
AIRFLOW_SCHEDULE=0 0 * * 1  # Every Monday at midnight
AIRFLOW__CORE__EXECUTOR=LocalExecutor
AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=postgresql://airflow_user:password@postgres:5432/airflow_db
```

### 8. Image Handling Strategy

Images remain in `data/raw/images/` on the filesystem (not copied to database).

Database stores:
- Relative paths: `images/image_train/image_*.jpg`
- `imageid` for linking

ML pipelines access images directly via file paths stored in dataframes.

**Benefits:**
- Lightweight database
- No duplication of large files
- Direct file access for model training


## File Structure

```
sep25_cmlops_rakuten/
├── docker-compose.yml
├── .env
├── .gitignore
├── requirements.txt
├── README.md
│
├── data/
│   ├── raw/  (gitignored)
│   │   ├── X_train.csv
│   │   ├── Y_train.csv
│   │   ├── X_test.csv
│   │   └── images/image_train/*.jpg
│   └── training_snapshots/  (generated parquet files)
│       ├── train_week_1.parquet
│       ├── train_week_2.parquet
│       └── test_df.parquet (fixed)
│
├── src/
│   ├── config.py
│   ├── data/
│   │   ├── db_init.py
│   │   ├── loader.py
│   │   ├── dataset_generator.py
│   │   └── schema.sql
│   └── models/
│       ├── train.py
│       └── evaluate.py
│
├── dags/
│   └── weekly_ml_pipeline_dag.py
│
└── docs/
    └── ARCHITECTURE_PLAN.md (this file)
```

## Key Design Decisions

1. **Deterministic Sampling**: Seeded random sampling (seed=42) ensures same rows selected for each percentage, enabling reproducibility.

2. **Audit Trail**: `products_history` table with triggers automatically tracks all data changes for time-travel queries.

3. **Batch Tracking**: `data_loads` table records metadata for each weekly load (percentage, row counts, timestamps).

4. **Test Data Separation**: Test data (`X_test.csv`) stays separate - loaded as DataFrame, versioned once in MLflow (not in database).

5. **Cumulative Incremental Loading**: Load 40%, then 43%, then 46%... (not appending 3% each time). Simplifies idempotency.

6. **Images on Filesystem**: Images stay in `data/raw/images/`, database stores only paths. Better performance and reduced DB size.

7. **MLflow for Dataset Versioning**: Training-ready datasets versioned in MLflow (not raw data). Tight integration with model training.

8. **Random Oversampling**: Simple, effective class balancing strategy that works with text and images.

9. **No Separate Tables for Datasets/Models**: MLflow tracks everything - no need for `training_datasets` or `model_trainings` tables in PostgreSQL.

10. **Local MLflow Storage**: Start with local volume for artifacts (can migrate to MinIO/S3 later if needed).


## Architecture Decisions Summary

**Decisions Made:**

1. **Balancing Strategy**: Random Oversampling (simple, effective, works with text/images)

2. **MLflow Artifact Storage**: Local volume initially (can migrate to MinIO/S3 later)

3. **Model Training**: Airflow automatically triggers training after each dataset generation

4. **Database Tables**: No additional tables needed - MLflow handles dataset and model tracking

5. **Audit Retention**: Keep data forever (project duration is only a few months)

6. **Testing**: Keep simple for now, implement proper CI/CD later

7. **Monitoring**: Minimal for now, will be added in future phases

8. **Validation**: Verify balanced distribution in generated dataframes (simple check)

9. **Scalability**: No specific plans for growth at this stage (educational project)

## Monitoring & Auditing Capabilities

**Database Audit:**
- `products_history` table tracks all data changes with timestamps
- `data_loads` table tracks batch loading status and progress
- Time-travel queries: reconstruct database state at any point in time

**MLflow Tracking:**
- All datasets versioned with metadata (class distribution, row counts)
- All models tracked with lineage to source datasets
- UI for comparing experiments and model performance

**Key Monitoring Points:**
- Data loading progress (percentage, row counts)
- Class distribution evolution over time
- Model performance trends as data grows
- Disk space for artifacts

---

## Summary

This architecture provides:

✅ **Incremental Data Loading**: Simulates real-world data growth (40% → 100%)  
✅ **Complete Audit Trail**: Every change tracked in products_history  
✅ **Dataset Versioning**: Training-ready datasets versioned in MLflow  
✅ **Full Lineage**: MLflow links datasets → models  
✅ **Reproducibility**: Any model can be retrained with exact same data  
✅ **Class Balancing**: Random oversampling handles imbalanced e-commerce data  
✅ **Simplicity**: No unnecessary tables, MLflow handles most tracking  
✅ **Automation**: Airflow orchestrates weekly pipeline with automatic model training  

The system is designed for **educational MLOps learning** with a **simplified, practical approach**.

---

## Next Steps

1. Set up Docker infrastructure (PostgreSQL, Airflow, MLflow)
2. Implement database schema and initialization
3. Create data loader with incremental loading logic
4. Implement dataset generator with random oversampling
5. Build Airflow DAG for weekly orchestration
6. Create basic model training pipeline
7. Test and validate the full workflow


---

## Summary

This architecture provides:

✅ **Incremental Data Loading**: Simulates real-world data growth (40% → 100%)  
✅ **Complete Audit Trail**: Every change tracked in products_history  
✅ **Dataset Versioning**: Training-ready datasets versioned in MLflow (not raw data)  
✅ **Full Lineage**: MLflow links datasets → models with tags  
✅ **Reproducibility**: Any model can be retrained with exact same data  
✅ **Class Balancing**: Random oversampling handles imbalanced e-commerce data  
✅ **Simplicity**: No unnecessary tables, MLflow handles tracking  
✅ **Automation**: Airflow orchestrates weekly pipeline with automatic training  

The system is designed for **educational MLOps learning** with a **simplified, practical approach**.
