"""
Database Pipeline Page

Monitor data ingestion, class distribution, and data loads.
"""
import streamlit as st
import sys
from pathlib import Path
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
import plotly.express as px
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
    page_title="Database Pipeline - Rakuten MLOps",
    page_icon="📊",
    layout="wide"
)

# Title
st.title("📊 Database Pipeline")
st.markdown("Monitor data ingestion and database state")

# Docker status header
render_docker_status(docker_manager, focus_services=["PostgreSQL"], show_all=True)

# Database connection settings
DB_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": int(os.getenv("POSTGRES_PORT", 5432)),
    "database": os.getenv("POSTGRES_DB", "rakuten_db"),
    "user": os.getenv("POSTGRES_USER", "rakuten_user"),
    "password": os.getenv("POSTGRES_PASSWORD", "change_this_password")
}

@st.cache_resource(ttl=30)
def get_db_connection():
    """Create database connection"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        st.error(f"❌ Could not connect to database: {e}")
        st.info("💡 Make sure PostgreSQL container is running and accessible")
        return None

@st.cache_data(ttl=10)
def query_database(query: str):
    """Execute query and return results as DataFrame"""
    conn = get_db_connection()
    if conn is None:
        return None
    
    try:
        df = pd.read_sql_query(query, conn)
        return df
    except Exception as e:
        st.error(f"❌ Query failed: {e}")
        return None

def query_database_dict(query: str):
    """Execute query and return results as list of dicts"""
    conn = get_db_connection()
    if conn is None:
        return None
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query)
            results = cur.fetchall()
        return results
    except Exception as e:
        st.error(f"❌ Query failed: {e}")
        return None

# Refresh button
col1, col2 = st.columns([6, 1])
with col2:
    if st.button("🔄 Refresh", use_container_width=True):
        st.cache_data.clear()
        st.cache_resource.clear()
        st.rerun()

# 1. Current Data State
st.header("1️⃣ Current Data State")

data_state = query_database_dict("SELECT * FROM current_data_state;")

if data_state and len(data_state) > 0:
    state = data_state[0]
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        percentage = float(state.get('percentage', 0))
        st.metric("Percentage Loaded", f"{percentage}%")
    
    with col2:
        total_rows = state.get('actual_rows', 0)
        st.metric("Total Rows", f"{total_rows:,}")
    
    with col3:
        last_load = state.get('completed_at', 'N/A')
        if isinstance(last_load, datetime):
            last_load_str = last_load.strftime("%Y-%m-%d %H:%M")
        else:
            last_load_str = str(last_load) if last_load else "N/A"
        st.metric("Last Load", last_load_str)
    
    with col4:
        total_classes = state.get('num_classes', 0)
        st.metric("Total Classes", total_classes)
    
    # Progress bar
    st.progress(percentage / 100.0)
    
else:
    st.warning("⚠️ No data state information available. Database may be empty.")

st.markdown("---")

# 2. Class Distribution
st.header("2️⃣ Class Distribution")

class_dist = query_database("SELECT * FROM class_distribution ORDER BY count DESC;")

if class_dist is not None and not class_dist.empty:
    # Show top classes
    st.subheader("Top Product Classes")
    
    # Create bar chart
    fig = px.bar(
        class_dist,
        x='prdtypecode',
        y='count',
        title='Products per Class',
        labels={'prdtypecode': 'Product Class', 'count': 'Count'},
        color='count',
        color_continuous_scale='Blues'
    )
    fig.update_layout(height=400, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)
    
    # Statistics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Classes", len(class_dist))
    
    with col2:
        avg_count = class_dist['count'].mean()
        st.metric("Avg Products/Class", f"{avg_count:.0f}")
    
    with col3:
        max_count = class_dist['count'].max()
        st.metric("Max Products/Class", f"{max_count:,}")
    
    # Detailed table
    with st.expander("📋 View Detailed Distribution"):
        st.dataframe(
            class_dist,
            use_container_width=True,
            hide_index=True
        )
else:
    st.warning("⚠️ No class distribution data available")

st.markdown("---")

# 3. Sample Products
st.header("3️⃣ Sample Products")

col1, col2 = st.columns([6, 1])
with col1:
    st.subheader("Random Product Samples")
with col2:
    if st.button("🎲 New Sample", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

sample_products = query_database("""
    SELECT 
        p.productid,
        p.designation,
        LEFT(p.description, 100) as description_preview,
        l.prdtypecode
    FROM products p
    LEFT JOIN labels l ON p.productid = l.productid
    ORDER BY RANDOM()
    LIMIT 10;
""")

if sample_products is not None and not sample_products.empty:
    # Format the dataframe
    sample_products['description_preview'] = sample_products['description_preview'].apply(
        lambda x: f"{x}..." if x and len(x) == 100 else x
    )
    
    st.dataframe(
        sample_products,
        use_container_width=True,
        hide_index=True,
        column_config={
            "productid": "Product ID",
            "designation": "Designation",
            "description_preview": "Description (Preview)",
            "prdtypecode": "Class"
        }
    )
else:
    st.warning("⚠️ No products available in database")

st.markdown("---")

# 4. Recent Loads History
st.header("4️⃣ Recent Loads History")

recent_loads = query_database("""
    SELECT 
        id as load_id,
        batch_name as batch_number,
        total_rows as rows_loaded,
        percentage as cumulative_percentage,
        started_at,
        completed_at,
        status
    FROM data_loads
    ORDER BY completed_at DESC NULLS LAST
    LIMIT 5;
""")

if recent_loads is not None and not recent_loads.empty:
    # Format dates
    if 'started_at' in recent_loads.columns:
        recent_loads['started_at'] = pd.to_datetime(recent_loads['started_at']).dt.strftime('%Y-%m-%d %H:%M')
    if 'completed_at' in recent_loads.columns:
        recent_loads['completed_at'] = pd.to_datetime(recent_loads['completed_at']).dt.strftime('%Y-%m-%d %H:%M')
    
    # Display table with color coding for status
    def highlight_status(row):
        if row['status'] == 'completed':
            return ['background-color: #d4edda'] * len(row)
        elif row['status'] == 'failed':
            return ['background-color: #f8d7da'] * len(row)
        else:
            return [''] * len(row)
    
    st.dataframe(
        recent_loads,
        use_container_width=True,
        hide_index=True,
        column_config={
            "load_id": "Load ID",
            "batch_number": "Batch #",
            "rows_loaded": "Rows Loaded",
            "cumulative_percentage": st.column_config.NumberColumn(
                "Cumulative %",
                format="%.1f%%"
            ),
            "started_at": "Started",
            "completed_at": "Completed",
            "status": "Status"
        }
    )
    
    # Summary metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        total_loads = len(recent_loads)
        st.metric("Total Loads (Recent)", total_loads)
    
    with col2:
        total_rows_loaded = recent_loads['rows_loaded'].sum()
        st.metric("Total Rows Loaded", f"{total_rows_loaded:,}")
    
    with col3:
        successful_loads = len(recent_loads[recent_loads['status'] == 'completed'])
        st.metric("Successful Loads", f"{successful_loads}/{total_loads}")
else:
    st.warning("⚠️ No recent load history available")

# Footer
st.markdown("---")
st.caption("💡 Tip: Use the refresh button to update data, or wait 30 seconds for automatic cache refresh")
