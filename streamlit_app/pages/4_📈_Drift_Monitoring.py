"""
Drift & Monitoring Page

Monitor model performance, system health, and inference logs.
"""
import streamlit as st
import sys
from pathlib import Path
import pandas as pd
import requests
import os
from datetime import datetime
import plotly.express as px

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
    page_title="Drift & Monitoring - Rakuten MLOps",
    page_icon="📈",
    layout="wide"
)

# Title
st.title("📈 Drift & Monitoring")
st.markdown("Monitor model performance and system health")

# Docker status header
render_docker_status(
    docker_manager, 
    focus_services=["Prometheus", "Grafana", "API"], 
    show_all=True
)

# Configuration
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://localhost:9090")
GRAFANA_URL = os.getenv("GRAFANA_URL", "http://localhost:3000")
API_URL = os.getenv("API_URL", "http://localhost:8000")

# Refresh button
col1, col2 = st.columns([6, 1])
with col2:
    if st.button("🔄 Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# 1. Grafana Link
st.header("1️⃣ Grafana Dashboards")

col1, col2 = st.columns([2, 1])

with col1:
    st.markdown(f"""
        Access the Grafana dashboards for comprehensive monitoring and visualization.
        
        **Available Dashboards:**
        - System Metrics (CPU, Memory, Disk)
        - API Performance (Request Rate, Latency, Errors)
        - Model Metrics (Predictions, Confidence Distribution)
        - Database Metrics (Connections, Query Performance)
    """)

with col2:
    st.link_button(
        "🎨 Open Grafana",
        GRAFANA_URL,
        use_container_width=True,
        type="primary"
    )
    
    st.info(f"📍 {GRAFANA_URL}")
    
    # Try to check Grafana health
    try:
        response = requests.get(f"{GRAFANA_URL}/api/health", timeout=3)
        if response.status_code == 200:
            st.success("✅ Grafana is healthy")
        else:
            st.warning("⚠️ Grafana health check failed")
    except:
        st.error("❌ Cannot reach Grafana")

# Optional: Embed Grafana dashboard
with st.expander("🖼️ Embedded Dashboard (Experimental)"):
    st.markdown("""
        **Note**: Embedding may not work due to browser security settings.
        Use the button above to open Grafana in a new tab.
    """)
    
    # Example dashboard URL (customize based on your Grafana setup)
    dashboard_url = f"{GRAFANA_URL}/d/your-dashboard-id"
    
    st.markdown(f"""
        <iframe src="{dashboard_url}" width="100%" height="600" frameborder="0"></iframe>
    """, unsafe_allow_html=True)

st.markdown("---")

# 2. Prometheus Metrics Summary
st.header("2️⃣ Prometheus Metrics")

@st.cache_data(ttl=30)
def query_prometheus(query: str):
    """Query Prometheus API"""
    try:
        response = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params={"query": query},
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            if data["status"] == "success":
                return data["data"]["result"]
        return None
    except Exception as e:
        st.error(f"Error querying Prometheus: {e}")
        return None

try:
    # Define metrics to query
    metrics_queries = {
        "API Request Count": "http_requests_total",
        "API Error Rate": "rate(http_requests_total{status=~\"5..\"}[5m])",
        "Average Response Time": "rate(http_request_duration_seconds_sum[5m]) / rate(http_request_duration_seconds_count[5m])",
        "Active Predictions": "prediction_count_total"
    }
    
    st.subheader("Key Metrics")
    
    cols = st.columns(len(metrics_queries))
    
    for idx, (metric_name, query) in enumerate(metrics_queries.items()):
        with cols[idx]:
            result = query_prometheus(query)
            
            if result and len(result) > 0:
                value = result[0].get("value", [None, "N/A"])[1]
                try:
                    value_float = float(value)
                    if "Rate" in metric_name or "Time" in metric_name:
                        st.metric(metric_name, f"{value_float:.4f}")
                    else:
                        st.metric(metric_name, f"{int(value_float):,}")
                except:
                    st.metric(metric_name, str(value))
            else:
                st.metric(metric_name, "N/A")
    
    # Additional metrics
    with st.expander("📋 View More Metrics"):
        st.markdown("""
            Query Prometheus directly for specific metrics:
            
            - `up` - Service availability
            - `process_cpu_seconds_total` - CPU usage
            - `process_resident_memory_bytes` - Memory usage
            - `http_requests_total` - Total HTTP requests
            - `model_predictions_total` - Total predictions made
        """)
        
        custom_query = st.text_input("Custom Prometheus Query", value="up")
        
        if st.button("Execute Query"):
            result = query_prometheus(custom_query)
            if result:
                st.json(result)
            else:
                st.warning("No results or query failed")

except Exception as e:
    st.error(f"❌ Error fetching Prometheus metrics: {e}")
    st.info(f"💡 Make sure Prometheus is running at {PROMETHEUS_URL}")

st.markdown("---")

# 3. Inference Log Statistics
st.header("3️⃣ Inference Log Statistics")

# Look for inference log in multiple possible locations
log_paths = [
    "/app/data/monitoring/inference_log.csv",  # Docker container path
    "./data/monitoring/inference_log.csv",      # Relative path
    "../data/monitoring/inference_log.csv",     # Parent relative path
    str(Path(project_root).parent / "data" / "monitoring" / "inference_log.csv")  # Absolute path
]

inference_log = None
log_path_used = None

for log_path in log_paths:
    try:
        if os.path.exists(log_path):
            inference_log = pd.read_csv(log_path)
            log_path_used = log_path
            break
    except Exception as e:
        continue

if inference_log is not None and not inference_log.empty:
    st.success(f"✅ Loaded inference log from: {log_path_used}")
    
    # Parse timestamp if exists
    if 'timestamp' in inference_log.columns:
        inference_log['timestamp'] = pd.to_datetime(inference_log['timestamp'])
    
    # Statistics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_predictions = len(inference_log)
        st.metric("Total Predictions", f"{total_predictions:,}")
    
    with col2:
        if 'predicted_class' in inference_log.columns:
            unique_classes = inference_log['predicted_class'].nunique()
            st.metric("Unique Classes", unique_classes)
        else:
            st.metric("Unique Classes", "N/A")
    
    with col3:
        if 'confidence' in inference_log.columns:
            avg_confidence = inference_log['confidence'].mean()
            st.metric("Avg Confidence", f"{avg_confidence:.2%}")
        else:
            st.metric("Avg Confidence", "N/A")
    
    with col4:
        if 'timestamp' in inference_log.columns:
            last_prediction = inference_log['timestamp'].max()
            st.metric("Last Prediction", last_prediction.strftime("%Y-%m-%d %H:%M"))
        else:
            st.metric("Last Prediction", "N/A")
    
    # Predictions per class
    if 'predicted_class' in inference_log.columns:
        st.subheader("Predictions per Class")
        
        class_counts = inference_log['predicted_class'].value_counts().reset_index()
        class_counts.columns = ['Class', 'Count']
        
        fig = px.bar(
            class_counts.head(15),
            x='Class',
            y='Count',
            title='Top 15 Classes by Prediction Count',
            color='Count',
            color_continuous_scale='Viridis'
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    # Confidence distribution
    if 'confidence' in inference_log.columns:
        st.subheader("Confidence Distribution")
        
        fig = px.histogram(
            inference_log,
            x='confidence',
            nbins=50,
            title='Distribution of Prediction Confidence',
            labels={'confidence': 'Confidence', 'count': 'Frequency'}
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    # Recent predictions
    st.subheader("Recent Predictions")
    
    if 'timestamp' in inference_log.columns:
        recent_preds = inference_log.sort_values('timestamp', ascending=False).head(10)
    else:
        recent_preds = inference_log.tail(10)
    
    display_cols = [col for col in ['timestamp', 'predicted_class', 'confidence', 'designation'] 
                    if col in recent_preds.columns]
    
    st.dataframe(
        recent_preds[display_cols],
        use_container_width=True,
        hide_index=True
    )
    
    # Download option
    csv = inference_log.to_csv(index=False)
    st.download_button(
        label="📥 Download Full Log",
        data=csv,
        file_name="inference_log.csv",
        mime="text/csv",
        use_container_width=False
    )

else:
    st.warning("⚠️ No inference log found")
    st.info(f"💡 Inference logs will appear after making predictions via the API")
    
    with st.expander("📍 Searched Paths"):
        for path in log_paths:
            st.text(f"- {path}")

st.markdown("---")

# 4. System Health Overview
st.header("4️⃣ System Health Overview")

try:
    # Get Docker container health
    services_health = docker_manager.get_service_health()
    
    st.subheader("Container Status")
    
    # Create health summary table
    health_data = []
    for service_name, health in services_health.items():
        health_data.append({
            "Service": service_name,
            "Status": health["status"],
            "Container Running": "✅" if health["container_running"] else "❌",
            "URL Reachable": "✅" if health.get("url_reachable") else "N/A",
            "Port": health.get("port", "N/A")
        })
    
    health_df = pd.DataFrame(health_data)
    
    # Color code by status
    def highlight_status(row):
        if row['Status'] == 'healthy':
            return ['background-color: #d4edda'] * len(row)
        elif row['Status'] == 'starting':
            return ['background-color: #fff3cd'] * len(row)
        elif row['Status'] == 'down':
            return ['background-color: #f8d7da'] * len(row)
        return [''] * len(row)
    
    st.dataframe(
        health_df,
        use_container_width=True,
        hide_index=True
    )
    
    # System metrics
    st.subheader("System Resources")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Try to get container stats
        if docker_manager.client:
            try:
                # Count running containers
                containers = docker_manager.client.containers.list()
                st.metric("Running Containers", len(containers))
            except:
                st.metric("Running Containers", "N/A")
        else:
            st.metric("Running Containers", "N/A")
    
    with col2:
        # Container uptime (for API)
        if docker_manager.client:
            try:
                api_container = docker_manager.client.containers.get("rakuten_api")
                started = api_container.attrs['State']['StartedAt']
                started_dt = datetime.fromisoformat(started.replace('Z', '+00:00'))
                uptime = datetime.now(started_dt.tzinfo) - started_dt
                uptime_hours = uptime.total_seconds() / 3600
                st.metric("API Uptime", f"{uptime_hours:.1f}h")
            except:
                st.metric("API Uptime", "N/A")
        else:
            st.metric("API Uptime", "N/A")
    
    with col3:
        # Last model reload (from API health)
        try:
            response = requests.get(f"{API_URL}/health", timeout=3)
            if response.status_code == 200:
                health = response.json()
                model_info = health.get("model_info", {})
                loaded_at = model_info.get("loaded_at", "N/A")
                st.metric("Model Loaded At", loaded_at)
            else:
                st.metric("Model Loaded At", "N/A")
        except:
            st.metric("Model Loaded At", "N/A")
    
except Exception as e:
    st.error(f"❌ Error fetching system health: {e}")

# Quick links
st.markdown("---")
st.subheader("🔗 Monitoring Links")

col1, col2, col3 = st.columns(3)

with col1:
    st.link_button("📊 Grafana Dashboards", GRAFANA_URL, use_container_width=True)

with col2:
    st.link_button("🔍 Prometheus Queries", f"{PROMETHEUS_URL}/graph", use_container_width=True)

with col3:
    st.link_button("📖 API Documentation", f"{API_URL}/docs", use_container_width=True)

# Footer
st.markdown("---")
st.caption(f"""
    💡 Connected to:
    - Prometheus: {PROMETHEUS_URL}
    - Grafana: {GRAFANA_URL}
    - API: {API_URL}
""")
