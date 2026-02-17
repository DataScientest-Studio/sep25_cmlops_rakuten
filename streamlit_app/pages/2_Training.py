"""
Training Pipeline

Data preparation, model training, and experiment tracking.
"""
import streamlit as st
import sys
from pathlib import Path
import pandas as pd
import mlflow
from mlflow.tracking import MlflowClient
import os
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Add streamlit_app to path
streamlit_app_root = Path(__file__).parent.parent
sys.path.insert(0, str(streamlit_app_root))

from managers.pipeline_executor import run_dataset_generator, run_model_training

# Page configuration
st.set_page_config(
    page_title="Training - Rakuten MLOps",
    page_icon="🔄",
    layout="wide"
)

st.title("Training Pipeline")

# MLflow connection
MLFLOW_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")

@st.cache_resource
def get_mlflow_client():
    """Create MLflow client"""
    try:
        mlflow.set_tracking_uri(MLFLOW_URI)
        client = MlflowClient(tracking_uri=MLFLOW_URI)
        return client
    except Exception as e:
        st.error(f"❌ Could not connect to MLflow: {e}")
        return None

client = get_mlflow_client()

# Refresh button
col1, col2 = st.columns([6, 1])
with col2:
    if st.button("Refresh", use_container_width=True):
        st.cache_resource.clear()
        st.cache_data.clear()
        st.rerun()

# =============================================================================
# SECTION 1: DATASET GENERATION
# =============================================================================
st.header("1️⃣ Dataset Preparation")

st.markdown("""
Generate a balanced dataset from the current database state. This creates a training-ready dataset with:
- Class balancing (RandomOverSampling)
- Logged to MLflow for versioning
- Saved as parquet for reproducibility
""")

col1, col2 = st.columns([1, 3])

with col1:
    if st.button("Generate Balanced Dataset", type="primary", use_container_width=True):
        with st.spinner("Generating balanced dataset... This may take 1-2 minutes"):
            result = run_dataset_generator()
            
            if result['success']:
                st.success(f"✅ {result['message']}")
                st.info(f"📊 Size: {result.get('dataset_size', 0):,} samples")
                st.info(f"🔬 MLflow Run: {result.get('run_id', 'N/A')[:8]}...")
                st.cache_data.clear()
            else:
                st.error(f"❌ {result['message']}")

with col2:
    st.info("""
    **What this does:**
    1. Queries current products from database
    2. Applies RandomOverSampling for class balance
    3. Logs dataset metadata to MLflow
    4. Saves as parquet file
    """)

# Show recent dataset runs if available
if client:
    try:
        experiments = client.search_experiments()
        dataset_exp = [e for e in experiments if 'dataset' in e.name.lower()]
        
        if dataset_exp:
            st.subheader("Recent Dataset Generations")
            
            runs = client.search_runs(
                experiment_ids=[dataset_exp[0].experiment_id],
                max_results=5,
                order_by=["start_time DESC"]
            )
            
            if runs:
                run_data = []
                for run in runs:
                    run_data.append({
                        "Date": datetime.fromtimestamp(run.info.start_time / 1000).strftime("%Y-%m-%d %H:%M"),
                        "Percentage": run.data.params.get('percentage', 'N/A'),
                        "Size": f"{run.data.metrics.get('total_samples', 0):,.0f}",
                        "Classes": f"{run.data.metrics.get('num_classes', 0):.0f}",
                        "Imbalance": f"{run.data.metrics.get('imbalance_ratio_after', 0):.2f}"
                    })
                
                st.dataframe(pd.DataFrame(run_data), use_container_width=True, hide_index=True)
    except:
        pass

st.markdown("---")

# =============================================================================
# SECTION 2: MODEL TRAINING
# =============================================================================
st.header("2️⃣ Model Training")

st.markdown("""
Train TF-IDF + Logistic Regression classifier on the current database state.
**Auto-promotion enabled**: New models are automatically promoted to Production if they perform better than the current model.
""")

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("Training Configuration")
    
    max_features = st.number_input(
        "Max TF-IDF Features",
        min_value=1000,
        max_value=10000,
        value=5000,
        step=1000,
        help="Maximum number of TF-IDF features to extract"
    )
    
    C_param = st.number_input(
        "C (Regularization)",
        min_value=0.1,
        max_value=10.0,
        value=1.0,
        step=0.1,
        help="Inverse of regularization strength"
    )

