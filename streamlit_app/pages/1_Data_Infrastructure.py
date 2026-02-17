"""
Data & Infrastructure Status

Monitor Docker services, database state, and data evolution tracking.
"""
import streamlit as st
import sys
from pathlib import Path
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
import plotly.express as px
import os

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Add streamlit_app to path for local imports
streamlit_app_root = Path(__file__).parent.parent
sys.path.insert(0, str(streamlit_app_root))

from managers.docker_manager import docker_manager
from managers.pipeline_executor import run_data_loader, get_data_status
from utils.env_config import get_db_config

# Page configuration
st.set_page_config(
    page_title="Data & Infrastructure - Rakuten MLOps",
    page_icon="🗄️",
    layout="wide"
)

st.title("Data & Infrastructure Status")

# =============================================================================
# SECTION 1: DOCKER SERVICES STATUS
# =============================================================================
st.header("1️⃣ Docker Services")

try:
    services_health = docker_manager.get_service_health()
    
    cols = st.columns(len(services_health))
    
    for idx, (service_name, info) in enumerate(services_health.items()):
        with cols[idx]:
            status = info["status"]
            
            if status == "healthy":
                st.success(f"**{service_name}**\n\n✅ Healthy")
            elif status == "unhealthy":
                st.error(f"**{service_name}**\n\n❌ Unhealthy")
            else:
                st.warning(f"**{service_name}**\n\n⚠️ {status}")
            
            if info.get("url"):
                st.caption(f"[Open]({info['url']})")

except Exception as e:
    st.error(f"❌ Could not check Docker services: {e}")
    st.info("Make sure Docker services are running: `make start`")

st.markdown("---")

# =============================================================================
# SECTION 2: DATABASE STATUS
# =============================================================================
st.header("2️⃣ Database Status")

# Database connection config
# Automatically loads from .env file and st.secrets
DB_CONFIG = get_db_config()

@st.cache_data(ttl=30)
def get_database_stats():
    """Get current database statistics"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get current state
        cursor.execute("""
            SELECT 
                COUNT(*) as total_products,
                COUNT(DISTINCT l.prdtypecode) as total_classes
            FROM products p
            LEFT JOIN labels l ON p.productid = l.productid
        """)
        stats = cursor.fetchone()
        
        # Get current percentage
        cursor.execute("""
            SELECT percentage, total_rows, completed_at
            FROM data_loads
            WHERE status = 'completed'
            ORDER BY percentage DESC
            LIMIT 1
        """)
        load_info = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        return {
            'total_products': stats['total_products'] if stats else 0,
            'total_classes': stats['total_classes'] if stats else 0,
            'current_percentage': float(load_info['percentage']) if load_info else 0,
            'last_load_date': load_info['completed_at'] if load_info else None
        }
    except Exception as e:
        st.error(f"Database connection error: {e}")
        return None

stats = get_database_stats()

if stats:
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Products", f"{stats['total_products']:,}")
    
    with col2:
        st.metric("Product Classes", stats['total_classes'])
    
    with col3:
        st.metric("Data Loaded", f"{stats['current_percentage']:.1f}%")
    
    with col4:
        next_pct = min(stats['current_percentage'] + 3, 100)
        st.metric("Next Load", f"{next_pct:.1f}%")
    
    # Progress bar
    progress = stats['current_percentage'] / 100
    st.progress(progress)
    st.caption(f"Last updated: {stats['last_load_date'].strftime('%Y-%m-%d %H:%M') if stats['last_load_date'] else 'Never'}")

else:
    st.warning("⚠️ Could not connect to database")
    st.info("Run `make init-db` to initialize the database")

st.markdown("---")

# =============================================================================
# SECTION 3: DATA EVOLUTION TRACKING
# =============================================================================
st.header("3️⃣ Data Evolution Tracking")

st.markdown("""
Track incremental data loading and changes over time. Each batch is logged in the database audit trail.
""")

@st.cache_data(ttl=30)
def get_load_history():
    """Get data loading history"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        
        query = """
        SELECT 
            batch_name,
            percentage,
            total_rows,
            started_at,
            completed_at,
            status
        FROM data_loads
        WHERE status = 'completed'
        ORDER BY percentage ASC
        """
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        return df
    except Exception as e:
        return None

