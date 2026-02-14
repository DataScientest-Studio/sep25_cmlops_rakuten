"""
Rakuten MLOps Pipeline - Home & Presentation

Welcome page with project overview and pipeline explanation.
"""
import streamlit as st
from pathlib import Path

# Page configuration
st.set_page_config(
    page_title="Rakuten MLOps - Home",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        color: #1f77b4;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        text-align: center;
        color: #666;
        margin-bottom: 2rem;
    }
    </style>
    """, unsafe_allow_html=True)

# Main content
st.markdown('<div class="main-header">🎯 Rakuten MLOps Pipeline</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Product Classification - MLOps Certification Project</div>', unsafe_allow_html=True)

# Project Overview
st.header("📖 Project Overview")

st.markdown("""
This project demonstrates a **complete MLOps pipeline** for product classification using:
- Incremental data loading (40% → 100%)
- Experiment tracking with MLflow
- Model versioning and promotion
- REST API serving with monitoring
- Drift detection and observability

**Goal**: Classify Rakuten products into 27 categories using text data (designation + description)
""")

# Pipeline Architecture
st.header("🏗️ Pipeline Architecture")

col1, col2 = st.columns([1, 1])

with col1:
    st.markdown("""
    ### Core Components
    
    **1. Data Storage**
    - PostgreSQL with audit trail
    - Tracks all data changes
    - Enables reproducibility
    
    **2. Experiment Tracking**
    - MLflow for runs & metrics
    - Model registry
    - Artifact storage (MinIO)
    
    **3. Model Serving**
    - FastAPI REST API
    - Automatic model reloading
    - Health monitoring
    
    **4. Observability**
    - Prometheus metrics
    - Grafana dashboards
    - Inference logging
    """)

with col2:
    st.markdown("""
    ### Pipeline Flow
    
    ```
    1️⃣ Data Pipeline
       ↓ Load incremental data
       ↓ Track in database audit trail
    
    2️⃣ Training Pipeline
       ↓ Generate balanced dataset
       ↓ Train TF-IDF + LogisticRegression
       ↓ Log to MLflow
    
    3️⃣ Model Registry
       ↓ Register model version
       ↓ Promote to Production
    
    4️⃣ Serving
       ↓ API loads Production model
       ↓ Serve predictions
       ↓ Log inferences
    
    5️⃣ Monitoring
       ↓ Collect metrics
       ↓ Detect drift
       ↓ Alert if needed
    ```
    """)

# Key Features
st.header("✨ Key MLOps Capabilities")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    ### 📊 Data Versioning
    - Database audit trail
    - Batch tracking
    - Timestamp-based reproducibility
    - No external tools needed
    """)

with col2:
    st.markdown("""
    ### 🔬 Experiment Tracking
    - All hyperparameters logged
    - Metrics & artifacts stored
    - Model lineage
    - Easy comparison
    """)

with col3:
    st.markdown("""
    ### 🚀 Production Ready
    - Stage-based promotion
    - Health checks
    - Automated reloading
    - Monitoring & alerting
    """)

# Versioning Strategy
st.header("🔄 Reproducibility Strategy")

st.info("""
**How we ensure reproducibility without DVC:**

1. **Data Versioning**: PostgreSQL `data_loads` and `products_history` tables track every data change with timestamps
2. **Experiment Tracking**: MLflow logs all parameters, metrics, and artifacts for every training run
3. **Model Registry**: Each model version links back to its training run and data version

**To reproduce any training**: Given an MLflow run_id, we can query the database for the exact data state at that time, 
retrieve all hyperparameters from MLflow, and retrain with identical setup.
""")

# Navigation
st.header("🗺️ Demo Navigation")

st.markdown("""
Use the sidebar to navigate through the pipeline stages:

- **Page 1**: 🏠 This overview
- **Page 2**: 🗄️ Data & Infrastructure - Docker status, database state, data evolution
- **Page 3**: 🔄 Training - Dataset generation, model training, experiment tracking  
- **Page 4**: 🚀 Promotion - Model registry, promotion, and prediction testing
- **Page 5**: 📈 Monitoring - Drift detection, system health, inference logs

Each page represents a stage in the MLOps lifecycle.
""")

# Quick Links
st.header("🔗 External Services")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### MLflow UI")
    st.markdown("http://localhost:5000")
    st.caption("Experiment tracking & model registry")

with col2:
    st.markdown("### API Documentation")
    st.markdown("http://localhost:8000/docs")
    st.caption("FastAPI Swagger UI")

with col3:
    st.markdown("### Grafana Dashboards")
    st.markdown("http://localhost:3000")
    st.caption("Monitoring & visualization")

# Technical Details
with st.expander("🔧 Technical Stack"):
    st.markdown("""
    **Infrastructure**:
    - PostgreSQL 15 (database with audit trail)
    - MinIO (S3-compatible object storage)
    - MLflow 2.10 (experiment tracking)
    - FastAPI (model serving)
    - Prometheus + Grafana (monitoring)
    
    **ML Stack**:
    - scikit-learn (TF-IDF + LogisticRegression)
    - imbalanced-learn (data balancing)
    - pandas (data processing)
    
    **Deployment**:
    - Docker Compose (container orchestration)
    - Streamlit (control room UI)
    """)

# Footer
st.markdown("---")
st.markdown("""
    <div style="text-align: center; color: #666;">
        <small>DataScientest MLOps Certification - September 2025</small>
    </div>
    """, unsafe_allow_html=True)
