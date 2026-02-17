"""
Model Registry & Predictions

Model registry overview, prediction testing, and API information.
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

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Add streamlit_app to path
streamlit_app_root = Path(__file__).parent.parent
sys.path.insert(0, str(streamlit_app_root))

# Page configuration
st.set_page_config(
    page_title="Prediction - Rakuten MLOps",
    page_icon="🔮",
    layout="wide"
)

st.title("Prediction & Model Registry")

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

client = get_mlflow_client()

# Refresh button
col1, col2 = st.columns([6, 1])
with col2:
    if st.button("Refresh", use_container_width=True):
        st.cache_resource.clear()
        st.cache_data.clear()
        st.rerun()

# =============================================================================
# SECTION 1: MODEL REGISTRY
# =============================================================================
st.header("1️⃣ Model Registry")

st.markdown("""
View all registered models and their versions. Models are automatically managed based on performance.
""")

if client:
    try:
        registered_models = client.search_registered_models()
        
        if registered_models:
            for model in registered_models:
                with st.expander(f"Model: **{model.name}**", expanded=True):
                    
                    # Get all versions
                    versions = client.search_model_versions(f"name='{model.name}'")
                    
                    if versions:
                        version_data = []
                        for version in versions:
                            version_data.append({
                                "Version": version.version,
                                "Stage": version.current_stage,
                                "Status": version.status,
                                "Created": datetime.fromtimestamp(version.creation_timestamp / 1000).strftime("%Y-%m-%d %H:%M"),
                                "Run ID": version.run_id[:8]
                            })
                        
                        df = pd.DataFrame(version_data)
                        st.dataframe(df, use_container_width=True, hide_index=True)
                        
                        # Show stage counts
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            prod_count = len([v for v in versions if v.current_stage == "Production"])
                            st.metric("Production", prod_count)
                        
                        with col2:
                            staging_count = len([v for v in versions if v.current_stage == "Staging"])
                            st.metric("Staging", staging_count)
                        
                        with col3:
                            none_count = len([v for v in versions if v.current_stage == "None"])
                            st.metric("Not Promoted", none_count)
                        
                        with col4:
                            archived_count = len([v for v in versions if v.current_stage == "Archived"])
                            st.metric("Archived", archived_count)
                    else:
                        st.info("No versions for this model yet")
        else:
            st.info("No registered models yet. Train and register a model first!")
            st.caption("Go to Training page and train a model with auto-register enabled")
    
    except Exception as e:
        st.error(f"❌ Error fetching models: {e}")

else:
    st.error("❌ MLflow connection required")
    st.info(f"Make sure MLflow is running at {MLFLOW_URI}")

st.markdown("---")

# =============================================================================
# SECTION 2: TEST PREDICTIONS
# =============================================================================
st.header("2️⃣ Test Predictions")

st.markdown("""
Test the deployed model by sending prediction requests to the API.
The API will use the current **Production** model.
""")

# Example products
examples = {
    "Livre Harry Potter": {
        "designation": "Harry Potter à l'école des sorciers",
        "description": "Premier tome de la saga Harry Potter. Roman jeunesse fantastique."
    },
    "Chaise de bureau": {
        "designation": "Chaise de bureau ergonomique",
        "description": "Chaise avec dossier réglable, accoudoirs, roulettes pour parquet."
    },
    "Console PlayStation": {
        "designation": "PlayStation 5 Console",
        "description": "Console de jeux vidéo nouvelle génération avec lecteur Blu-ray."
    }
}

# Select example
example_choice = st.selectbox(
    "Choose an example or enter custom text",
    options=["Custom"] + list(examples.keys())
)

if example_choice != "Custom":
    selected = examples[example_choice]
    designation = st.text_input("Designation", value=selected["designation"])
    description = st.text_area("Description", value=selected["description"], height=100)
else:
    designation = st.text_input("Designation", value="")
    description = st.text_area("Description", value="", height=100)

if st.button("Predict", type="primary", disabled=(not designation or not description)):
    
    payload = {
        "designation": designation,
        "description": description
    }
    
    try:
        with st.spinner("Making prediction..."):
            response = requests.post(
                f"{API_URL}/predict",
                json=payload,
                timeout=10
            )
        
        if response.status_code == 200:
            result = response.json()
            
            st.success("✅ Prediction successful!")
            
            col1, col2 = st.columns(2)
            
            with col1:
                predicted_class = result.get("predicted_class", "N/A")
                st.metric("Predicted Class", predicted_class)
            
            with col2:
                confidence = result.get("confidence", 0)
                st.metric("Confidence", f"{confidence:.2%}")
            
            # Show top probabilities
            if "probabilities" in result:
                st.subheader("Top 5 Class Probabilities")
                
                probs = result["probabilities"]
                top_probs = sorted(probs.items(), key=lambda x: x[1], reverse=True)[:5]
                
                prob_data = [{"Class": k, "Probability": f"{v:.4f}"} for k, v in top_probs]
                st.dataframe(pd.DataFrame(prob_data), use_container_width=True, hide_index=True)
            
            # Full response
            with st.expander("📋 Full API Response"):
                st.json(result)
        
        else:
            st.error(f"❌ API Error: {response.status_code}")
            st.text(response.text)
    
    except requests.exceptions.ConnectionError:
        st.error("❌ Could not connect to API")
        st.info(f"💡 Make sure API is running at {API_URL}")
    except requests.exceptions.Timeout:
        st.error("❌ Request timeout")
    except Exception as e:
        st.error(f"❌ Prediction failed: {e}")

st.markdown("---")

# =============================================================================
# SECTION 3: API INFORMATION
# =============================================================================
st.header("3️⃣ API Information")

st.info(f"""
**API Endpoints:**
- Base URL: {API_URL}
- Health: {API_URL}/health
- Predict: {API_URL}/predict
- Documentation: {API_URL}/docs
""")

st.markdown("""
The API serves the current Production model from the MLflow registry. 
All predictions are logged for monitoring and drift detection.
""")

# Footer
st.markdown("---")
st.caption("The API automatically reloads when a new model is promoted to Production")
