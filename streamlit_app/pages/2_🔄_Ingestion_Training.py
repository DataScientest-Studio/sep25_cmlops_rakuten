"""
Ingestion & Training Page

Track MLflow experiments, view training metrics, and manage model artifacts.
"""
import streamlit as st
import sys
from pathlib import Path
import pandas as pd
import mlflow
from mlflow.tracking import MlflowClient
import os
from datetime import datetime

# Add project root to path (parent of streamlit_app)
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Add streamlit_app to path for local imports
streamlit_app_root = Path(__file__).parent.parent
sys.path.insert(0, str(streamlit_app_root))

from managers.docker_manager import docker_manager
from components.docker_status import render_docker_status

# Page configuration
st.set_page_config(
    page_title="Ingestion & Training - Rakuten MLOps",
    page_icon="🔄",
    layout="wide"
)

# Title
st.title("🔄 Ingestion & Training")
st.markdown("Monitor MLflow experiments and training runs")

# Docker status header
render_docker_status(docker_manager, focus_services=["PostgreSQL", "MLflow"], show_all=True)

# MLflow connection settings
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
        st.info(f"💡 Make sure MLflow is running at {MLFLOW_URI}")
        return None

# Refresh button
col1, col2 = st.columns([6, 1])
with col2:
    if st.button("🔄 Refresh", use_container_width=True):
        st.cache_resource.clear()
        st.cache_data.clear()
        st.rerun()

# Get MLflow client
client = get_mlflow_client()

if client is None:
    st.stop()

# 1. MLflow Experiments
st.header("1️⃣ MLflow Experiments")

