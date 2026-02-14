"""
Model Loader

Loads models from MLflow Model Registry with caching and automatic reloading.
"""
import mlflow
import mlflow.sklearn
from mlflow.tracking import MlflowClient
import time
import logging
from typing import Optional, Tuple, Any
import config
from metrics import update_model_metrics

logger = logging.getLogger(__name__)


class ModelLoader:
    """
    Loads and caches model from MLflow Model Registry.

    Features:
    - Lazy loading (loads on first request)
    - Automatic reloading based on time interval
    - Caches model and vectorizer to avoid repeated loads
    - Tracks model metadata (version, stage)
    """

    def __init__(
        self,
        model_name: str = None,
        model_stage: str = None,
        reload_interval: int = None,
    ):
        self.model_name = model_name or config.MODEL_NAME
        self.model_stage = model_stage or config.MODEL_STAGE
        self.reload_interval = reload_interval or config.MODEL_RELOAD_INTERVAL

        # Set MLflow tracking URI
        mlflow.set_tracking_uri(config.MLFLOW_TRACKING_URI)

        # Cached model components
        self._model = None
        self._vectorizer = None
        self._model_version = None
        self._last_reload = None

        logger.info(
            f"ModelLoader initialized: {self.model_name} (stage={self.model_stage})"
        )

    def get_model(self) -> Tuple[Any, Any, str]:
        """
        Get model and vectorizer.

        Returns:
            Tuple of (model, vectorizer, version_info)
        """
        if self._should_reload():
            self._load_from_registry()

        return self._model, self._vectorizer, self._model_version

    def _should_reload(self) -> bool:
        """Check if model should be reloaded"""
        # First load
        if self._model is None:
            return True

        # Check reload interval
        if self._last_reload is None:
            return True

        elapsed = time.time() - self._last_reload
        return elapsed > self.reload_interval

    def _load_from_registry(self):
        """Load model from MLflow Model Registry"""
        try:
            logger.info(
                f"Loading model from registry: {self.model_name}/{self.model_stage}"
            )

            # Get model URI
            model_uri = f"models:/{self.model_name}/{self.model_stage}"

            # Load model (sklearn pipeline or model)
            loaded_model = mlflow.sklearn.load_model(model_uri)

            # Get model version info
            client = MlflowClient()
            try:
                # Get latest version in stage
                versions = client.get_latest_versions(
                    self.model_name, stages=[self.model_stage]
                )
                if versions:
                    version = versions[0].version
                    run_id = versions[0].run_id
                else:
                    version = "unknown"
                    run_id = None
            except Exception as e:
                logger.warning(f"Could not get version info: {e}")
                version = "unknown"
                run_id = None

            # Check if model is a pipeline or just a model
            if hasattr(loaded_model, "named_steps"):
                # It's a sklearn Pipeline
                # Extract vectorizer and model
                if "vectorizer" in loaded_model.named_steps:
                    self._vectorizer = loaded_model.named_steps["vectorizer"]
                    self._model = loaded_model.named_steps["classifier"]
                else:
                    # Try to find TfidfVectorizer in pipeline
                    for step_name, step in loaded_model.named_steps.items():
                        if "tfidf" in step_name.lower() or "vectorizer" in step_name.lower():
                            self._vectorizer = step
                        elif "classifier" in step_name.lower() or "model" in step_name.lower():
                            self._model = step

                    # If still not found, use whole pipeline
                    if self._model is None:
                        self._model = loaded_model
                        self._vectorizer = None
            else:
                # Not a pipeline, just a model
                # We'll need to load vectorizer separately
                self._model = loaded_model
                self._vectorizer = None

                # Try to load vectorizer from artifacts
                if run_id:
                    try:
                        artifact_uri = f"runs:/{run_id}/vectorizer.pkl"
                        import pickle
                        import mlflow.artifacts
                        
                        # Download artifact
                        local_path = mlflow.artifacts.download_artifacts(artifact_uri)
                        with open(local_path, "rb") as f:
                            self._vectorizer = pickle.load(f)
                        logger.info("Loaded vectorizer from artifacts")
                    except Exception as e:
                        logger.warning(f"Could not load vectorizer: {e}")

            self._model_version = version
            self._last_reload = time.time()

            # Update Prometheus metrics
            update_model_metrics(self.model_name, version, self.model_stage)

            logger.info(
                f"Model loaded successfully: version={version}, stage={self.model_stage}"
            )

        except Exception as e:
            logger.error(f"Failed to load model from registry: {e}")
            # Keep using cached model if available
            if self._model is None:
                raise RuntimeError(f"No model available and loading failed: {e}")

    def is_loaded(self) -> bool:
        """Check if model is loaded"""
        return self._model is not None

    def get_model_info(self) -> dict:
        """Get current model metadata"""
        return {
            "name": self.model_name,
            "version": self._model_version or "not_loaded",
            "stage": self.model_stage,
            "loaded": self.is_loaded(),
            "last_reload": self._last_reload,
        }


# Global model loader instance
model_loader = ModelLoader()
