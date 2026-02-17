"""
Drift Detection Thresholds

Configuration for drift monitoring thresholds (configurable via environment variables).

Severity levels (based on overall drift score / PSI):
  - OK       : score < WARNING  (no action)
  - WARNING  : score >= 0.1     (log only)
  - ALERT    : score >= 0.2     (notify + log)
  - CRITICAL : score >= 0.3     (notify + recommend retrain)
"""
import os

# ---------------------------------------------------------------------------
# Evidently-based thresholds
# ---------------------------------------------------------------------------
DATASET_DRIFT_THRESHOLD = float(os.getenv("DRIFT_THRESHOLD", "0.3"))
FEATURE_DRIFT_THRESHOLD = 0.5
PREDICTION_DRIFT_THRESHOLD = 0.3

# ---------------------------------------------------------------------------
# Statistical test thresholds
# ---------------------------------------------------------------------------
MIN_SAMPLES_FOR_DRIFT = int(os.getenv("MIN_SAMPLES_FOR_DRIFT", "100"))

# Severity thresholds (PSI-based)
DRIFT_WARNING_THRESHOLD = float(os.getenv("DRIFT_WARNING_THRESHOLD", "0.1"))
DRIFT_ALERT_THRESHOLD = float(os.getenv("DRIFT_ALERT_THRESHOLD", "0.2"))
DRIFT_CRITICAL_THRESHOLD = float(os.getenv("DRIFT_CRITICAL_THRESHOLD", "0.3"))
