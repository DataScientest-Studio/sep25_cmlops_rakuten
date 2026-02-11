"""
Prefect Monitoring and Retraining Flow

Checks for data drift and triggers retraining if threshold exceeded.
Scheduled to run daily.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from prefect import flow, task
import logging
import pandas as pd
import os
from datetime import datetime

from src.monitoring.drift_detector import generate_drift_report
from src.monitoring import thresholds

logger = logging.getLogger(__name__)


@task(name="load-inference-log", retries=2)
def load_inference_log_task(log_path: str = None):
    """Load recent inferences from log file"""
    if log_path is None:
        log_path = os.getenv(
            "INFERENCE_LOG_PATH", "./data/monitoring/inference_log.csv"
        )

    logger.info(f"Loading inference log: {log_path}")

    if not os.path.exists(log_path):
        logger.warning(f"Inference log not found: {log_path}")
        return None

    try:
        df = pd.read_csv(log_path)
        logger.info(f"Loaded {len(df)} inference records")

        # Check minimum samples
        if len(df) < thresholds.MIN_SAMPLES_FOR_DRIFT:
            logger.warning(
                f"Insufficient samples for drift detection: {len(df)} < "
                f"{thresholds.MIN_SAMPLES_FOR_DRIFT}"
            )
            return None

        return df

    except Exception as e:
        logger.error(f"Failed to load inference log: {e}")
        return None


@task(name="load-reference-data", retries=2)
def load_reference_data_task():
    """Load reference (training) data from database"""
    logger.info("Loading reference data from database")

    try:
        from scripts.train_baseline_model import load_data_from_database

        df = load_data_from_database()
        logger.info(f"Loaded {len(df)} reference samples")
        return df

    except Exception as e:
        logger.error(f"Failed to load reference data: {e}")
        return None


@task(name="detect-drift", retries=1)
def detect_drift_task(reference_df: pd.DataFrame, current_df: pd.DataFrame):
    """Run drift detection"""
    logger.info("Running drift detection...")

    try:
        # Prepare current data (inference log) to match reference format
        # Map inference log columns to reference columns
        current_prepared = current_df.copy()

        # Rename predicted_class to prdtypecode for comparison
        if "predicted_class" in current_prepared.columns:
            current_prepared["prdtypecode"] = current_prepared["predicted_class"]

        # Select matching columns
        common_cols = ["designation", "description", "prdtypecode"]
        available_cols = [c for c in common_cols if c in current_prepared.columns]

        if not available_cols:
            logger.error("No common columns found for drift detection")
            return None

        current_prepared = current_prepared[available_cols]

        # Also select same columns from reference
        reference_prepared = reference_df[available_cols].copy()

        # Run drift detection
        drift_metrics = generate_drift_report(
            reference_df=reference_prepared, current_df=current_prepared
        )

        return drift_metrics

    except Exception as e:
        logger.error(f"Drift detection failed: {e}", exc_info=True)
        return None


@task(name="trigger-retraining")
def trigger_retraining_task():
    """Trigger model retraining"""
    logger.info("Triggering model retraining...")

    try:
        from flows.pipeline_flow import training_pipeline

        # Run training pipeline as a subflow
        result = training_pipeline(
            dataset_run_id=None,  # Load from database
            week_number=None,
            max_features=5000,
            C=1.0,
            auto_promote_threshold=0.70,
        )

        logger.info(f"Retraining complete: {result}")
        return result

    except Exception as e:
        logger.error(f"Retraining failed: {e}")
        return None


@task(name="send-notification")
def send_notification_task(drift_detected: bool, drift_score: float, retrained: bool):
    """Send notification about drift status"""
    logger.info("=" * 80)
    logger.info("📊 MONITORING SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Drift Detected: {drift_detected}")
    logger.info(f"Drift Score: {drift_score:.3f}")
    logger.info(f"Threshold: {thresholds.DATASET_DRIFT_THRESHOLD}")
    logger.info(f"Retrained: {retrained}")
    logger.info("=" * 80)

    # TODO: Send actual notification (Slack, email, etc.)
    # For now, just log

    notification = {
        "timestamp": datetime.now().isoformat(),
        "drift_detected": drift_detected,
        "drift_score": drift_score,
        "threshold": thresholds.DATASET_DRIFT_THRESHOLD,
        "retrained": retrained,
    }

    return notification


@flow(name="rakuten-monitor-retrain", log_prints=True)
def monitor_and_retrain(
    inference_log_path: str = None,
    force_retrain: bool = False,
):
    """
    Daily monitoring flow with conditional retraining.

    Args:
        inference_log_path: Path to inference log CSV
        force_retrain: Force retraining regardless of drift

    Returns:
        Dictionary with monitoring results
    """
    logger.info("=" * 80)
    logger.info("📊 Rakuten Monitoring & Retraining Flow")
    logger.info("=" * 80)

    # Load inference log
    current_df = load_inference_log_task(inference_log_path)

    if current_df is None or len(current_df) < thresholds.MIN_SAMPLES_FOR_DRIFT:
        logger.warning("Insufficient data for monitoring, skipping")
        return {
            "status": "skipped",
            "reason": "insufficient_data",
            "drift_detected": False,
            "retrained": False,
        }

    # Load reference data
    reference_df = load_reference_data_task()

    if reference_df is None:
        logger.error("Failed to load reference data, aborting")
        return {
            "status": "error",
            "reason": "reference_data_unavailable",
            "drift_detected": False,
            "retrained": False,
        }

    # Detect drift
    drift_metrics = detect_drift_task(reference_df, current_df)

    if drift_metrics is None:
        logger.error("Drift detection failed")
        return {
            "status": "error",
            "reason": "drift_detection_failed",
            "drift_detected": False,
            "retrained": False,
        }

    drift_detected = drift_metrics.get("drift_detected", False)
    drift_score = drift_metrics.get("dataset_drift", 0.0)

    logger.info(f"Drift Score: {drift_score:.3f}")
    logger.info(f"Threshold: {thresholds.DATASET_DRIFT_THRESHOLD}")
    logger.info(f"Drift Detected: {drift_detected}")

    # Check if retraining is needed
    should_retrain = drift_detected or force_retrain

    retrain_result = None
    if should_retrain:
        logger.warning("⚠️  Drift threshold exceeded, triggering retraining...")
        retrain_result = trigger_retraining_task()
        retrained = retrain_result is not None
    else:
        logger.info("✅ No significant drift detected, no retraining needed")
        retrained = False

    # Send notification
    notification = send_notification_task(drift_detected, drift_score, retrained)

    logger.info("=" * 80)
    logger.info("✅ Monitoring Flow Complete")
    logger.info("=" * 80)

    return {
        "status": "success",
        "drift_detected": drift_detected,
        "drift_score": drift_score,
        "threshold": thresholds.DATASET_DRIFT_THRESHOLD,
        "retrained": retrained,
        "drift_metrics": drift_metrics,
        "retrain_result": retrain_result,
        "notification": notification,
    }


if __name__ == "__main__":
    # Example: Run monitoring flow
    result = monitor_and_retrain(
        inference_log_path="./data/monitoring/inference_log.csv",
        force_retrain=False,
    )
    print(f"\nMonitoring complete: {result}")
