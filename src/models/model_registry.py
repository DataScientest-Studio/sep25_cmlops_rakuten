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
