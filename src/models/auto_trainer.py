"""
Auto Trainer Module

Automates the complete training pipeline:
  1. Generate balanced dataset from current database state
  2. Log dataset to MLflow
  3. Train model (TF-IDF + LogisticRegression)
  4. Register model in MLflow Model Registry
"""
import sys
from pathlib import Path
import logging
import os

sys.path.append(str(Path(__file__).parent.parent.parent))

import mlflow
from mlflow.tracking import MlflowClient

from src.data.dataset_generator import generate_balanced_dataset, save_and_log_dataset
from src.models.train import train_model
from src.config import PIPELINE_CONFIG, MLFLOW_CONFIG

logger = logging.getLogger(__name__)


class AutoTrainer:
    """
    Automated model training pipeline.

    Orchestrates: balanced dataset generation -> model training -> MLflow registration.
    The promotion step is handled separately by PromotionEngine.
    """

    def __init__(
        self,
        model_name: str = "rakuten_classifier",
        max_features: int = 5000,
        C: float = 1.0,
        max_iter: int = 1000,
    ):
        self.model_name = model_name
        self.max_features = max_features
        self.C = C
        self.max_iter = max_iter

        mlflow.set_tracking_uri(MLFLOW_CONFIG["tracking_uri"])
        self.client = MlflowClient()

    def run(self) -> dict:
        """
        Run the complete auto-training pipeline.

        Returns:
            dict with keys: run_id, dataset_run_id, model_version,
                            week_number, f1_score, accuracy, dataset_size
        """
        logger.info("=" * 80)
        logger.info("AUTO-TRAINER: Starting automated training pipeline")
        logger.info("=" * 80)

        # Step 1: Generate balanced dataset
        logger.info("Step 1/3: Generating balanced dataset...")
        df_balanced, week_number, metadata = generate_balanced_dataset(
            strategy=PIPELINE_CONFIG["balancing_strategy"]
        )

        if df_balanced is None:
            raise RuntimeError(
                "Failed to generate balanced dataset - no data available"
            )

        logger.info(
            f"  Dataset generated: {len(df_balanced)} samples, week {week_number}"
        )

        # Step 2: Save and log dataset to MLflow
        logger.info("Step 2/3: Logging dataset to MLflow...")
        dataset_run_id = save_and_log_dataset(df_balanced, week_number, metadata)
        logger.info(f"  Dataset logged: run_id={dataset_run_id}")

        # Step 3: Train model (register but do NOT promote)
        logger.info("Step 3/3: Training model...")
        run_id = train_model(
            train_df=df_balanced,
            week_number=week_number,
            max_features=self.max_features,
            C=self.C,
            max_iter=self.max_iter,
            auto_register=True,
            auto_promote=False,
        )

        # Retrieve metrics and model version from MLflow
        run = self.client.get_run(run_id)
        f1_score = run.data.metrics.get("test_f1_weighted", 0.0)
        accuracy = run.data.metrics.get("test_accuracy", 0.0)

        versions = self.client.search_model_versions(f"run_id='{run_id}'")
        model_version = int(versions[0].version) if versions else None

        # Tag the run as auto-trained
        self.client.set_tag(run_id, "auto_trained", "true")
        self.client.set_tag(run_id, "pipeline", "weekly_auto_train")
        self.client.set_tag(run_id, "week_number", str(week_number))

        result = {
            "run_id": run_id,
            "dataset_run_id": dataset_run_id,
            "model_version": model_version,
            "week_number": week_number,
            "f1_score": f1_score,
            "accuracy": accuracy,
            "dataset_size": len(df_balanced),
        }

        logger.info("=" * 80)
        logger.info("AUTO-TRAINER: Training pipeline complete")
        logger.info(f"   Run ID:        {run_id}")
        logger.info(f"   Model Version: {model_version}")
        logger.info(f"   F1 Score:      {f1_score:.4f}")
        logger.info(f"   Accuracy:      {accuracy:.4f}")
        logger.info("=" * 80)

        return result
