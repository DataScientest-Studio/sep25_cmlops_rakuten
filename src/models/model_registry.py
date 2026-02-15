"""
MLflow Model Registry Helpers

Functions for registering, promoting, and managing models in MLflow Model Registry.
"""
import mlflow
from mlflow.tracking import MlflowClient
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def register_model(
    run_id: str,
    model_name: str = "rakuten_classifier",
    artifact_path: str = "model",
) -> int:
    """
    Register model from run to MLflow Model Registry.

    Args:
        run_id: MLflow run ID
        model_name: Name for registered model
        artifact_path: Path to model artifact within run

    Returns:
        Model version number
    """
    try:
        model_uri = f"runs:/{run_id}/{artifact_path}"

        logger.info(f"Registering model: {model_uri} as {model_name}")

        model_version = mlflow.register_model(model_uri, model_name)

        logger.info(
            f"Model registered successfully: {model_name} version {model_version.version}"
        )

        return int(model_version.version)

    except Exception as e:
        logger.error(f"Failed to register model: {e}")
        raise


def promote_model(
    model_name: str,
    version: int,
    stage: str = "Production",
    archive_existing: bool = True,
):
    """
    Promote model version to a stage.

    Args:
        model_name: Name of registered model
        version: Model version number
        stage: Target stage ("Staging", "Production", "Archived")
        archive_existing: Whether to archive existing models in the target stage
    """
    try:
        client = MlflowClient()

        logger.info(
            f"Promoting model {model_name} version {version} to {stage} "
            f"(archive_existing={archive_existing})"
        )

        client.transition_model_version_stage(
            name=model_name,
            version=version,
            stage=stage,
            archive_existing_versions=archive_existing,
        )

        logger.info(f"Model promoted successfully to {stage}")

    except Exception as e:
        logger.error(f"Failed to promote model: {e}")
        raise


def auto_promote_if_better(
    model_name: str,
    new_version: int,
    new_f1_score: float,
    min_f1_threshold: float = 0.70,
) -> dict:
    """
    Automatically promote new model to Production if it's better than the current one.
    
    Logic:
    1. If no Production model exists and new model meets threshold → Promote to Production
    2. If Production model exists:
       - If new model is better → Promote to Production (archives old)
       - If new model is worse → Archive new model
    
    Args:
        model_name: Name of registered model
        new_version: New model version number
        new_f1_score: F1 score of new model
        min_f1_threshold: Minimum F1 score to be considered for Production
        
    Returns:
        dict with promotion decision and details
    """
    try:
        client = MlflowClient()
        
        # Get current Production model if it exists
        production_versions = client.get_latest_versions(model_name, stages=["Production"])
        
        if not production_versions:
            # No production model exists
            if new_f1_score >= min_f1_threshold:
                logger.info(
                    f"No Production model exists. New model F1={new_f1_score:.4f} "
                    f"meets threshold ({min_f1_threshold}). Promoting to Production."
                )
                promote_model(model_name, new_version, stage="Production", archive_existing=False)
                return {
                    "promoted": True,
                    "reason": "First production model (meets threshold)",
                    "new_version": new_version,
                    "new_f1": new_f1_score,
                    "previous_version": None,
                    "previous_f1": None,
                }
            else:
                logger.warning(
                    f"No Production model exists and new model F1={new_f1_score:.4f} "
                    f"below threshold ({min_f1_threshold}). Archiving."
                )
                promote_model(model_name, new_version, stage="Archived", archive_existing=False)
                return {
                    "promoted": False,
                    "reason": f"Below minimum threshold ({min_f1_threshold})",
                    "new_version": new_version,
                    "new_f1": new_f1_score,
                    "previous_version": None,
                    "previous_f1": None,
                }
        
        # Production model exists - compare performance
        current_prod = production_versions[0]
        current_version = int(current_prod.version)
        
        # Get F1 score from current production model's run
        current_run = client.get_run(current_prod.run_id)
        current_f1 = current_run.data.metrics.get("test_f1_weighted", 0.0)
        
        logger.info(f"Current Production: version {current_version}, F1={current_f1:.4f}")
        logger.info(f"New model: version {new_version}, F1={new_f1_score:.4f}")
        
        if new_f1_score > current_f1:
            # New model is better - promote it (automatically archives old one)
            improvement = ((new_f1_score - current_f1) / current_f1) * 100
            logger.info(
                f"✅ New model is better! Improvement: +{improvement:.2f}%. "
                f"Promoting to Production (archiving version {current_version})."
            )
            promote_model(model_name, new_version, stage="Production", archive_existing=True)
            return {
                "promoted": True,
                "reason": f"Better performance (+{improvement:.2f}%)",
                "new_version": new_version,
                "new_f1": new_f1_score,
                "previous_version": current_version,
                "previous_f1": current_f1,
                "improvement_pct": improvement,
            }
        else:
            # New model is not better - archive it
            degradation = ((current_f1 - new_f1_score) / current_f1) * 100
            logger.info(
                f"❌ New model is worse (F1={new_f1_score:.4f} vs {current_f1:.4f}, "
                f"-{degradation:.2f}%). Archiving new model."
            )
            promote_model(model_name, new_version, stage="Archived", archive_existing=False)
            return {
                "promoted": False,
                "reason": f"Worse than current production (-{degradation:.2f}%)",
                "new_version": new_version,
                "new_f1": new_f1_score,
                "previous_version": current_version,
                "previous_f1": current_f1,
                "degradation_pct": degradation,
            }
            
    except Exception as e:
        logger.error(f"Failed to auto-promote model: {e}")
        raise


