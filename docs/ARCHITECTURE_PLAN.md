# Incremental Data Pipeline Architecture

## Overview

Create a PostgreSQL database in Docker that simulates time-evolving data, starting with 40% of CSV/image data and incrementally adding 3% weekly via Apache Airflow orchestration until reaching 100%. Heavy datasets will be stored and versioned in DagsHub using DVC (Data Version Control).

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                   DagsHub Repository                        │
│  Remote Storage (S3-compatible):                           │
│  - X_train.csv, Y_train.csv, X_test.csv (tracked by DVC)  │
│  - images.zip (tracked by DVC)                             │
│  Git tracking: .dvc files, dvc.yaml, pipeline configs      │
└─────────────┬───────────────────────────────────────────────┘
              │ dvc pull
              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Local data/raw/                          │
│  - X_train.csv, Y_train.csv, X_test.csv                    │
│  - images/ (extracted from images.zip)                     │
│  Note: Files are .gitignore'd, managed by DVC only         │
└─────────────┬───────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────┐
│            Data Loader Service (Python)                     │
│  - Calculates current percentage (40% + 3% × weeks)        │
│  - Samples deterministic subset of CSV rows                │
│  - Loads data into PostgreSQL                              │
└─────────────┬───────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────┐
│          PostgreSQL Database (Docker)                       │
│  Tables:                                                    │
│  - products (designation, description, productid, imageid) │
│  - labels (productid, prdtypecode)                         │
│  - test_products (same schema as products)                 │
│  - load_state (tracks current percentage, last_load_date)  │
└─────────────────────────────────────────────────────────────┘
              ▲
              │
┌─────────────┴───────────────────────────────────────────────┐
│         Apache Airflow (Docker Compose)                     │
│  DAG: weekly_data_increment                                │
│  - Runs weekly (configurable)                              │
│  - Optional: dvc pull to sync latest data                  │
│  - Triggers data loader with next percentage               │
│  - Monitors completion and logs state                      │
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

### 2. Database Schema

**PostgreSQL tables:**

```sql
-- Main products table
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    designation TEXT,
    description TEXT,
    productid BIGINT,
    imageid BIGINT,
    image_path TEXT,  -- relative path to image file
    loaded_at TIMESTAMP DEFAULT NOW()
);

-- Labels/targets table
CREATE TABLE labels (
    id SERIAL PRIMARY KEY,
    productid BIGINT UNIQUE,
    prdtypecode INTEGER
);

-- Test data (full 100% from start)
CREATE TABLE test_products (
    id SERIAL PRIMARY KEY,
    designation TEXT,
    description TEXT,
    productid BIGINT,
    imageid BIGINT,
    image_path TEXT
);

-- State tracking
CREATE TABLE load_state (
    id INTEGER PRIMARY KEY DEFAULT 1,
    current_percentage DECIMAL(5,2),
    rows_loaded INTEGER,
    last_load_date TIMESTAMP,
    next_load_date TIMESTAMP,
    CHECK (id = 1)  -- Only one row allowed
);
```

### 3. Data Loader Service

**src/data/loader.py** - Main data loading logic:
- Read CSV files using pandas
- Calculate target row count: `total_rows × current_percentage`
- Use deterministic sampling (seeded by week number) to ensure consistency
- Map imageid to actual file paths in `images/image_train/`
- Insert data into PostgreSQL using `psycopg2` or `sqlalchemy`
- Update `load_state` table with new percentage and timestamp

**src/data/db_init.py** - Database initialization:
- Create tables if they don't exist
- Initialize `load_state` with 40% and current timestamp
- Load 100% of test data upfront (X_test.csv)

**Key logic for incremental loading:**
```python
# Pseudo-code
current_week = calculate_weeks_since_start()
current_percentage = min(40 + (current_week * 3), 100)
target_rows = int(total_rows * current_percentage / 100)

# Deterministic sampling - always same rows for same percentage
df_sample = df.sample(n=target_rows, random_state=SEED)
```

### 4. Airflow DAG

**dags/weekly_increment_dag.py:**
- Schedule: `@weekly` or cron expression for specific day/time
- Tasks:
  1. **check_state**: Query `load_state` to see if we're at 100%
  2. **load_increment**: Execute `src/data/loader.py` if not at 100%
  3. **validate_load**: Count rows, verify percentage reached
  4. **send_notification**: Optional logging/alerting

- Task dependencies: check_state >> load_increment >> validate_load >> send_notification
- Retry logic and failure handling

### 5. Configuration Management

**config.yaml** or **.env** file:
```
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=rakuten_db
POSTGRES_USER=rakuten_user
POSTGRES_PASSWORD=<secure_password>

INITIAL_PERCENTAGE=40
INCREMENT_PERCENTAGE=3
MAX_PERCENTAGE=100

DATA_PATH=/opt/airflow/data/raw
RANDOM_SEED=42

AIRFLOW_SCHEDULE=0 0 * * 1  # Every Monday at midnight
```

### 6. DagsHub Integration

**DVC Setup for Large Files:**
- Configure DVC to use DagsHub's S3-compatible storage
- Track large files: `dvc add data/raw/X_train.csv data/raw/Y_train.csv data/raw/images.zip`
- Push to DagsHub: `dvc push`
- Git tracks only `.dvc` pointer files (lightweight)

**Benefits:**
- Version control for datasets (track changes over time)
- Efficient storage (deduplication, compression)
- Easy collaboration (team members `dvc pull` to get data)
- Integration with MLOps workflows

