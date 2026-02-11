"""
Drift Detection Thresholds

Configuration for drift monitoring thresholds.
"""
import os

# Drift threshold for dataset-level drift (0-1 scale)
# If drift score exceeds this, trigger retraining
DATASET_DRIFT_THRESHOLD = float(os.getenv("DRIFT_THRESHOLD", "0.3"))

# Feature-level drift threshold
FEATURE_DRIFT_THRESHOLD = 0.5

# Minimum samples required for drift detection
MIN_SAMPLES_FOR_DRIFT = 100

# Prediction drift threshold (for distribution shifts)
PREDICTION_DRIFT_THRESHOLD = 0.3