def get_latest_model_version(model_name: str, stage: Optional[str] = None) -> Optional[dict]:
    """
    Get latest model version from registry.

    Args:
        model_name: Name of registered model
        stage: Optional stage filter ("Production", "Staging", etc.)

    Returns:
        Dictionary with version info or None if not found
    """
    try:
        client = MlflowClient()

        if stage:
            versions = client.get_latest_versions(model_name, stages=[stage])
        else:
            # Get all versions and find latest
            all_versions = client.search_model_versions(f"name='{model_name}'")
            if not all_versions:
                return None
            versions = [max(all_versions, key=lambda v: int(v.version))]

        if not versions:
            logger.warning(f"No model found: {model_name} (stage={stage})")
            return None

        version = versions[0]

        info = {
            "name": version.name,
            "version": int(version.version),
            "stage": version.current_stage,
            "run_id": version.run_id,
            "creation_timestamp": version.creation_timestamp,
        }

        logger.info(
            f"Latest model: {model_name} version {info['version']} (stage={info['stage']})"
        )

        return info

    except Exception as e:
        logger.error(f"Failed to get latest model version: {e}")
        return None


def list_model_versions(model_name: str, stage: Optional[str] = None) -> list:
    """
    List all versions of a model.

    Args:
        model_name: Name of registered model
        stage: Optional stage filter

    Returns:
        List of version info dictionaries
    """
    try:
        client = MlflowClient()

        if stage:
            versions = client.get_latest_versions(model_name, stages=[stage])
        else:
            versions = client.search_model_versions(f"name='{model_name}'")

        version_list = [
            {
                "name": v.name,
                "version": int(v.version),
                "stage": v.current_stage,
                "run_id": v.run_id,
                "creation_timestamp": v.creation_timestamp,
            }
            for v in versions
        ]

        logger.info(f"Found {len(version_list)} versions of {model_name}")

        return version_list

    except Exception as e:
        logger.error(f"Failed to list model versions: {e}")
        return []


def delete_model_version(model_name: str, version: int):
    """
    Delete a specific model version.

    Args:
        model_name: Name of registered model
        version: Model version number to delete
    """
    try:
        client = MlflowClient()

        logger.info(f"Deleting model {model_name} version {version}")

        client.delete_model_version(name=model_name, version=str(version))

        logger.info(f"Model version deleted successfully")

    except Exception as e:
        logger.error(f"Failed to delete model version: {e}")
        raise
