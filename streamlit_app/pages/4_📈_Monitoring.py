"""
Drift & Monitoring

System monitoring, drift detection, and inference analysis.
"""
import streamlit as st
import sys
from pathlib import Path
import pandas as pd
import requests
import os
from datetime import datetime
import plotly.express as px

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Add streamlit_app to path
streamlit_app_root = Path(__file__).parent.parent
sys.path.insert(0, str(streamlit_app_root))

from managers.docker_manager import docker_manager

# Page configuration
st.set_page_config(
    page_title="Monitoring - Rakuten MLOps",
    page_icon="📈",
    layout="wide"
)

st.title("📈 Drift & Monitoring")

# Configuration
API_URL = os.getenv("API_URL", "http://localhost:8000")
PROMETHEUS_URL = "http://localhost:9090"
GRAFANA_URL = "http://localhost:3000"

# Refresh button
col1, col2 = st.columns([6, 1])
with col2:
    if st.button("🔄 Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# =============================================================================
# SECTION 1: SYSTEM HEALTH
# =============================================================================
st.header("1️⃣ System Health")

try:
    services_health = docker_manager.get_service_health()
    
    # Overall health
    healthy_count = sum(1 for s in services_health.values() if s["status"] == "healthy")
    total_count = len(services_health)
    health_percentage = (healthy_count / total_count * 100) if total_count > 0 else 0
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Services Running", f"{healthy_count}/{total_count}")
    
    with col2:
        st.metric("System Health", f"{health_percentage:.0f}%")
    
    with col3:
        if healthy_count == total_count:
            st.success("**Status**\n\n🟢 All Healthy")
        elif healthy_count > 0:
            st.warning("**Status**\n\n🟡 Degraded")
        else:
            st.error("**Status**\n\n🔴 Down")
    
    # Service details
    with st.expander("🔍 Service Details"):
        for service_name, info in services_health.items():
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.text(f"{service_name}")
            
            with col2:
                status = info["status"]
                if status == "healthy":
                    st.success("✅")
                elif status == "unhealthy":
                    st.error("❌")
                else:
                    st.warning("⚠️")

except Exception as e:
    st.error(f"❌ Could not check system health: {e}")

st.markdown("---")

# =============================================================================
# SECTION 2: API METRICS
# =============================================================================
st.header("2️⃣ API Metrics")

st.markdown("""
Prometheus metrics exposed by the FastAPI service:
- Total predictions
- Prediction latency
- Input text characteristics
- Model version info
""")

try:
    # Try to fetch metrics from API
    response = requests.get(f"{API_URL}/metrics", timeout=5)
    
    if response.status_code == 200:
        metrics_text = response.text
        
        # Parse key metrics
        lines = metrics_text.split('\n')
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 Key Metrics")
            
            # Extract prediction count
            for line in lines:
                if line.startswith('rakuten_predictions_total'):
                    try:
                        count = float(line.split()[-1])
                        st.metric("Total Predictions", f"{count:.0f}")
                    except:
                        pass
            
            # Model version
            for line in lines:
                if line.startswith('rakuten_model_version{'):
                    st.caption(line)
        
        with col2:
            st.subheader("📈 Raw Metrics")
            
            # Show first 20 lines
            preview_lines = [l for l in lines if l and not l.startswith('#')][:20]
            st.code('\n'.join(preview_lines), language='text')
        
        # Full metrics
        with st.expander("📋 Full Metrics Output"):
            st.code(metrics_text, language='text')
        
        st.info(f"💡 View full metrics in Prometheus: {PROMETHEUS_URL}")
    
    else:
        st.warning(f"⚠️ Could not fetch metrics (status {response.status_code})")

except requests.exceptions.ConnectionError:
    st.warning("⚠️ API not reachable - no metrics available")
    st.info("💡 Start the API to see metrics: `docker compose up api`")
except Exception as e:
    st.error(f"❌ Error fetching metrics: {e}")

st.markdown("---")

# =============================================================================
# SECTION 3: INFERENCE LOGS
# =============================================================================
st.header("3️⃣ Inference Logs")

st.markdown("""
All predictions are logged to CSV for drift analysis. Monitor:
- Prediction distribution over time
- Confidence scores
- Input text characteristics
""")

@st.cache_data(ttl=30)
def load_inference_logs():
    """Load inference logs from CSV"""
    try:
        log_path = project_root / "data" / "monitoring" / "inference_log.csv"
        
        if log_path.exists():
            df = pd.read_csv(log_path)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            return df
        else:
            return None
    except Exception as e:
        st.error(f"Error loading logs: {e}")
        return None

logs_df = load_inference_logs()

if logs_df is not None and len(logs_df) > 0:
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Predictions", len(logs_df))
    
    with col2:
        avg_confidence = logs_df['confidence'].mean()
        st.metric("Avg Confidence", f"{avg_confidence:.2%}")
    
    with col3:
        unique_classes = logs_df['predicted_class'].nunique()
        st.metric("Unique Classes", unique_classes)
    
    with col4:
        if 'model_version' in logs_df.columns:
            current_version = logs_df['model_version'].mode()[0] if len(logs_df['model_version'].mode()) > 0 else "N/A"
            st.metric("Model Version", current_version)
    
    # Prediction distribution over time
    st.subheader("📊 Predictions Over Time")
    
    # Resample by hour
    logs_df_hourly = logs_df.set_index('timestamp').resample('H').size().reset_index(name='count')
    
    fig = px.line(
        logs_df_hourly,
        x='timestamp',
        y='count',
        title='Predictions per Hour',
        labels={'timestamp': 'Time', 'count': 'Predictions'}
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Class distribution
    st.subheader("🎯 Predicted Class Distribution")
    
    class_dist = logs_df['predicted_class'].value_counts().head(10)
    
    fig = px.bar(
        x=class_dist.index,
        y=class_dist.values,
        title='Top 10 Predicted Classes',
        labels={'x': 'Class', 'y': 'Count'}
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Confidence distribution
    st.subheader("📈 Confidence Score Distribution")
    
    fig = px.histogram(
        logs_df,
        x='confidence',
        nbins=20,
        title='Confidence Score Distribution',
        labels={'confidence': 'Confidence', 'count': 'Frequency'}
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Recent predictions
    st.subheader("📋 Recent Predictions")
    
    recent_logs = logs_df.tail(20).sort_values('timestamp', ascending=False)
    
    display_df = recent_logs[['timestamp', 'designation', 'predicted_class', 'confidence']].copy()
    display_df['timestamp'] = display_df['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
    display_df['confidence'] = display_df['confidence'].apply(lambda x: f"{x:.2%}")
    display_df['designation'] = display_df['designation'].str[:50] + '...'
    
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "timestamp": "Time",
            "designation": "Product",
            "predicted_class": "Class",
            "confidence": "Confidence"
        }
    )

else:
    st.info("📭 No inference logs yet. Make some predictions first!")
    st.caption("💡 Go to Promotion page and test predictions")

st.markdown("---")

# =============================================================================
# SECTION 4: DRIFT DETECTION
# =============================================================================
st.header("4️⃣ Drift Detection")

st.markdown("""
Monitor for data drift by comparing current predictions with training distribution.
Key indicators:
- Change in class distribution
- Confidence score trends
- Input text characteristics
""")

if logs_df is not None and len(logs_df) > 10:
    
    # Simple drift indicators
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("⚠️ Drift Indicators")
        
        # Confidence trend
        recent = logs_df.tail(50)
        older = logs_df.head(50) if len(logs_df) > 100 else logs_df.head(len(logs_df) // 2)
        
        recent_conf = recent['confidence'].mean()
        older_conf = older['confidence'].mean()
        conf_change = ((recent_conf - older_conf) / older_conf * 100) if older_conf > 0 else 0
        
        st.metric(
            "Confidence Change",
            f"{recent_conf:.2%}",
            delta=f"{conf_change:+.1f}%",
            help="Comparing last 50 vs first 50 predictions"
        )
        
        # Class diversity
        recent_classes = recent['predicted_class'].nunique()
        older_classes = older['predicted_class'].nunique()
        
        st.metric(
            "Class Diversity",
            f"{recent_classes} classes",
            delta=f"{recent_classes - older_classes:+d}",
            help="Number of unique classes in recent predictions"
        )
    
    with col2:
        st.subheader("💡 Recommendations")
        
        if conf_change < -10:
            st.warning("⚠️ Confidence drop detected - consider retraining")
        elif conf_change > 10:
            st.success("✅ Confidence improving")
        else:
            st.info("ℹ️ Confidence stable")
        
        if recent_classes < older_classes * 0.7:
            st.warning("⚠️ Prediction diversity decreased")
        else:
            st.success("✅ Prediction diversity healthy")
        
        st.caption("💡 For detailed drift analysis, use Evidently library")

else:
    st.info("📊 Need more predictions for drift analysis (minimum 10)")

st.markdown("---")

# =============================================================================
# SECTION 5: EXTERNAL DASHBOARDS
# =============================================================================
st.header("5️⃣ External Dashboards")

st.markdown("""
Access external monitoring tools for deeper analysis.
""")

col1, col2 = st.columns(2)

with col1:
    st.subheader("🔥 Prometheus")
    st.markdown(f"[Open Prometheus]({PROMETHEUS_URL})")
    st.caption("Query raw metrics and set up alerts")
    
    st.markdown("**Useful queries:**")
    st.code("rate(rakuten_predictions_total[5m])")
    st.code("histogram_quantile(0.95, rakuten_prediction_latency_seconds)")

with col2:
    st.subheader("📊 Grafana")
    st.markdown(f"[Open Grafana]({GRAFANA_URL})")
    st.caption("Visualize metrics with dashboards")
    
    st.info("""
    **Login**: admin / admin
    
    Create dashboards for:
    - Prediction rate over time
    - Latency percentiles
    - Error rates
    - Model version tracking
    """)

# Footer
st.markdown("---")
st.caption("💡 All inference logs are stored in data/monitoring/inference_log.csv")
