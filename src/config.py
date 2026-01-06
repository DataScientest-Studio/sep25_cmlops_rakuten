"""
Configuration module for Rakuten MLOps Pipeline
Loads environment variables and provides configuration constants
"""
import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Project Paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_PATH = Path(os.getenv("DATA_PATH", PROJECT_ROOT / "data" / "raw"))
TRAINING_SNAPSHOTS_PATH = PROJECT_ROOT / "data" / "training_snapshots"

# PostgreSQL Configuration
POSTGRES_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": int(os.getenv("POSTGRES_PORT", "5432")),
    "database": os.getenv("POSTGRES_DB", "rakuten_db"),
    "user": os.getenv("POSTGRES_USER", "rakuten_user"),
    "password": os.getenv("POSTGRES_PASSWORD", "rakuten_pass"),
}

# Database connection string for SQLAlchemy
DATABASE_URL = (
    f"postgresql://{POSTGRES_CONFIG['user']}:{POSTGRES_CONFIG['password']}"
    f"@{POSTGRES_CONFIG['host']}:{POSTGRES_CONFIG['port']}/{POSTGRES_CONFIG['database']}"
)

# MLflow Configuration
MLFLOW_CONFIG = {
    "tracking_uri": os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000"),
    "experiment_dataset": "rakuten_dataset_versioning",
    "experiment_training": "rakuten_model_training",
}

# Data Pipeline Configuration
PIPELINE_CONFIG = {
    "initial_percentage": float(os.getenv("INITIAL_PERCENTAGE", "40")),
    "increment_percentage": float(os.getenv("INCREMENT_PERCENTAGE", "3")),
    "max_percentage": float(os.getenv("MAX_PERCENTAGE", "100")),
    "random_seed": int(os.getenv("RANDOM_SEED", "42")),
    "balancing_strategy": os.getenv("BALANCING_STRATEGY", "random_oversampling"),
}

# Airflow Configuration
AIRFLOW_CONFIG = {
    "schedule": os.getenv("AIRFLOW_SCHEDULE", "0 0 * * 1"),  # Every Monday at midnight
}

# Data Files
DATA_FILES = {
    "x_train": DATA_PATH / "X_train.csv",
    "y_train": DATA_PATH / "Y_train.csv",
    "x_test": DATA_PATH / "X_test.csv",
    "images_dir": DATA_PATH / "images" / "image_train",
}


def get_database_connection_string(for_airflow: bool = False) -> str:
    """
    Get database connection string
    
    Args:
        for_airflow: If True, returns connection string in format suitable for Airflow
        
    Returns:
        Database connection string
    """
    if for_airflow:
        return f"postgresql+psycopg2://{POSTGRES_CONFIG['user']}:{POSTGRES_CONFIG['password']}@{POSTGRES_CONFIG['host']}:{POSTGRES_CONFIG['port']}/{POSTGRES_CONFIG['database']}"
    return DATABASE_URL


def validate_config() -> bool:
    """
    Validate configuration and check if required files exist
    
    Returns:
        True if configuration is valid, False otherwise
    """
    errors = []
    
    # Check if data files exist (only in production, not in Docker)
    if os.getenv("ENVIRONMENT") != "docker":
        for name, path in DATA_FILES.items():
            if name != "images_dir" and not path.exists():
                errors.append(f"Missing data file: {path}")
        
        if not DATA_FILES["images_dir"].exists():
            errors.append(f"Missing images directory: {DATA_FILES['images_dir']}")
    
    # Validate pipeline configuration
    if not (0 <= PIPELINE_CONFIG["initial_percentage"] <= 100):
        errors.append("initial_percentage must be between 0 and 100")
    
    if not (0 < PIPELINE_CONFIG["increment_percentage"] <= 100):
        errors.append("increment_percentage must be between 0 and 100")
    
    if errors:
        for error in errors:
            print(f"Config Error: {error}")
        return False
    
    return True


def create_directories():
    """Create necessary directories if they don't exist"""
    TRAINING_SNAPSHOTS_PATH.mkdir(parents=True, exist_ok=True)
    DATA_PATH.mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    print("=== Rakuten MLOps Configuration ===\n")
    print(f"Project Root: {PROJECT_ROOT}")
    print(f"Data Path: {DATA_PATH}")
    print(f"Database URL: {DATABASE_URL}")
    print(f"MLflow Tracking URI: {MLFLOW_CONFIG['tracking_uri']}")
    print(f"\nPipeline Config:")
    for key, value in PIPELINE_CONFIG.items():
        print(f"  {key}: {value}")
    
    print(f"\nConfiguration Valid: {validate_config()}")
