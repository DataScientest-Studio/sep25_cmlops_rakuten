"""
Unit tests for src/monitoring/drift_monitor.py
"""
import pytest
import os
import tempfile
import pandas as pd
import numpy as np

from src.monitoring.drift_monitor import DriftMonitor


class TestDriftMonitor:
    """Tests for the DriftMonitor class."""

    def test_missing_log_file_returns_error(self):
        monitor = DriftMonitor(inference_log_path="/nonexistent/path.csv")
        report = monitor.run_drift_analysis()
        assert report["status"] == "error"
        assert report["severity"] == "OK"

    def test_empty_log_returns_error(self, tmp_path):
        log_file = tmp_path / "empty.csv"
        log_file.write_text(
            "timestamp,prediction_id,designation,description,"
            "predicted_class,confidence,text_length,model_version,model_stage\n"
        )
        monitor = DriftMonitor(inference_log_path=str(log_file))
        report = monitor.run_drift_analysis()
        assert report["status"] in ("error", "insufficient_data")

    def test_insufficient_samples(self, tmp_path):
        """With <100 samples, should return insufficient_data."""
        np.random.seed(42)
        n = 50
        df = pd.DataFrame(
            {
                "timestamp": pd.date_range(end="2026-02-17", periods=n, freq="1h"),
                "prediction_id": [f"p{i}" for i in range(n)],
                "designation": ["prod"] * n,
                "description": ["desc"] * n,
                "predicted_class": np.random.choice([10, 20], n),
                "confidence": np.random.uniform(0.5, 0.9, n),
                "text_length": np.random.randint(10, 200, n),
                "model_version": ["1"] * n,
                "model_stage": ["Production"] * n,
            }
        )
        log_file = tmp_path / "small.csv"
        df.to_csv(log_file, index=False)

        monitor = DriftMonitor(inference_log_path=str(log_file))
        report = monitor.run_drift_analysis()
        assert report["status"] == "insufficient_data"

    def test_classify_severity_ok(self):
        monitor = DriftMonitor()
        assert monitor._classify_severity(0.05) == "OK"

    def test_classify_severity_warning(self):
        monitor = DriftMonitor()
        assert monitor._classify_severity(0.15) == "WARNING"

    def test_classify_severity_alert(self):
        monitor = DriftMonitor()
        assert monitor._classify_severity(0.25) == "ALERT"

    def test_classify_severity_critical(self):
        monitor = DriftMonitor()
        assert monitor._classify_severity(0.35) == "CRITICAL"

    def test_build_report_structure(self):
        monitor = DriftMonitor()
        report = monitor._build_report(
            status="completed",
            data_drift_score=0.15,
            overall_drift_score=0.12,
            severity="WARNING",
        )
        assert report["status"] == "completed"
        assert report["data_drift_score"] == 0.15
        assert report["overall_drift_score"] == 0.12
        assert report["severity"] == "WARNING"
        assert "report_date" in report
