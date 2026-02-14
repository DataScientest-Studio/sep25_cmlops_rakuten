"""
Pipeline Executor for Streamlit

This module provides functions to execute pipeline tasks from the Streamlit UI.
All functions run the actual Python scripts/modules and return results.
"""
import subprocess
import sys
from pathlib import Path
import logging
import os

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get project root
PROJECT_ROOT = Path(__file__).parent.parent.parent


def run_data_loader(target_percentage: float = None) -> dict:
    """
    Run the incremental data loader
    
    Args:
        target_percentage: Target percentage to load (optional)
        
    Returns:
        dict: Result with success status and message
    """
    try:
        logger.info(f"Running data loader (target: {target_percentage}%)")
        
        # Import and run the loader directly
        sys.path.insert(0, str(PROJECT_ROOT))
        from src.data.loader import load_incremental_data, get_current_state
        
        # Get current state
        state = get_current_state()
        current_pct = state['current_percentage']
        
        # Load data
        success = load_incremental_data(target_percentage)
        
        if success:
            new_state = get_current_state()
            return {
                'success': True,
                'message': f'Successfully loaded data from {current_pct}% to {new_state["current_percentage"]}%',
                'current_percentage': new_state['current_percentage'],
                'total_rows': new_state['total_rows']
            }
        else:
            return {
                'success': False,
                'message': 'Data loading failed',
                'current_percentage': current_pct
            }
            
    except Exception as e:
        logger.error(f"Error loading data: {e}")
        return {
            'success': False,
            'message': f'Error: {str(e)}'
        }


def run_dataset_generator() -> dict:
    """
    Generate balanced dataset and log to MLflow
    
    Returns:
        dict: Result with success status and message
    """
    try:
        logger.info("Generating balanced dataset")
        
        # Import and run dataset generator
        sys.path.insert(0, str(PROJECT_ROOT))
        from src.data.dataset_generator import generate_balanced_dataset, save_and_log_dataset
        from src.config import PIPELINE_CONFIG
        
        # Generate dataset
        df_balanced, week_number, metadata = generate_balanced_dataset(
            strategy=PIPELINE_CONFIG['balancing_strategy']
        )
        
        if df_balanced is None:
            return {
                'success': False,
                'message': 'Failed to generate balanced dataset'
            }
        
        # Save and log to MLflow
        run_id = save_and_log_dataset(df_balanced, week_number, metadata)
        
        return {
            'success': True,
            'message': f'Dataset generated for week {week_number} (size: {len(df_balanced)})',
            'week_number': week_number,
            'dataset_size': len(df_balanced),
            'run_id': run_id
        }
        
    except Exception as e:
        logger.error(f"Error generating dataset: {e}")
        return {
            'success': False,
            'message': f'Error: {str(e)}'
        }


def run_model_training(max_features: int = 5000, C: float = 1.0, auto_promote: bool = False) -> dict:
    """
    Train model from database data
    
    Args:
        max_features: Max TF-IDF features
        C: Regularization parameter
        auto_promote: Auto-promote if F1 > 0.70
        
    Returns:
        dict: Result with success status and message
    """
    try:
        logger.info("Training model from database")
        
        # Import required modules
        sys.path.insert(0, str(PROJECT_ROOT))
        from src.models.train import train_model
        import psycopg2
        import pandas as pd
        
        # Load data from database
        postgres_host = os.getenv("POSTGRES_HOST", "localhost")
        postgres_port = os.getenv("POSTGRES_PORT", "5432")
        postgres_db = os.getenv("POSTGRES_DB", "rakuten_db")
        postgres_user = os.getenv("POSTGRES_USER", "rakuten_user")
        postgres_password = os.getenv("POSTGRES_PASSWORD", "rakuten_pass")
        
        query = """
        SELECT 
            p.productid,
            p.designation,
            p.description,
            l.prdtypecode
        FROM products p
        JOIN labels l ON p.productid = l.productid
        ORDER BY p.productid
        """
        
        conn = psycopg2.connect(
            host=postgres_host,
            port=postgres_port,
            database=postgres_db,
            user=postgres_user,
            password=postgres_password
        )
        
        try:
            df = pd.read_sql_query(query, conn)
        finally:
            conn.close()
        
        if len(df) == 0:
            return {
                'success': False,
                'message': 'No data in database. Please load data first.'
            }
        
        # Set MLflow tracking URI
        mlflow_uri = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
        os.environ["MLFLOW_TRACKING_URI"] = mlflow_uri
        
        # Train model
        run_id = train_model(
            train_df=df,
            test_df=None,
            max_features=max_features,
            C=C,
            max_iter=1000,
            auto_register=True,
            auto_promote=auto_promote
        )
        
        return {
            'success': True,
            'message': f'Model trained successfully!',
            'run_id': run_id,
            'samples': len(df),
            'classes': df['prdtypecode'].nunique()
        }
        
    except Exception as e:
        logger.error(f"Error training model: {e}")
        return {
            'success': False,
            'message': f'Error: {str(e)}'
        }


def get_data_status() -> dict:
    """
    Get current data loading status
    
    Returns:
        dict: Current data status
    """
    try:
        sys.path.insert(0, str(PROJECT_ROOT))
        from src.data.loader import get_current_state
        
        state = get_current_state()
        
        return {
            'success': True,
            'current_percentage': state['current_percentage'],
            'total_rows': state['total_rows'],
            'last_load_date': state['last_load_date']
        }
        
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return {
            'success': False,
            'message': f'Error: {str(e)}'
        }


def promote_model(model_name: str, version: int, stage: str, archive_existing: bool = True) -> dict:
    """
    Promote model to a stage
    
    Args:
        model_name: Name of the model
        version: Version number
        stage: Target stage (Staging, Production, Archived)
        archive_existing: Archive existing models in target stage
        
    Returns:
        dict: Result with success status and message
    """
    try:
        logger.info(f"Promoting {model_name} v{version} to {stage}")
        
        # Import MLflow
        import mlflow
        from mlflow.tracking import MlflowClient
        
        mlflow_uri = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
        mlflow.set_tracking_uri(mlflow_uri)
        client = MlflowClient(tracking_uri=mlflow_uri)
        
        # Transition model version
        client.transition_model_version_stage(
            name=model_name,
            version=version,
            stage=stage,
            archive_existing_versions=archive_existing
        )
        
        return {
            'success': True,
            'message': f'Successfully promoted {model_name} v{version} to {stage}'
        }
        
    except Exception as e:
        logger.error(f"Error promoting model: {e}")
        return {
            'success': False,
            'message': f'Error: {str(e)}'
        }
