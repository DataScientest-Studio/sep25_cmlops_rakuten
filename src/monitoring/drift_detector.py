"""
Drift Detection with Evidently

Generates drift reports comparing reference and current data.
"""
import pandas as pd
import numpy as np
from pathlib import Path
import logging
import os
from datetime import datetime
from typing import Dict, Optional

try:
    from evidently import ColumnMapping
    from evidently.report import Report
    from evidently.metric_preset import DataDriftPreset, DataQualityPreset
    from evidently.metrics import *
except ImportError:
    logging.warning("Evidently not installed. Install with: pip install evidently")
    ColumnMapping = None
    Report = None

from . import thresholds

logger = logging.getLogger(__name__)


class DriftDetector:
    """
    Detects data drift using Evidently AI.

    Compares reference data (training) with current data (production inferences).
    """

    def __init__(self, report_path: str = None):
        self.report_path = report_path or os.getenv(
            "EVIDENTLY_REPORT_PATH", "./reports/evidently"
        )
        Path(self.report_path).mkdir(parents=True, exist_ok=True)

    def detect_drift(
        self,
        reference_df: pd.DataFrame,
        current_df: pd.DataFrame,
        text_columns: list = None,
    ) -> Dict:
        """
        Detect drift between reference and current data.

        Args:
            reference_df: Reference dataset (training data)
            current_df: Current dataset (production inferences)
            text_columns: List of text column names (e.g., ['designation', 'description'])

        Returns:
            Dictionary with drift metrics and report path
        """
        if Report is None:
            raise ImportError("Evidently not installed. Install with: pip install evidently")

        logger.info("Detecting data drift...")
        logger.info(f"Reference samples: {len(reference_df)}")
        logger.info(f"Current samples: {len(current_df)}")

        # Check minimum samples
        if len(current_df) < thresholds.MIN_SAMPLES_FOR_DRIFT:
            logger.warning(
                f"Insufficient samples for drift detection: {len(current_df)} < "
                f"{thresholds.MIN_SAMPLES_FOR_DRIFT}"
            )
            return {
                "dataset_drift": None,
                "drift_detected": False,
                "message": "Insufficient samples",
            }

        # Prepare data
        # Ensure same columns
        common_cols = list(set(reference_df.columns) & set(current_df.columns))
        reference_df = reference_df[common_cols].copy()
        current_df = current_df[common_cols].copy()

        # Column mapping
        column_mapping = ColumnMapping()

        # If predicted_class exists, use as target
        if "predicted_class" in common_cols:
            column_mapping.target = "predicted_class"
        elif "prdtypecode" in common_cols:
            column_mapping.target = "prdtypecode"

        # Mark text columns (Evidently handles them differently)
        if text_columns:
            column_mapping.text_features = [
                col for col in text_columns if col in common_cols
            ]

        # Create report
        report = Report(
            metrics=[
                DataDriftPreset(stattest="psi", stattest_threshold=0.1),
                DataQualityPreset(),
            ]
        )

        # Run report
        try:
            report.run(
                reference_data=reference_df,
                current_data=current_df,
                column_mapping=column_mapping,
            )
        except Exception as e:
            logger.error(f"Failed to run Evidently report: {e}")
            return {
                "dataset_drift": None,
                "drift_detected": False,
                "error": str(e),
            }

        # Save HTML report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = Path(self.report_path) / f"evidently_report_{timestamp}.html"
        report.save_html(str(report_file))
        logger.info(f"Drift report saved: {report_file}")

        # Also save latest as standard name (for Streamlit)
        latest_report = Path(self.report_path) / "evidently_report.html"
        report.save_html(str(latest_report))

        # Extract drift metrics
        try:
            # Get report dictionary
            report_dict = report.as_dict()

            # Extract dataset-level drift (simplified)
            # Look for dataset drift metric
            dataset_drift_detected = False
            dataset_drift_score = 0.0

            for metric in report_dict.get("metrics", []):
                if metric.get("metric") == "DatasetDriftMetric":
                    result = metric.get("result", {})
                    dataset_drift_detected = result.get("dataset_drift", False)
                    # Calculate drift score as proportion of drifted features
                    n_features = result.get("number_of_columns", 1)
                    n_drifted = result.get("number_of_drifted_columns", 0)
                    dataset_drift_score = n_drifted / n_features if n_features > 0 else 0.0
                    break

            drift_metrics = {
                "dataset_drift": dataset_drift_score,
                "dataset_drift_detected": dataset_drift_detected,
                "drift_detected": dataset_drift_score > thresholds.DATASET_DRIFT_THRESHOLD,
                "threshold": thresholds.DATASET_DRIFT_THRESHOLD,
                "report_path": str(report_file),
                "reference_samples": len(reference_df),
                "current_samples": len(current_df),
                "timestamp": timestamp,
            }

            logger.info(
                f"Drift detection complete: drift_score={dataset_drift_score:.3f}, "
                f"drift_detected={drift_metrics['drift_detected']}"
            )

            # Save metrics as JSON
            metrics_file = Path(self.report_path) / "drift_metrics.json"
            import json

            with open(metrics_file, "w") as f:
                json.dump(drift_metrics, f, indent=2)

            return drift_metrics

        except Exception as e:
            logger.error(f"Failed to extract drift metrics: {e}")
            return {
                "dataset_drift": None,
                "drift_detected": False,
                "report_path": str(report_file),
                "error": str(e),
            }


def generate_drift_report(
    reference_csv: str = None,
    current_csv: str = None,
    reference_df: pd.DataFrame = None,
    current_df: pd.DataFrame = None,
) -> Dict:
    """
    Convenience function to generate drift report.

    Args:
        reference_csv: Path to reference data CSV
        current_csv: Path to current data CSV
        reference_df: Reference DataFrame (alternative to CSV)
        current_df: Current DataFrame (alternative to CSV)

    Returns:
        Drift metrics dictionary
    """
    # Load data if paths provided
    if reference_df is None:
        if reference_csv is None:
            raise ValueError("Either reference_csv or reference_df must be provided")
        reference_df = pd.read_csv(reference_csv)

    if current_df is None:
        if current_csv is None:
            raise ValueError("Either current_csv or current_df must be provided")
        current_df = pd.read_csv(current_csv)

    # Detect drift
    detector = DriftDetector()
    return detector.detect_drift(
        reference_df,
        current_df,
        text_columns=["designation", "description"],
    )


if __name__ == "__main__":
    # Example usage
    import argparse

    parser = argparse.ArgumentParser(description="Generate drift report")
    parser.add_argument("--reference", required=True, help="Reference data CSV")
    parser.add_argument("--current", required=True, help="Current data CSV")

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    metrics = generate_drift_report(
        reference_csv=args.reference, current_csv=args.current
    )

    print("\nDrift Detection Results:")
    print(f"  Dataset Drift: {metrics.get('dataset_drift', 'N/A')}")
    print(f"  Drift Detected: {metrics.get('drift_detected', False)}")
    print(f"  Threshold: {metrics.get('threshold', 'N/A')}")
    print(f"  Report: {metrics.get('report_path', 'N/A')}")