try:
    experiments = client.search_experiments()
    
    if experiments:
        exp_data = []
        for exp in experiments:
            # Get run count
            runs = client.search_runs(experiment_ids=[exp.experiment_id])
            exp_data.append({
                "Experiment ID": exp.experiment_id,
                "Name": exp.name,
                "Artifact Location": exp.artifact_location,
                "Run Count": len(runs),
                "Lifecycle Stage": exp.lifecycle_stage
            })
        
        exp_df = pd.DataFrame(exp_data)
        
        # Display metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Experiments", len(experiments))
        
        with col2:
            total_runs = exp_df['Run Count'].sum()
            st.metric("Total Runs", total_runs)
        
        with col3:
            active_exps = len([e for e in experiments if e.lifecycle_stage == "active"])
            st.metric("Active Experiments", active_exps)
        
        # Display experiments table
        st.dataframe(
            exp_df,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.warning("⚠️ No experiments found in MLflow")

except Exception as e:
    st.error(f"❌ Error fetching experiments: {e}")

st.markdown("---")

# 2. Recent Training Runs
st.header("2️⃣ Recent Training Runs")

try:
    # Get all runs, sorted by start time
    all_runs = client.search_runs(
        experiment_ids=[exp.experiment_id for exp in experiments],
        max_results=5,
        order_by=["start_time DESC"]
    )
    
    if all_runs:
        run_data = []
        for run in all_runs:
            metrics = run.data.metrics
            params = run.data.params
            
            run_data.append({
                "Run ID": run.info.run_id[:8] + "...",
                "Status": run.info.status,
                "Start Time": datetime.fromtimestamp(run.info.start_time / 1000).strftime("%Y-%m-%d %H:%M"),
                "Duration (min)": f"{(run.info.end_time - run.info.start_time) / 60000:.1f}" if run.info.end_time else "Running",
                "Accuracy": f"{metrics.get('accuracy', 0):.4f}",
                "F1 Score": f"{metrics.get('f1_score', 0):.4f}",
                "Model": params.get('model_type', 'N/A')
            })
        
        run_df = pd.DataFrame(run_data)
        
        st.dataframe(
            run_df,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.warning("⚠️ No training runs found")

except Exception as e:
    st.error(f"❌ Error fetching runs: {e}")

st.markdown("---")

# 3. Latest Training Run Details
st.header("3️⃣ Latest Training Run Details")

try:
    # Get the most recent run
    latest_runs = client.search_runs(
        experiment_ids=[exp.experiment_id for exp in experiments],
        max_results=1,
        order_by=["start_time DESC"]
    )
    
    if latest_runs:
        latest_run = latest_runs[0]
        
        st.subheader(f"Run ID: {latest_run.info.run_id}")
        
        # Run info
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Status", latest_run.info.status)
        
        with col2:
            start_time = datetime.fromtimestamp(latest_run.info.start_time / 1000)
            st.metric("Start Time", start_time.strftime("%Y-%m-%d %H:%M"))
        
        with col3:
            if latest_run.info.end_time:
                duration = (latest_run.info.end_time - latest_run.info.start_time) / 60000
                st.metric("Duration", f"{duration:.1f} min")
            else:
                st.metric("Duration", "Running...")
        
        # Metrics
        st.subheader("📊 Metrics")
        metrics = latest_run.data.metrics
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Accuracy", f"{metrics.get('accuracy', 0):.4f}")
        
        with col2:
            st.metric("F1 Score", f"{metrics.get('f1_score', 0):.4f}")
        
        with col3:
            st.metric("Precision", f"{metrics.get('precision', 0):.4f}")
        
        with col4:
            st.metric("Recall", f"{metrics.get('recall', 0):.4f}")
        
        # Additional metrics
        if metrics:
            with st.expander("📋 View All Metrics"):
                metrics_df = pd.DataFrame([
                    {"Metric": k, "Value": f"{v:.6f}"}
                    for k, v in metrics.items()
                ])
                st.dataframe(metrics_df, use_container_width=True, hide_index=True)
        
        # Parameters
        st.subheader("⚙️ Parameters")
        params = latest_run.data.params
        
        if params:
            # Display important parameters
            col1, col2 = st.columns(2)
            
            with col1:
                if 'max_features' in params:
                    st.metric("Max Features", params['max_features'])
                if 'ngram_range' in params:
                    st.metric("N-gram Range", params['ngram_range'])
                if 'model_type' in params:
                    st.metric("Model Type", params['model_type'])
            
            with col2:
                if 'test_size' in params:
                    st.metric("Test Size", params['test_size'])
                if 'random_state' in params:
                    st.metric("Random State", params['random_state'])
                if 'balancing_strategy' in params:
                    st.metric("Balancing", params['balancing_strategy'])
            
            # All parameters
            with st.expander("📋 View All Parameters"):
                params_df = pd.DataFrame([
                    {"Parameter": k, "Value": v}
                    for k, v in params.items()
                ])
                st.dataframe(params_df, use_container_width=True, hide_index=True)
        else:
            st.info("No parameters recorded for this run")
        
    else:
        st.warning("⚠️ No training runs available")

except Exception as e:
    st.error(f"❌ Error fetching latest run: {e}")

st.markdown("---")

# 4. Model Artifacts
st.header("4️⃣ Model Artifacts")

try:
    if latest_runs:
        latest_run = latest_runs[0]
        
        # List artifacts
        artifacts = client.list_artifacts(latest_run.info.run_id)
        
        if artifacts:
            artifact_data = []
            for artifact in artifacts:
                # Get artifact info
                artifact_data.append({
                    "Path": artifact.path,
                    "Is Directory": "📁" if artifact.is_dir else "📄",
                    "Size (bytes)": artifact.file_size if hasattr(artifact, 'file_size') else "N/A"
                })
            
            artifact_df = pd.DataFrame(artifact_data)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("Total Artifacts", len(artifacts))
            
            with col2:
                files = [a for a in artifacts if not a.is_dir]
                st.metric("Files", len(files))
            
            st.dataframe(
                artifact_df,
                use_container_width=True,
                hide_index=True
            )
            
            # Artifact location
            st.info(f"📍 Artifact Location: {latest_run.info.artifact_uri}")
        else:
            st.warning("⚠️ No artifacts found for latest run")
    else:
        st.warning("⚠️ No runs available")

except Exception as e:
    st.error(f"❌ Error fetching artifacts: {e}")

st.markdown("---")

# 5. Data Pipeline Actions (LIVE)
st.header("5️⃣ Data Pipeline Actions")

st.markdown("""
    Use these actions to trigger real pipeline operations.
    
    ⚠️ **Note**: These buttons execute actual Python scripts and may take time to complete.
""")

# Import pipeline executor
from managers.pipeline_executor import run_data_loader, run_dataset_generator, run_model_training

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("📥 Load Next Data Increment (+3%)", use_container_width=True):
        with st.spinner("Loading data..."):
            result = run_data_loader()
            
            if result['success']:
                st.success(f"✅ {result['message']}")
                st.info(f"📊 Current: {result['current_percentage']}% ({result.get('total_rows', 0)} products)")
                # Clear cache to refresh data
                st.cache_data.clear()
                st.cache_resource.clear()
            else:
                st.error(f"❌ {result['message']}")

with col2:
    if st.button("🔄 Generate Balanced Dataset", use_container_width=True):
        with st.spinner("Generating balanced dataset..."):
            result = run_dataset_generator()
            
            if result['success']:
                st.success(f"✅ {result['message']}")
                st.info(f"📦 MLflow Run ID: {result['run_id'][:8]}...")
            else:
                st.error(f"❌ {result['message']}")

with col3:
    with st.popover("⚙️ Training Config"):
        max_features = st.number_input("Max Features", value=5000, step=1000)
        C_param = st.number_input("C (Regularization)", value=1.0, step=0.1)
        auto_promote = st.checkbox("Auto-promote if F1 > 0.70", value=False)
        
        if st.button("🚀 Train Model", type="primary"):
            with st.spinner("Training model... This may take a few minutes."):
                result = run_model_training(
                    max_features=int(max_features),
                    C=float(C_param),
                    auto_promote=auto_promote
                )
                
                if result['success']:
                    st.success(f"✅ {result['message']}")
                    st.info(f"📊 Trained on {result['samples']} samples, {result['classes']} classes")
                    st.info(f"🔬 MLflow Run ID: {result['run_id'][:8]}...")
                    # Clear cache to show new run
                    st.cache_data.clear()
                    st.cache_resource.clear()
                else:
                    st.error(f"❌ {result['message']}")

# Footer
st.markdown("---")
st.caption(f"💡 Connected to MLflow at {MLFLOW_URI}")
