"""
Unit tests for src/monitoring/statistical_tests.py
"""
import pytest
import numpy as np
import pandas as pd

from src.monitoring.statistical_tests import (
    population_stability_index,
    ks_test,
    chi_square_test,
    jensen_shannon_divergence,
    compute_drift_scores,
)


class TestPSI:
    """Tests for Population Stability Index."""

    def test_identical_distributions_return_near_zero(self):
        data = np.random.normal(0, 1, 1000)
        psi = population_stability_index(data, data)
        assert psi < 0.01

    def test_different_distributions_return_high_value(self):
        ref = np.random.normal(0, 1, 1000)
        cur = np.random.normal(5, 1, 1000)
        psi = population_stability_index(ref, cur)
        assert psi > 0.2

    def test_psi_is_non_negative(self):
        ref = np.random.uniform(0, 10, 500)
        cur = np.random.uniform(0, 10, 500)
        psi = population_stability_index(ref, cur)
        assert psi >= 0

    def test_small_shift_moderate_psi(self):
        ref = np.random.normal(0, 1, 1000)
        cur = np.random.normal(0.5, 1, 1000)
        psi = population_stability_index(ref, cur)
        assert 0.0 < psi < 1.0


class TestKSTest:
    """Tests for Kolmogorov-Smirnov test."""

    def test_same_distribution_no_drift(self):
        data = np.random.normal(0, 1, 500)
        result = ks_test(data, data)
        assert result["drift_detected"] is False
        assert result["p_value"] > 0.05

    def test_different_distributions_detect_drift(self):
        ref = np.random.normal(0, 1, 500)
        cur = np.random.normal(3, 1, 500)
        result = ks_test(ref, cur)
        assert result["drift_detected"] is True
        assert result["p_value"] < 0.05

    def test_returns_statistic_and_pvalue(self):
        ref = np.random.normal(0, 1, 100)
        cur = np.random.normal(0, 1, 100)
        result = ks_test(ref, cur)
        assert "statistic" in result
        assert "p_value" in result
        assert 0 <= result["statistic"] <= 1
        assert 0 <= result["p_value"] <= 1


class TestChiSquare:
    """Tests for Chi-Square test."""

    def test_same_distribution_no_drift(self):
        np.random.seed(42)
        cats = [1, 2, 3, 4, 5]
        ref = np.random.choice(cats, 500)
        result = chi_square_test(ref, ref)
        assert result["drift_detected"] is False

    def test_different_distributions_detect_drift(self):
        ref = np.array([1] * 100 + [2] * 100 + [3] * 100)
        cur = np.array([1] * 250 + [2] * 25 + [3] * 25)
        result = chi_square_test(ref, cur)
        assert result["drift_detected"] is True

    def test_handles_new_categories(self):
        ref = np.array([1, 1, 2, 2, 3, 3])
        cur = np.array([1, 2, 3, 4, 4, 4])
        result = chi_square_test(ref, cur)
        assert "statistic" in result


class TestJSD:
    """Tests for Jensen-Shannon Divergence."""

    def test_identical_distributions_near_zero(self):
        data = np.random.normal(0, 1, 1000)
        jsd = jensen_shannon_divergence(data, data)
        assert jsd < 0.05

    def test_different_distributions_high_value(self):
        ref = np.random.normal(0, 1, 1000)
        cur = np.random.normal(10, 1, 1000)
        jsd = jensen_shannon_divergence(ref, cur)
        assert jsd > 0.3

    def test_bounded_zero_to_one(self):
        ref = np.random.uniform(0, 1, 500)
        cur = np.random.uniform(0, 1, 500)
        jsd = jensen_shannon_divergence(ref, cur)
        assert 0 <= jsd <= 1


class TestComputeDriftScores:
    """Tests for the composite drift scoring function."""

    def test_returns_expected_keys(self, sample_inference_log):
        ref = sample_inference_log.head(100)
        cur = sample_inference_log.tail(100)
        result = compute_drift_scores(ref, cur)

        assert "data_drift" in result
        assert "prediction_drift" in result
        assert "confidence_drift" in result
        assert "overall_drift_score" in result
        assert "drift_detected" in result

    def test_identical_data_no_drift(self, sample_inference_log):
        df = sample_inference_log.head(100)
        result = compute_drift_scores(df, df)
        assert result["overall_drift_score"] < 0.1
        assert result["drift_detected"] is False

    def test_handles_empty_columns_gracefully(self):
        ref = pd.DataFrame({"other_col": [1, 2, 3]})
        cur = pd.DataFrame({"other_col": [4, 5, 6]})
        result = compute_drift_scores(ref, cur)
        assert result["overall_drift_score"] == 0.0