history_df = get_load_history()

if history_df is not None and len(history_df) > 0:
    
    # Chart: Data growth over time
    fig = px.line(
        history_df, 
        x='completed_at', 
        y='percentage',
        markers=True,
        title='Data Loading Progress Over Time',
        labels={'completed_at': 'Date', 'percentage': 'Percentage (%)'}
    )
    fig.update_traces(line_color='#1f77b4', marker=dict(size=10))
    st.plotly_chart(fig, use_container_width=True)
    
    # History table
    st.subheader("Loading History")
    
    display_df = history_df.copy()
    display_df['started_at'] = pd.to_datetime(display_df['started_at']).dt.strftime('%Y-%m-%d %H:%M')
    display_df['completed_at'] = pd.to_datetime(display_df['completed_at']).dt.strftime('%Y-%m-%d %H:%M')
    display_df['percentage'] = display_df['percentage'].apply(lambda x: f"{x:.1f}%")
    display_df['total_rows'] = display_df['total_rows'].apply(lambda x: f"{x:,}")
    
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "batch_name": "Batch",
            "percentage": "Loaded",
            "total_rows": "Rows",
            "started_at": "Started",
            "completed_at": "Completed",
            "status": "Status"
        }
    )
else:
    st.info("No data loading history yet. Initialize the database first.")

st.markdown("---")

# =============================================================================
# SECTION 4: CLASS DISTRIBUTION
# =============================================================================
st.header("4️⃣ Current Class Distribution")

@st.cache_data(ttl=30)
def get_class_distribution():
    """Get current class distribution"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        
        query = """
        SELECT 
            l.prdtypecode,
            COUNT(*) as count
        FROM labels l
        JOIN products p ON p.productid = l.productid
        GROUP BY l.prdtypecode
        ORDER BY count DESC
        """
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        return df
    except Exception as e:
        return None

dist_df = get_class_distribution()

if dist_df is not None and len(dist_df) > 0:
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Bar chart
        fig = px.bar(
            dist_df,
            x='prdtypecode',
            y='count',
            title='Products per Class',
            labels={'prdtypecode': 'Product Type Code', 'count': 'Count'}
        )
        fig.update_traces(marker_color='#1f77b4')
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("Statistics")
        
        total = dist_df['count'].sum()
        mean_count = dist_df['count'].mean()
        min_count = dist_df['count'].min()
        max_count = dist_df['count'].max()
        imbalance_ratio = max_count / min_count if min_count > 0 else 0
        
        st.metric("Total Products", f"{total:,}")
        st.metric("Classes", len(dist_df))
        st.metric("Avg per Class", f"{mean_count:.0f}")
        st.metric("Min Count", f"{min_count:,}")
        st.metric("Max Count", f"{max_count:,}")
        st.metric("Imbalance Ratio", f"{imbalance_ratio:.2f}")

else:
    st.info("No class distribution data available yet")

st.markdown("---")

# =============================================================================
# SECTION 5: LOAD MORE DATA ACTION
# =============================================================================
st.header("5️⃣ Load More Data")

st.markdown("""
Load the next increment of data (3%) to simulate database evolution.
This will trigger the actual data loading script.
""")

col1, col2, col3 = st.columns([1, 1, 2])

with col1:
    if st.button("Load Next 3%", type="primary", use_container_width=True):
        if stats and stats['current_percentage'] >= 100:
            st.warning("⚠️ Already at 100% data loaded")
        else:
            with st.spinner("Loading data... This may take 30-60 seconds"):
                result = run_data_loader()
                
                if result['success']:
                    st.success(f"✅ {result['message']}")
                    st.balloons()
                    # Clear cache to refresh all data
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error(f"❌ {result['message']}")

with col2:
    if st.button("Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

with col3:
    st.caption("Each load adds ~3% more products to the database")

# Footer
st.markdown("---")
st.caption("Database tracks all changes in audit trail for reproducibility")
