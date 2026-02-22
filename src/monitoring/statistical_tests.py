"""
Statistical Tests for Drift Detection

Implements lightweight statistical tests for detecting data and prediction drift
without requiring Evidently (can run alongside or as fallback).

Tests:
  - PSI (Population Stability Index): measures distribution shift
  - KS Test (Kolmogorov-Smirnov): compares two continuous distributions
  - Chi-Square Test: compares two categorical distributions
  - Jensen-Shannon Divergence: symmetric measure of distribution difference
"""
import numpy as np
import pandas as pd
from scipy import stats
from typing import Dict, Tuple
import logging

logger = logging.getLogger(__name__)


def population_stability_index(
    reference: np.ndarray,
    current: np.ndarray,
    bins: int = 10,
) -> float:
    """
    Calculate Population Stability Index (PSI) between two distributions.

    PSI interpretation:
      - PSI < 0.1  : no significant shift
      - 0.1 <= PSI < 0.2 : moderate shift (warning)
      - PSI >= 0.2 : significant shift (alert)

    Uses an adaptive floor ``0.5 / N`` for empty bins so that the score
    stays bounded even when many bins are empty (sparse data / few samples).

    Args:
        reference: Reference distribution values
        current: Current distribution values
        bins: Number of bins for histogram

    Returns:
        PSI score (float >= 0)
    """
    breakpoints = np.linspace(
        min(np.min(reference), np.min(current)),
        max(np.max(reference), np.max(current)),
        bins + 1,
    )

    ref_counts, _ = np.histogram(reference, bins=breakpoints)
    cur_counts, _ = np.histogram(current, bins=breakpoints)

    ref_floor = 0.5 / len(reference)
    cur_floor = 0.5 / len(current)

    ref_pct = np.maximum(ref_counts / len(reference), ref_floor)
    cur_pct = np.maximum(cur_counts / len(current), cur_floor)

    psi = np.sum((cur_pct - ref_pct) * np.log(cur_pct / ref_pct))
    return float(max(psi, 0.0))


def ks_test(reference: np.ndarray, current: np.ndarray) -> Dict:
    """
    Kolmogorov-Smirnov test for continuous distributions.

    Args:
        reference: Reference distribution values
        current: Current distribution values

    Returns:
        dict with statistic, p_value, drift_detected
    """
    statistic, p_value = stats.ks_2samp(reference, current)
    return {
        "statistic": float(statistic),
        "p_value": float(p_value),
        "drift_detected": bool(p_value < 0.05),
    }


def chi_square_test(
    reference: np.ndarray, current: np.ndarray
) -> Dict:
    """
    Chi-square test for categorical distributions.

    Args:
        reference: Reference category values
        current: Current category values

    Returns:
        dict with statistic, p_value, drift_detected
    """
    # Get all unique categories
    all_categories = np.union1d(np.unique(reference), np.unique(current))

    ref_counts = pd.Series(reference).value_counts()
    cur_counts = pd.Series(current).value_counts()

    # Align both to all categories (fill missing with 0)
    ref_aligned = np.array([ref_counts.get(c, 0) for c in all_categories], dtype=float)
    cur_aligned = np.array([cur_counts.get(c, 0) for c in all_categories], dtype=float)

    # Only compare categories present in reference (ignore brand-new categories)
    ref_categories = set(np.unique(reference))
    mask = np.array([c in ref_categories for c in all_categories])

    ref_filtered = ref_aligned[mask]
    cur_filtered = cur_aligned[mask]

    total_ref = ref_filtered.sum()
    total_cur = cur_filtered.sum()

    if total_ref == 0 or total_cur == 0:
        return {"statistic": 0.0, "p_value": 1.0, "drift_detected": False}

    # Scale expected proportionally so sums match
    expected = ref_filtered / total_ref * total_cur
    nonzero = expected > 0
    if nonzero.sum() < 2:
        return {"statistic": 0.0, "p_value": 1.0, "drift_detected": False}

    statistic, p_value = stats.chisquare(
        cur_filtered[nonzero], f_exp=expected[nonzero]
    )
    return {
        "statistic": float(statistic),
        "p_value": float(p_value),
        "drift_detected": bool(p_value < 0.05),
    }


def jensen_shannon_divergence(
    reference: np.ndarray,
    current: np.ndarray,
    bins: int = 10,
    eps: float = 1e-6,
) -> float:
    """
    Jensen-Shannon Divergence (symmetric KL divergence).

    JSD interpretation:
      - JSD close to 0 : distributions are similar
      - JSD close to 1 : distributions are very different

    Args:
        reference: Reference distribution values
        current: Current distribution values
        bins: Number of bins
        eps: Small value to avoid log(0)

    Returns:
        JSD score (0-1)
    """
    breakpoints = np.linspace(
        min(np.min(reference), np.min(current)),
        max(np.max(reference), np.max(current)),
        bins + 1,
    )

    ref_counts, _ = np.histogram(reference, bins=breakpoints)
    cur_counts, _ = np.histogram(current, bins=breakpoints)

    ref_pct = ref_counts / ref_counts.sum() + eps
    cur_pct = cur_counts / cur_counts.sum() + eps

    # Normalize
    ref_pct = ref_pct / ref_pct.sum()
    cur_pct = cur_pct / cur_pct.sum()

    m = 0.5 * (ref_pct + cur_pct)

    jsd = 0.5 * np.sum(ref_pct * np.log(ref_pct / m)) + 0.5 * np.sum(
        cur_pct * np.log(cur_pct / m)
    )
    return float(np.clip(jsd, 0, 1))


