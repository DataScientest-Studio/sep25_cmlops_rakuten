"""
Prefect Training Pipeline Flow

Orchestrates model training from dataset generation to model registration.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from prefect import flow, task
from prefect.runtime import flow_run
import logging
import mlflow

from src.models.train import train_model
from src.models.model_registry import get_latest_model_version

logger = logging.getLogger(__name__)


@task(name="load-dataset", retries=2, retry_delay_seconds=10)
def load_dataset_task(dataset_run_id: str = None):
    """Load dataset from MLflow or database"""
    logger.info(f"Loading dataset: {dataset_run_id}")

    if dataset_run_id:
        # Load from MLflow
        try:
            from src.models.train import load_dataset_from_mlflow

            train_df, test_df = load_dataset_from_mlflow(dataset_run_id)
            return train_df, test_df, dataset_run_id
        except Exception as e:
            logger.error(f"Failed to load from MLflow: {e}")
            # Fall back to database
            dataset_run_id = None

    # Load from database
    if dataset_run_id is None:
        from scripts.train_baseline_model import load_data_from_database

        df = load_data_from_database()
        return df, None, None

    return None, None, None


@task(name="train-model", retries=1, retry_delay_seconds=30)
def train_model_task(
    train_df,
    test_df,
    dataset_run_id=None,
    week_number=None,
    max_features=5000,
    C=1.0,
):
    """Train model with given dataset"""
    logger.info(f"Training model (week={week_number})")

    run_id = train_model(
        dataset_run_id=dataset_run_id,
        week_number=week_number,
        train_df=train_df,
        test_df=test_df,
        max_features=max_features,
        C=C,
        max_iter=1000,
        auto_register=True,
        auto_promote=False,  # Manual promotion via Streamlit
    )

    return run_id


@task(name="get-model-metrics")
def get_model_metrics_task(run_id: str):
    """Get metrics from trained model run"""
    try:
        client = mlflow.tracking.MlflowClient()
        run = client.get_run(run_id)
        metrics = run.data.metrics

        return {
            "run_id": run_id,
            "test_f1_weighted": metrics.get("test_f1_weighted", 0.0),
            "test_accuracy": metrics.get("test_accuracy", 0.0),
        }
    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        return {"run_id": run_id, "test_f1_weighted": 0.0}


@task(name="promote-if-better")
def promote_if_better_task(current_metrics: dict, threshold: float = 0.75):
    """Promote model to Production if it meets quality threshold"""
    from src.models.model_registry import register_model, promote_model, get_latest_model_version

    f1_score = current_metrics.get("test_f1_weighted", 0.0)

    logger.info(f"Model F1 score: {f1_score:.4f} (threshold: {threshold})")

    if f1_score < threshold:
        logger.warning(
            f"Model F1 ({f1_score:.4f}) below threshold ({threshold}), not promoting"
        )
        return False

    # Get model version from registry
    try:
        # The model should already be registered by train_model
        # Find the version associated with this run_id
        from mlflow.tracking import MlflowClient

        client = MlflowClient()
        run_id = current_metrics["run_id"]

        # Search for model version with this run_id
        versions = client.search_model_versions(f"run_id='{run_id}'")

        if not versions:
            logger.warning(f"No model version found for run_id: {run_id}")
            return False

        version = int(versions[0].version)
        model_name = versions[0].name

        logger.info(f"Promoting {model_name} version {version} to Production")

        promote_model(model_name, version, stage="Production", archive_existing=True)

        logger.info(f"Model promoted successfully!")
        return True

    except Exception as e:
        logger.error(f"Failed to promote model: {e}")
        return False


@flow(name="rakuten-training-pipeline", log_prints=True)
def training_pipeline(
    dataset_run_id: str = None,
    week_number: int = None,
    max_features: int = 5000,
    C: float = 1.0,
    auto_promote_threshold: float = 0.75,
):
    """
    Complete training pipeline flow.

    Args:
        dataset_run_id: MLflow run ID of the dataset (optional)
        week_number: Week number for tracking (optional)
        max_features: Max TF-IDF features
        C: Regularization parameter
        auto_promote_threshold: F1 threshold for auto-promotion

    Returns:
        Dictionary with run information
    """
    logger.info("=" * 80)
    logger.info("🚀 Rakuten Training Pipeline Started")
    logger.info("=" * 80)

    # Load dataset
    train_df, test_df, dataset_id = load_dataset_task(dataset_run_id)

    if train_df is None:
        logger.error("Failed to load dataset")
        raise ValueError("Dataset loading failed")

    # Train model
    run_id = train_model_task(
        train_df, test_df, dataset_id, week_number, max_features, C
    )

    if not run_id:
        logger.error("Training failed")
        raise ValueError("Training failed")

    # Get metrics
    metrics = get_model_metrics_task(run_id)

    # Optional: Auto-promote if meets threshold
    promoted = promote_if_better_task(metrics, threshold=auto_promote_threshold)

    logger.info("=" * 80)
    logger.info("✅ Training Pipeline Complete")
    logger.info(f"   Run ID: {run_id}")
    logger.info(f"   F1 Score: {metrics.get('test_f1_weighted', 0):.4f}")
    logger.info(f"   Promoted: {promoted}")
    logger.info("=" * 80)

    return {
        "run_id": run_id,
        "metrics": metrics,
        "promoted": promoted,
        "dataset_run_id": dataset_id,
        "week_number": week_number,
    }


if __name__ == "__main__":
    # Example: Run training pipeline
    result = training_pipeline(
        dataset_run_id=None,  # Load from database
        week_number=1,
        max_features=5000,
        C=1.0,
        auto_promote_threshold=0.70,
    )
    print(f"\nTraining complete: {result}")