with col2:
    st.subheader("Auto-Promotion Logic")
    
    st.info("""
    **Automatic promotion to Production:**
    
    1. ✅ **Better performance** → Promote to Production, archive old
    2. ❌ **Worse performance** → Archive new model, keep current Production
    3. 🆕 **First model** (F1 ≥ 0.70) → Promote to Production
    4. ⚠️ **Below threshold** (F1 < 0.70) → Archive automatically
    
    **No manual intervention needed!** 🎯
    """)

# Train button
if st.button("Train Model", type="primary", use_container_width=True):
    with st.spinner("Training model... This may take 2-4 minutes"):
        result = run_model_training(
            max_features=int(max_features),
            C=float(C_param),
            auto_promote=True  # Always enabled - automatic smart promotion
        )
        
        if result['success']:
            st.success(f"✅ {result['message']}")
            st.balloons()
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Samples", f"{result.get('samples', 0):,}")
            with col2:
                st.metric("Classes", result.get('classes', 0))
            with col3:
                st.info(f"🔬 Run ID: {result.get('run_id', 'N/A')[:8]}...")
            
            st.cache_data.clear()
            st.cache_resource.clear()
        else:
            st.error(f"❌ {result['message']}")

st.markdown("---")

# =============================================================================
# SECTION 3: EXPERIMENT TRACKING
# =============================================================================
st.header("3️⃣ Training History & Experiments")

if client:
    try:
        # Get model training experiments
        experiments = client.search_experiments()
        training_exp = [e for e in experiments if 'training' in e.name.lower()]
        
        if training_exp:
            # Get recent runs
            runs = client.search_runs(
                experiment_ids=[training_exp[0].experiment_id],
                max_results=10,
                order_by=["start_time DESC"]
            )
            
            if runs:
                st.subheader("Recent Training Runs")
                
                run_data = []
                for run in runs:
                    metrics = run.data.metrics
                    params = run.data.params
                    
                    run_data.append({
                        "Date": datetime.fromtimestamp(run.info.start_time / 1000).strftime("%Y-%m-%d %H:%M"),
                        "Run ID": run.info.run_id[:8],
                        "Accuracy": f"{metrics.get('test_accuracy', 0):.4f}",
                        "F1 Score": f"{metrics.get('test_f1_weighted', 0):.4f}",
                        "Precision": f"{metrics.get('test_precision_weighted', 0):.4f}",
                        "Recall": f"{metrics.get('test_recall_weighted', 0):.4f}",
                        "Max Features": params.get('max_features', 'N/A'),
                        "C": params.get('C', 'N/A'),
                        "Status": run.info.status
                    })
                
                df = pd.DataFrame(run_data)
                st.dataframe(df, use_container_width=True, hide_index=True)
                
                # Show latest run details
                if len(runs) > 0:
                    with st.expander("Latest Run Details"):
                        latest_run = runs[0]
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.markdown("**Parameters**")
                            for key, value in latest_run.data.params.items():
                                st.text(f"{key}: {value}")
                        
                        with col2:
                            st.markdown("**Metrics**")
                            for key, value in latest_run.data.metrics.items():
                                st.text(f"{key}: {value:.4f}")
                        
                        st.markdown("**Artifacts**")
                        try:
                            artifacts = client.list_artifacts(latest_run.info.run_id)
                            for artifact in artifacts:
                                st.text(f"{'Folder' if artifact.is_dir else 'File'} {artifact.path}")
                        except:
                            st.caption("Could not list artifacts")
            else:
                st.info("No training runs yet. Train your first model above!")
        else:
            st.info("No training experiments found in MLflow")
    
    except Exception as e:
        st.warning(f"⚠️ Could not fetch experiments: {e}")

else:
    st.error("❌ MLflow connection required to view experiments")
    st.info(f"Make sure MLflow is running at {MLFLOW_URI}")

# =============================================================================
# SECTION 4: MODEL VERSIONING
# =============================================================================
st.header("4️⃣ Model Versioning Strategy")

st.markdown("""
**Every training run creates a complete version:**

1. **Data Version**: Linked via database timestamp (which batch was used)
2. **Code Version**: Git commit hash (can be tagged in MLflow)
3. **Parameter Version**: All hyperparameters logged to MLflow
4. **Model Version**: Artifact stored in MinIO via MLflow

**To reproduce any training:**
- Get MLflow run_id
- Query database for data state at training time
- Retrieve all parameters from MLflow
- Retrain with identical setup

No external versioning tools needed!
""")

# Footer
st.markdown("---")
st.caption(f"Connected to MLflow at {MLFLOW_URI}")
