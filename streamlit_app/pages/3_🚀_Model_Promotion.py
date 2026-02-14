"""
Model Promotion & Prediction Page

Manage model registry, promote models, and test predictions via API.
"""
import streamlit as st
import sys
from pathlib import Path
import pandas as pd
import mlflow
from mlflow.tracking import MlflowClient
import requests
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
    page_title="Model Promotion - Rakuten MLOps",
    page_icon="🚀",
    layout="wide"
)

# Title
st.title("🚀 Model Promotion & Prediction")
st.markdown("Manage model registry and test predictions")

# Docker status header
render_docker_status(docker_manager, focus_services=["MLflow", "API"], show_all=True)

# Configuration
MLFLOW_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
API_URL = os.getenv("API_URL", "http://localhost:8000")

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
    st.warning("⚠️ MLflow not available. Some features will be limited.")

# 1. Registered Models
st.header("1️⃣ Registered Models")

try:
    if client:
        registered_models = client.search_registered_models()
        
        if registered_models:
            model_data = []
            
            for model in registered_models:
                # Get latest versions
                latest_versions = client.get_latest_versions(model.name)
                
                for version in latest_versions:
                    model_data.append({
                        "Model Name": model.name,
                        "Version": version.version,
                        "Stage": version.current_stage,
                        "Status": version.status,
                        "Created": datetime.fromtimestamp(version.creation_timestamp / 1000).strftime("%Y-%m-%d %H:%M"),
                        "Run ID": version.run_id[:8] + "..."
                    })
            
            if model_data:
                model_df = pd.DataFrame(model_data)
                
                # Metrics
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Total Models", len(registered_models))
                
                with col2:
                    st.metric("Total Versions", len(model_data))
                
                with col3:
                    prod_count = len([m for m in model_data if m["Stage"] == "Production"])
                    st.metric("Production", prod_count)
                
                with col4:
                    staging_count = len([m for m in model_data if m["Stage"] == "Staging"])
                    st.metric("Staging", staging_count)
                
                # Display table
                st.dataframe(
                    model_df,
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("ℹ️ Models registered but no versions available")
        else:
            st.warning("⚠️ No registered models found in MLflow")
            st.info("💡 Train and register a model first using MLflow")
    else:
        st.warning("⚠️ Cannot fetch registered models without MLflow connection")

except Exception as e:
    st.error(f"❌ Error fetching registered models: {e}")

st.markdown("---")

# 2. Model Promotion Panel (LIVE)
st.header("2️⃣ Model Promotion")

st.markdown("""
    Promote model versions between stages (None → Staging → Production)
    
    ⚠️ **Note**: This will update the actual model registry in MLflow.
""")

# Import pipeline executor
from managers.pipeline_executor import promote_model

col1, col2 = st.columns(2)

with col1:
    # Model selection
    model_name = st.text_input(
        "Model Name",
        value="rakuten_classifier",
        help="Enter the name of the model to promote"
    )
    
    version = st.number_input(
        "Version",
        min_value=1,
        value=1,
        help="Enter the version number to promote"
    )

with col2:
    # Stage selection
    target_stage = st.selectbox(
        "Target Stage",
        options=["Staging", "Production", "Archived", "None"],
        help="Select the target stage for promotion"
    )
    
    archive_existing = st.checkbox(
        "Archive existing Production models",
        value=True,
        help="Automatically archive current Production models"
    )

# Promotion button
if st.button("🚀 Promote Model", type="primary", use_container_width=True):
    if not client:
        st.error("❌ MLflow connection required for promotion")
        st.info("💡 Make sure MLflow is running at http://localhost:5000")
    else:
        with st.spinner(f"Promoting {model_name} v{version} to {target_stage}..."):
            result = promote_model(
                model_name=model_name,
                version=version,
                stage=target_stage,
                archive_existing=archive_existing
            )
            
            if result['success']:
                st.success(f"✅ {result['message']}")
                st.balloons()
                # Clear cache to refresh model registry
                st.cache_data.clear()
                st.cache_resource.clear()
            else:
                st.error(f"❌ {result['message']}")

st.markdown("---")

# 3. Prediction Simulator
st.header("3️⃣ Prediction Simulator")

st.markdown("Test the deployed model via the API")

# Input form
with st.form("prediction_form"):
    st.subheader("Product Information")
    
    designation = st.text_input(
        "Designation",
        value="Chaise de bureau ergonomique",
        help="Product title/name"
    )
    
    description = st.text_area(
        "Description",
        value="Chaise de bureau avec dossier ergonomique, accoudoirs réglables, roulettes pour parquet. Parfait pour télétravail.",
        height=150,
        help="Product description"
    )
    
    submitted = st.form_submit_button("🔮 Predict", type="primary", use_container_width=True)

if submitted:
    st.subheader("Prediction Results")
    
    try:
        # Make API request
        payload = {
            "designation": designation,
            "description": description
        }
        
        with st.spinner("Making prediction..."):
            response = requests.post(
                f"{API_URL}/predict",
                json=payload,
                timeout=10
            )
        
        if response.status_code == 200:
            result = response.json()
            
            # Display results
            col1, col2 = st.columns(2)
            
            with col1:
                predicted_class = result.get("predicted_class", "N/A")
                st.success(f"### Predicted Class: **{predicted_class}**")
            
            with col2:
                confidence = result.get("confidence", 0)
                st.metric("Confidence", f"{confidence:.2%}")
            
            # Show probabilities if available
            if "probabilities" in result:
                st.subheader("Class Probabilities")
                
                probs = result["probabilities"]
                probs_df = pd.DataFrame([
                    {"Class": k, "Probability": f"{v:.4f}"}
                    for k, v in sorted(probs.items(), key=lambda x: x[1], reverse=True)
                ])
                
                st.dataframe(
                    probs_df.head(10),  # Show top 10
                    use_container_width=True,
                    hide_index=True
                )
            
            # Additional info
            with st.expander("📋 Full Response"):
                st.json(result)
        
        else:
            st.error(f"❌ API Error: {response.status_code}")
            st.text(response.text)
    
    except requests.exceptions.ConnectionError:
        st.error("❌ Could not connect to API. Make sure the API container is running.")
        st.info(f"💡 Expected API URL: {API_URL}")
    except requests.exceptions.Timeout:
        st.error("❌ Request timeout. The API is taking too long to respond.")
    except Exception as e:
        st.error(f"❌ Prediction failed: {e}")

st.markdown("---")

# 4. API Health Status
st.header("4️⃣ API Health Status")

try:
    response = requests.get(f"{API_URL}/health", timeout=5)
    
    if response.status_code == 200:
        health = response.json()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            status = health.get("status", "unknown")
            if status == "healthy":
                st.success(f"### {status}")
            else:
                st.warning(f"### {status}")
        
        with col2:
            model_loaded = health.get("model_loaded", False)
            st.metric("Model Loaded", "✅ Yes" if model_loaded else "❌ No")
        
        with col3:
            model_version = health.get("model_version", "N/A")
            st.metric("Model Version", model_version)
        
        with col4:
            timestamp = health.get("timestamp", "N/A")
            st.metric("Last Check", timestamp)
        
        # Additional details
        with st.expander("📋 Full Health Response"):
            st.json(health)
    
    else:
        st.error(f"❌ Health check failed: {response.status_code}")

except requests.exceptions.ConnectionError:
    st.error("❌ API is not reachable")
    st.info(f"💡 Make sure the API container is running at {API_URL}")
except Exception as e:
    st.error(f"❌ Health check failed: {e}")

# Quick API info
st.markdown("---")
st.info(f"""
    **API Information:**
    - Base URL: {API_URL}
    - Health Endpoint: {API_URL}/health
    - Prediction Endpoint: {API_URL}/predict
    - Docs: {API_URL}/docs
""")

# Footer
st.markdown("---")
st.caption(f"💡 Connected to API at {API_URL} and MLflow at {MLFLOW_URI}")