def categorical_psi(
    reference: np.ndarray,
    current: np.ndarray,
) -> float:
    """
    Bias-corrected PSI for categorical data.

    Compares per-category proportions directly instead of binning numeric
    codes.  Subtracts the expected PSI under the null hypothesis (no
    drift) to eliminate the upward bias caused by small samples:

        E[PSI_null] ≈ (K - 1) × (1/n_ref + 1/n_cur)

    where K is the number of categories.  Without this correction the raw
    PSI for ~25 classes with ~100 samples per window is already ≈ 0.4–0.5
    even when the distributions are identical.

    Uses an adaptive floor ``0.5 / N`` for zero-count categories so that
    the log-ratio stays bounded.

    Args:
        reference: Reference category values (e.g. predicted class codes)
        current: Current category values

    Returns:
        Bias-corrected PSI score (float >= 0)
    """
    n_ref = len(reference)
    n_cur = len(current)
    all_categories = np.union1d(np.unique(reference), np.unique(current))
    k = len(all_categories)

    ref_counts = pd.Series(reference).value_counts()
    cur_counts = pd.Series(current).value_counts()

    ref_floor = 0.5 / n_ref
    cur_floor = 0.5 / n_cur

    ref_pct = np.array(
        [max(ref_counts.get(c, 0) / n_ref, ref_floor) for c in all_categories]
    )
    cur_pct = np.array(
        [max(cur_counts.get(c, 0) / n_cur, cur_floor) for c in all_categories]
    )

    raw_psi = float(np.sum((cur_pct - ref_pct) * np.log(cur_pct / ref_pct)))
    bias = (k - 1) * (1.0 / n_ref + 1.0 / n_cur)
    return max(raw_psi - bias, 0.0)


def compute_drift_scores(
    reference_df: pd.DataFrame,
    current_df: pd.DataFrame,
) -> Dict:
    """
    Compute comprehensive drift scores across multiple dimensions.

    Analyses:
      - Data drift: text_length distribution (PSI + KS)
      - Prediction drift: predicted_class distribution (Chi-square + PSI)
      - Confidence drift: confidence distribution (KS + PSI)

    Args:
        reference_df: Reference data (training or earlier inference window)
        current_df: Current data (recent inferences)

    Returns:
        dict with per-dimension scores and overall drift assessment
    """
    results = {
        "data_drift": {},
        "prediction_drift": {},
        "confidence_drift": {},
        "overall_drift_score": 0.0,
        "drift_detected": False,
    }

    # -- Data drift: text_length --
    if "text_length" in reference_df.columns and "text_length" in current_df.columns:
        ref_len = reference_df["text_length"].dropna().values.astype(float)
        cur_len = current_df["text_length"].dropna().values.astype(float)

        if len(ref_len) > 0 and len(cur_len) > 0:
            results["data_drift"] = {
                "psi": population_stability_index(ref_len, cur_len),
                "ks": ks_test(ref_len, cur_len),
                "jsd": jensen_shannon_divergence(ref_len, cur_len),
            }

    # -- Prediction drift: predicted_class distribution --
    if (
        "predicted_class" in reference_df.columns
        and "predicted_class" in current_df.columns
    ):
        ref_pred = reference_df["predicted_class"].dropna().values
        cur_pred = current_df["predicted_class"].dropna().values

        if len(ref_pred) > 0 and len(cur_pred) > 0:
            results["prediction_drift"] = {
                "chi_square": chi_square_test(ref_pred, cur_pred),
                "psi": categorical_psi(ref_pred, cur_pred),
            }

    # -- Confidence drift --
    if "confidence" in reference_df.columns and "confidence" in current_df.columns:
        ref_conf = reference_df["confidence"].dropna().values.astype(float)
        cur_conf = current_df["confidence"].dropna().values.astype(float)

        if len(ref_conf) > 0 and len(cur_conf) > 0:
            results["confidence_drift"] = {
                "psi": population_stability_index(ref_conf, cur_conf),
                "ks": ks_test(ref_conf, cur_conf),
                "mean_ref": float(np.mean(ref_conf)),
                "mean_cur": float(np.mean(cur_conf)),
                "mean_delta": float(np.mean(cur_conf) - np.mean(ref_conf)),
            }

    # -- Overall drift score (weighted average of PSI scores) --
    psi_scores = []

    data_psi = results.get("data_drift", {}).get("psi", 0.0)
    pred_psi = results.get("prediction_drift", {}).get("psi", 0.0)
    conf_psi = results.get("confidence_drift", {}).get("psi", 0.0)

    if data_psi:
        psi_scores.append(data_psi)
    if pred_psi:
        psi_scores.append(pred_psi)
    if conf_psi:
        psi_scores.append(conf_psi)

    if psi_scores:
        results["overall_drift_score"] = float(np.mean(psi_scores))

    # Drift detected if overall PSI > warning threshold (0.1)
    results["drift_detected"] = results["overall_drift_score"] > 0.1

    return results