**Workflow:**
```bash
# Team member setup
git clone <repo-url>
dvc pull  # Download datasets from DagsHub

# Airflow can optionally run dvc pull before data loading
# to ensure latest data version is available
```

### 7. Image Handling Strategy

Since images stay in `data/raw/images/`, the database will store:
- Relative paths (e.g., `images/image_train/image_1263597046_product_3804725264.jpg`)
- Applications accessing data will mount the same volume or use shared filesystem

**Advantages:**
- No duplication of large image files
- Database remains lightweight
- Easy to add images to existing rows
- Direct file access for ML training pipelines

### 8. Implementation Steps

1. **DagsHub & DVC Setup**
   - Initialize DVC in the repository
   - Configure DagsHub remote storage
   - Track and push large datasets (CSVs, images.zip)
   - Update `.gitignore` to exclude tracked files

2. **Infrastructure Setup**
   - Create `docker-compose.yml` with PostgreSQL + Airflow services
   - Set up volumes for data persistence
   - Configure networking between containers

3. **Database Initialization**
   - Write SQL schema (`schema.sql`)
   - Create `db_init.py` to bootstrap database
   - Load initial 40% of training data + 100% test data

4. **Data Loader Development**
   - Implement `loader.py` with incremental logic
   - Add CSV parsing and image path mapping
   - Implement database insert/upsert operations
   - Add state management (read/write `load_state`)

5. **Airflow DAG Creation**
   - Write `weekly_increment_dag.py`
   - Configure schedule and parameters
   - Add monitoring and logging
   - Test with manual trigger

6. **Testing & Validation**
   - Verify 40% initial load
   - Manually trigger weekly increments
   - Validate row counts match expected percentages
   - Check image paths are correctly stored

7. **Documentation**
   - Update README with setup instructions
   - Document how to start/stop services
   - Explain how to monitor progress
   - Add troubleshooting guide

## File Structure

```
sep25_cmlops_rakuten/
├── docker-compose.yml
├── .env
├── .dvc/
│   └── config (DagsHub remote configuration)
├── .dvcignore
├── requirements.txt (add dvc, psycopg2-binary, sqlalchemy, apache-airflow)
├── data/
│   └── raw/
│       ├── X_train.csv.dvc (DVC pointer file)
│       ├── Y_train.csv.dvc (DVC pointer file)
│       ├── X_test.csv.dvc (DVC pointer file)
│       ├── images.zip.dvc (DVC pointer file)
│       └── images/ (extracted locally, gitignored)
├── src/
│   ├── data/
│   │   ├── __init__.py
│   │   ├── db_init.py
│   │   ├── loader.py
│   │   └── schema.sql
│   └── config.py
├── dags/
│   └── weekly_increment_dag.py
├── docs/
│   └── ARCHITECTURE_PLAN.md (this file)
└── README.md
```

## Key Design Decisions

1. **Deterministic Sampling**: Using seeded random sampling ensures the same rows are always selected for a given percentage, maintaining consistency across runs.

2. **State Tracking**: `load_state` table acts as single source of truth for current progress, preventing duplicate loads and enabling restart capability.

3. **Full Test Data**: Loading 100% of test data upfront simulates a realistic scenario where evaluation data is separate from evolving training data.

4. **Incremental Strategy**: Instead of "appending" 3% each week, we load the cumulative percentage (40%, 43%, 46%...). This approach simplifies idempotency - if a load fails, re-running will reach the correct state.

5. **Image Storage**: Keeping images on filesystem rather than in database (BYTEA) balances performance, storage efficiency, and ease of access for ML pipelines.

6. **DagsHub for Data Versioning**: Large datasets are stored in DagsHub's S3-compatible storage, tracked by DVC. This provides version control, collaboration, and efficient storage without bloating the git repository.

## Implementation Todos

- [ ] Set up DVC and configure DagsHub remote storage
- [ ] Track and push datasets to DagsHub (X_train.csv, Y_train.csv, X_test.csv, images.zip)
- [ ] Create docker-compose.yml with PostgreSQL and Airflow services
- [ ] Design and implement PostgreSQL schema (products, labels, test_products, load_state)
- [ ] Create db_init.py to bootstrap database and load initial 40% data
- [ ] Implement loader.py with incremental loading logic and state management
- [ ] Create Airflow DAG for weekly 3% increment orchestration
- [ ] Test initial load, manual triggers, and validate row counts
- [ ] Update README with setup instructions and usage guide

## Questions for Review

Please review this architecture and provide feedback on:

1. **Data Versioning Strategy**: Is DagsHub + DVC the right choice for our team, or should we consider alternatives (Git LFS, MinIO, S3)?

2. **Incremental Loading Logic**: Does the 40% → 43% → 46% cumulative approach make sense, or would you prefer true incremental appends?

3. **Airflow vs Simpler Scheduling**: Is Airflow overkill for a weekly cron job? Should we start simpler (e.g., systemd timer, launchd) and add Airflow later?

4. **Database Schema**: Any missing fields or indexes needed for your use cases?

5. **Image Storage**: Should we consider storing images in DagsHub/S3 instead of local filesystem?

6. **Testing Strategy**: What level of testing do you expect (unit tests, integration tests, manual validation)?

7. **Monitoring & Alerting**: What should we monitor? Where should alerts go (Slack, email, logs)?

## Future Enhancements (Out of Scope)

- MinIO integration for distributed object storage
- Real-time streaming with Kafka instead of batch weekly
- Multi-node PostgreSQL with replication
- CDC (Change Data Capture) for downstream consumers
- ML model training triggered on each data increment
- Data quality checks and validation pipelines
