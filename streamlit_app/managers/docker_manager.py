"""
Docker Manager

Manages Docker containers and health checks.
"""
import docker
import logging
import requests
from typing import Dict, List
import streamlit as st

logger = logging.getLogger(__name__)


class DockerManager:
    """Manages Docker operations and health checks"""

    def __init__(self):
        try:
            self.client = docker.from_env()
        except Exception as e:
            logger.warning(f"Could not connect to Docker: {e}")
            self.client = None

    @st.cache_data(ttl=10)
    def get_service_health(_self) -> Dict[str, Dict]:
        """
        Get health status of all services.

        Returns:
            Dictionary mapping service names to health info
        """
        services = {
            "PostgreSQL": {
                "url": None,
                "container": "rakuten_postgres",
                "expected_port": 5432,
            },
            "MLflow": {
                "url": "http://localhost:5000/health",
                "container": "rakuten_mlflow",
                "expected_port": 5000,
            },
            "Airflow": {
                "url": "http://localhost:8080/health",
                "container": "rakuten_airflow_webserver",
                "expected_port": 8080,
            },
            "API": {
                "url": "http://localhost:8000/health",
                "container": "rakuten_api",
                "expected_port": 8000,
            },
            "Prometheus": {
                "url": "http://localhost:9090/-/healthy",
                "container": "rakuten_prometheus",
                "expected_port": 9090,
            },
            "Grafana": {
                "url": "http://localhost:3000/api/health",
                "container": "rakuten_grafana",
                "expected_port": 3000,
            },
        }

        results = {}

        for service_name, config in services.items():
            status = {
                "status": "unknown",
                "container_running": False,
                "url_reachable": False,
                "url": config["url"],
                "port": config["expected_port"],
            }

            # Check container status
            if _self.client:
                try:
                    container = _self.client.containers.get(config["container"])
                    status["container_running"] = container.status == "running"
                except:
                    status["container_running"] = False

            # Check URL reachability
            if config["url"]:
                try:
                    response = requests.get(config["url"], timeout=2)
                    status["url_reachable"] = response.status_code < 500
                except:
                    status["url_reachable"] = False

            # Determine overall status
            if config["url"]:
                # URL-based service
                if status["url_reachable"]:
                    status["status"] = "healthy"
                elif status["container_running"]:
                    status["status"] = "starting"
                else:
                    status["status"] = "down"
            else:
                # Container-only service (like PostgreSQL)
                if status["container_running"]:
                    status["status"] = "healthy"
                else:
                    status["status"] = "down"

            results[service_name] = status

        return results

    def start_stack(self, compose_file: str) -> bool:
        """Start Docker Compose stack"""
        try:
            import subprocess

            result = subprocess.run(
                ["docker-compose", "-f", compose_file, "up", "-d"],
                capture_output=True,
                text=True,
                timeout=120,
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Failed to start stack: {e}")
            return False

    def stop_stack(self, compose_file: str) -> bool:
        """Stop Docker Compose stack"""
        try:
            import subprocess

            result = subprocess.run(
                ["docker-compose", "-f", compose_file, "down"],
                capture_output=True,
                text=True,
                timeout=60,
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Failed to stop stack: {e}")
            return False

    def restart_container(self, container_name: str) -> bool:
        """Restart a specific container"""
        if not self.client:
            return False

        try:
            container = self.client.containers.get(container_name)
            container.restart(timeout=30)
            return True
        except Exception as e:
            logger.error(f"Failed to restart container: {e}")
            return False

    def get_container_logs(self, container_name: str, lines: int = 100) -> str:
        """Get recent logs from container"""
        if not self.client:
            return "Docker client not available"

        try:
            container = self.client.containers.get(container_name)
            logs = container.logs(tail=lines).decode("utf-8")
            return logs
        except Exception as e:
            return f"Error getting logs: {e}"


# Global instance
docker_manager = DockerManager()
