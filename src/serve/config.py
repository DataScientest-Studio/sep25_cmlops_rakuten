"""
Configuration for FastAPI Service
"""
import os
from pathlib import Path

# MLflow Configuration
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
MLFLOW_S3_ENDPOINT_URL = os.getenv("MLFLOW_S3_ENDPOINT_URL", "http://minio:9000")

# Model Configuration
MODEL_NAME = os.getenv("MODEL_NAME", "rakuten_classifier")
MODEL_STAGE = os.getenv("MODEL_STAGE", "Production")
MODEL_RELOAD_INTERVAL = int(os.getenv("MODEL_RELOAD_INTERVAL", "300"))  # seconds

# API Configuration
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
API_WORKERS = int(os.getenv("API_WORKERS", "2"))

# Inference Logging
INFERENCE_LOG_PATH = os.getenv(
    "INFERENCE_LOG_PATH", "/app/data/monitoring/inference_log.csv"
)
INFERENCE_LOG_MAX_ROWS = int(os.getenv("INFERENCE_LOG_MAX_ROWS", "100000"))

# PostgreSQL Configuration (optional, for dataset stats)
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.getenv("POSTGRES_DB", "rakuten_db")
POSTGRES_USER = os.getenv("POSTGRES_USER", "rakuten_user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "rakuten_pass")

# Ensure directories exist
Path(INFERENCE_LOG_PATH).parent.mkdir(parents=True, exist_ok=True)
