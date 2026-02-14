"""
Docker Status Component

Reusable component for displaying Docker container status across pages.
"""
import streamlit as st
from typing import List, Optional


def render_docker_status(
    docker_manager, 
    focus_services: Optional[List[str]] = None,
    show_all: bool = True
):
    """
    Render Docker container status header.
    
    Args:
        docker_manager: DockerManager instance
        focus_services: Optional list of service names to highlight
        show_all: Whether to show all services or only focused ones
    """
    st.markdown("---")
    st.subheader("🐳 Docker Services Status")
    
    # Get service health
    try:
        services_health = docker_manager.get_service_health()
    except Exception as e:
        st.error(f"❌ Could not get Docker status: {e}")
        return
    
    # Filter services if needed
    if focus_services and not show_all:
        services_to_show = {k: v for k, v in services_health.items() if k in focus_services}
    else:
        services_to_show = services_health
    
    # Create columns for status display
    cols = st.columns(len(services_to_show))
    
    for idx, (service_name, health) in enumerate(services_to_show.items()):
        with cols[idx]:
            # Determine status indicator
            status = health.get("status", "unknown")
            
            if status == "healthy":
                indicator = "🟢"
                status_text = "Healthy"
                col_type = "success"
            elif status == "starting":
                indicator = "🟡"
                status_text = "Starting"
                col_type = "warning"
            elif status == "down":
                indicator = "🔴"
                status_text = "Down"
                col_type = "error"
            else:
                indicator = "⚪"
                status_text = "Unknown"
                col_type = "info"
            
            # Highlight focused services
            is_focused = focus_services and service_name in focus_services
            
            if is_focused:
                st.markdown(f"**{indicator} {service_name}**")
            else:
                st.markdown(f"{indicator} {service_name}")
            
            st.caption(status_text)
            
            # Show additional info on hover (in expander)
            if st.session_state.get("show_details", False):
                with st.expander("Details", expanded=False):
                    st.text(f"Container: {health.get('container_running', 'N/A')}")
                    st.text(f"Port: {health.get('port', 'N/A')}")
    
    st.markdown("---")


def render_compact_status(docker_manager, focus_services: Optional[List[str]] = None):
    """
    Render a compact one-line status display.
    
    Args:
        docker_manager: DockerManager instance
        focus_services: Optional list of service names to show
    """
    try:
        services_health = docker_manager.get_service_health()
        
        # Filter services if specified
        if focus_services:
            services_to_show = {k: v for k, v in services_health.items() if k in focus_services}
        else:
            services_to_show = services_health
        
        # Build status string
        status_parts = []
        for service_name, health in services_to_show.items():
            status = health.get("status", "unknown")
            
            if status == "healthy":
                indicator = "🟢"
            elif status == "starting":
                indicator = "🟡"
            elif status == "down":
                indicator = "🔴"
            else:
                indicator = "⚪"
            
            status_parts.append(f"{indicator} {service_name}")
        
        st.info(" | ".join(status_parts))
        
    except Exception as e:
        st.warning(f"Could not get Docker status: {e}")
