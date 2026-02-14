"""
Rakuten MLOps Control Room - Home Page

Main entry point for the Streamlit MLOps monitoring application.
"""
import streamlit as st
import sys
from pathlib import Path

# Add project root to path (parent of streamlit_app)
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Add streamlit_app to path for local imports
streamlit_app_root = Path(__file__).parent
sys.path.insert(0, str(streamlit_app_root))

from managers.docker_manager import docker_manager
from components.docker_status import render_docker_status

# Page configuration
st.set_page_config(
    page_title="Rakuten MLOps Control Room",
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
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)

# Main content
st.markdown('<div class="main-header">🎯 Rakuten MLOps Control Room</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Monitor and control your ML pipeline</div>', unsafe_allow_html=True)

# System overview
st.header("📊 System Overview")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="🗄️ Database",
        value="PostgreSQL",
        delta="Active"
    )

with col2:
    st.metric(
        label="🔬 Experiment Tracking",
        value="MLflow",
        delta="Active"
    )

with col3:
    st.metric(
        label="🚀 API Server",
        value="FastAPI",
        delta="Ready"
    )

with col4:
    st.metric(
        label="📈 Monitoring",
        value="Prometheus + Grafana",
        delta="Active"
    )

# Docker status
render_docker_status(docker_manager, show_all=True)

# Description
st.header("📖 About")

st.markdown("""
This control room provides a centralized interface for monitoring and managing the Rakuten product classification MLOps pipeline.

**Key Features:**
- 📊 **Database Pipeline**: Monitor data ingestion, view class distribution, and track data loads
- 🔄 **Ingestion & Training**: Track MLflow experiments, view training metrics, and manage model artifacts
- 🚀 **Model Promotion**: Promote models between stages and test predictions via the API
- 📈 **Drift & Monitoring**: Monitor model performance, check system health, and view inference logs

**Architecture:**
- Data stored in PostgreSQL database with incremental loading
- MLflow for experiment tracking and model registry
- FastAPI for model serving with health monitoring
- Prometheus & Grafana for metrics and visualization
""")

# Quick links
st.header("🔗 Quick Links")

col1, col2 = st.columns(2)

with col1:
    st.subheader("📄 Pages")
    st.page_link("pages/1_📊_Database_Pipeline.py", label="📊 Database Pipeline", icon="1️⃣")
    st.page_link("pages/2_🔄_Ingestion_Training.py", label="🔄 Ingestion & Training", icon="2️⃣")
    st.page_link("pages/3_🚀_Model_Promotion.py", label="🚀 Model Promotion", icon="3️⃣")
    st.page_link("pages/4_📈_Drift_Monitoring.py", label="📈 Drift & Monitoring", icon="4️⃣")

with col2:
    st.subheader("🌐 External Services")
    st.markdown("- [MLflow UI](http://localhost:5000) - Experiment tracking")
    st.markdown("- [Airflow UI](http://localhost:8080) - Pipeline orchestration")
    st.markdown("- [API Docs](http://localhost:8000/docs) - FastAPI Swagger")
    st.markdown("- [Grafana](http://localhost:3000) - Monitoring dashboards")
    st.markdown("- [Prometheus](http://localhost:9090) - Metrics collection")

# System health summary
st.header("🏥 System Health Summary")

try:
    services_health = docker_manager.get_service_health()
    
    healthy_count = sum(1 for s in services_health.values() if s["status"] == "healthy")
    total_count = len(services_health)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Services Running", f"{healthy_count}/{total_count}")
    
    with col2:
        health_percentage = (healthy_count / total_count * 100) if total_count > 0 else 0
        st.metric("System Health", f"{health_percentage:.0f}%")
    
    with col3:
        overall_status = "🟢 Healthy" if healthy_count == total_count else "🟡 Degraded" if healthy_count > 0 else "🔴 Down"
        st.metric("Overall Status", overall_status)
    
except Exception as e:
    st.error(f"❌ Could not get system health: {e}")

# Footer
st.markdown("---")
st.markdown("""
    <div style="text-align: center; color: #666;">
        <small>Rakuten MLOps Control Room v1.0 | Built with Streamlit</small>
    </div>
    """, unsafe_allow_html=True)
