"""
Promotion Engine Module

Handles conditional model promotion to production based on performance criteria:
  - F1 score must exceed a configurable minimum threshold (default: 0.75)
  - F1 score must be better than the current production model
"""
import os
import logging
import json
from datetime import datetime
from pathlib import Path

import mlflow
from mlflow.tracking import MlflowClient

from src.models.model_registry import auto_promote_if_better
from src.config import MLFLOW_CONFIG

logger = logging.getLogger(__name__)


class PromotionEngine:
    """
    Evaluates trained models and promotes to production if performance criteria are met.

    Configuration (via environment variables):
        MIN_F1_THRESHOLD: Minimum F1 score required (default: 0.75)
        AUTO_PROMOTION_ENABLED: Enable/disable auto-promotion (default: true)
        PROMOTION_LOG_PATH: Path to decision log file (default: ./logs/promotion_decisions.jsonl)
    """

    def __init__(
        self,
        model_name: str = "rakuten_classifier",
        min_f1_threshold: float = None,
        enabled: bool = None,
    ):
        self.model_name = model_name
        self.min_f1_threshold = min_f1_threshold or float(
            os.getenv("MIN_F1_THRESHOLD", "0.75")
        )
        self.enabled = enabled if enabled is not None else (
            os.getenv("AUTO_PROMOTION_ENABLED", "true").lower() == "true"
        )

        mlflow.set_tracking_uri(MLFLOW_CONFIG["tracking_uri"])
        self.client = MlflowClient()

        self.decision_log_path = Path(
            os.getenv("PROMOTION_LOG_PATH", "./logs/promotion_decisions.jsonl")
        )
        self.decision_log_path.parent.mkdir(parents=True, exist_ok=True)

    def evaluate_and_promote(
        self,
        model_version: int,
        f1_score: float,
        run_id: str = None,
    ) -> dict:
        """
        Evaluate a model for promotion to production.

        Args:
            model_version: The new model version number
            f1_score: F1 weighted score of the new model
            run_id: MLflow run ID (for tagging the decision)

        Returns:
            dict: Promotion decision with keys: promoted, reason, new_version, new_f1, ...
        """
        logger.info("=" * 80)
        logger.info("PROMOTION ENGINE: Evaluating model for production")
        logger.info(f"   Model:         {self.model_name} v{model_version}")
        logger.info(f"   F1 Score:      {f1_score:.4f}")
        logger.info(f"   Min Threshold: {self.min_f1_threshold}")
        logger.info(f"   Auto-promotion enabled: {self.enabled}")
        logger.info("=" * 80)

        if not self.enabled:
            result = {
                "promoted": False,
                "reason": "Auto-promotion is disabled",
                "new_version": model_version,
                "new_f1": f1_score,
                "timestamp": datetime.now().isoformat(),
            }
            logger.info("Auto-promotion is disabled. Skipping.")
            self._log_decision(result)
            return result

        if model_version is None:
            result = {
                "promoted": False,
                "reason": "No model version provided",
                "new_f1": f1_score,
                "timestamp": datetime.now().isoformat(),
            }
            logger.error("No model version provided")
            self._log_decision(result)
            return result

        # Delegate to existing promotion logic
        result = auto_promote_if_better(
            model_name=self.model_name,
            new_version=model_version,
            new_f1_score=f1_score,
            min_f1_threshold=self.min_f1_threshold,
        )

        result["timestamp"] = datetime.now().isoformat()
        result["min_f1_threshold"] = self.min_f1_threshold

        # Tag the MLflow run with the promotion decision
        if run_id:
            decision_tag = "promoted" if result["promoted"] else "archived"
            self.client.set_tag(run_id, "promotion_decision", decision_tag)
            self.client.set_tag(run_id, "promotion_reason", result.get("reason", ""))

        self._log_decision(result)

        if result["promoted"]:
            logger.info(f"Model v{model_version} PROMOTED to Production!")
        else:
            logger.info(
                f"Model v{model_version} ARCHIVED: {result.get('reason')}"
            )

        return result

    def _log_decision(self, decision: dict):
        """Append promotion decision to JSONL log file."""
        try:
            with open(self.decision_log_path, "a") as f:
                f.write(json.dumps(decision, default=str) + "\n")
            logger.info(f"Decision logged to: {self.decision_log_path}")
        except Exception as e:
            logger.warning(f"Failed to log decision to file: {e}")
