#!/usr/bin/env python3
"""
Train Baseline Model Script

Trains an initial TF-IDF + LogisticRegression model from the database and registers it to MLflow.

Usage:
    python scripts/train_baseline_model.py [--auto-promote]
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
import pandas as pd
import logging
import argparse
from sqlalchemy import create_engine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def load_data_from_database():
    """Load training data from PostgreSQL database"""
    logger.info("Loading data from database...")

    # Get database connection from environment
    postgres_host = os.getenv("POSTGRES_HOST", "localhost")
    postgres_port = os.getenv("POSTGRES_PORT", "5432")
    postgres_db = os.getenv("POSTGRES_DB", "rakuten_db")
    postgres_user = os.getenv("POSTGRES_USER", "rakuten_user")
    postgres_password = os.getenv("POSTGRES_PASSWORD", "rakuten_pass")

    connection_string = (
        f"postgresql://{postgres_user}:{postgres_password}@"
        f"{postgres_host}:{postgres_port}/{postgres_db}"
    )

    engine = create_engine(connection_string)

    # Load products and labels
    query = """
    SELECT 
        p.productid,
        p.designation,
        p.description,
        p.imageid,
        p.image_path,
        l.prdtypecode
    FROM products p
    JOIN labels l ON p.productid = l.productid
    ORDER BY p.productid
    """

    df = pd.read_sql(query, engine)
    engine.dispose()

    logger.info(f"Loaded {len(df)} samples from database")
    logger.info(f"Classes: {df['prdtypecode'].nunique()}")

    return df


def main():
    parser = argparse.ArgumentParser(description="Train baseline Rakuten classifier")
    parser.add_argument(
        "--auto-promote",
        action="store_true",
        help="Automatically promote to Production if F1 > 0.70",
    )
    parser.add_argument(
        "--max-features",
        type=int,
        default=5000,
        help="Maximum TF-IDF features (default: 5000)",
    )
    parser.add_argument(
        "--C", type=float, default=1.0, help="Regularization parameter (default: 1.0)"
    )

    args = parser.parse_args()

    logger.info("=" * 80)
    logger.info("Training Baseline Model")
    logger.info("=" * 80)

    # Load data from database
    try:
        df = load_data_from_database()
    except Exception as e:
        logger.error(f"Failed to load data from database: {e}")
        logger.info("Make sure PostgreSQL is running and database is initialized")
        logger.info("Run: make start && make init-db")
        sys.exit(1)

    # Check data quality
    if len(df) == 0:
        logger.error("No data found in database!")
        logger.info("Initialize database with: make init-db")
        sys.exit(1)

    # Check required columns
    required_cols = ["designation", "description", "prdtypecode"]
    missing = set(required_cols) - set(df.columns)
    if missing:
        logger.error(f"Missing columns: {missing}")
        sys.exit(1)

    # Set MLflow tracking URI
    mlflow_uri = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
    os.environ["MLFLOW_TRACKING_URI"] = mlflow_uri
    logger.info(f"MLflow URI: {mlflow_uri}")

    # Train model
    from src.models.train import train_model

    try:
        run_id = train_model(
            train_df=df,
            test_df=None,  # Will split internally
            max_features=args.max_features,
            C=args.C,
            max_iter=1000,
            auto_register=True,
            auto_promote=args.auto_promote,
        )

        logger.info("=" * 80)
        logger.info("✅ Baseline Model Training Complete!")
        logger.info(f"   MLflow Run ID: {run_id}")
        logger.info(f"   MLflow UI: {mlflow_uri}")
        logger.info("=" * 80)

        # Print next steps
        logger.info("\nNext steps:")
        logger.info("1. View model in MLflow UI: open http://localhost:5000")
        logger.info("2. Start API service: make start-api")
        logger.info("3. Test prediction: curl -X POST http://localhost:8000/predict \\")
        logger.info('     -H "Content-Type: application/json" \\')
        logger.info(
            '     -d \'{"designation": "iPhone 13", "description": "Smartphone Apple"}\''
        )

    except Exception as e:
        logger.error(f"Training failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
