"""
Inference Logger

Logs predictions to CSV for drift monitoring with Evidently.
"""
import csv
import os
from datetime import datetime
from pathlib import Path
from typing import Dict
import pandas as pd
from . import config
import logging

logger = logging.getLogger(__name__)


class InferenceLogger:
    """Logger for inference predictions"""

    def __init__(self, log_path: str = None):
        self.log_path = log_path or config.INFERENCE_LOG_PATH
        self.max_rows = config.INFERENCE_LOG_MAX_ROWS
        self._ensure_log_file()

    def _ensure_log_file(self):
        """Ensure log file exists with headers"""
        Path(self.log_path).parent.mkdir(parents=True, exist_ok=True)

        if not os.path.exists(self.log_path):
            # Create with headers
            with open(self.log_path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(
                    [
                        "timestamp",
                        "prediction_id",
                        "designation",
                        "description",
                        "predicted_class",
                        "confidence",
                        "text_length",
                        "model_version",
                        "model_stage",
                    ]
                )
            logger.info(f"Created inference log at {self.log_path}")

    def log_prediction(
        self,
        prediction_id: str,
        designation: str,
        description: str,
        predicted_class: int,
        confidence: float,
        model_version: str,
        model_stage: str,
    ):
        """Log a single prediction"""
        try:
            text_length = len(designation) + len(description)
            timestamp = datetime.utcnow().isoformat()

            with open(self.log_path, "a", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(
                    [
                        timestamp,
                        prediction_id,
                        designation[:100],  # Truncate for CSV
                        description[:500],  # Truncate for CSV
                        predicted_class,
                        confidence,
                        text_length,
                        model_version,
                        model_stage,
                    ]
                )

            # Rotate if exceeds max rows
            self._rotate_if_needed()

        except Exception as e:
            logger.error(f"Failed to log prediction: {e}")

    def _rotate_if_needed(self):
        """Rotate log file if it exceeds max rows"""
        try:
            df = pd.read_csv(self.log_path)
            if len(df) > self.max_rows:
                # Keep most recent rows
                df = df.tail(self.max_rows)
                df.to_csv(self.log_path, index=False)
                logger.info(f"Rotated inference log, kept {len(df)} rows")
        except Exception as e:
            logger.warning(f"Failed to rotate log: {e}")

    def get_recent_predictions(self, limit: int = 100) -> pd.DataFrame:
        """Get recent predictions as DataFrame"""
        try:
            if not os.path.exists(self.log_path):
                return pd.DataFrame()

            df = pd.read_csv(self.log_path)
            return df.tail(limit)
        except Exception as e:
            logger.error(f"Failed to read predictions: {e}")
            return pd.DataFrame()


# Global inference logger instance
inference_logger = InferenceLogger()
