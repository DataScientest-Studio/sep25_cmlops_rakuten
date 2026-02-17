"""
Unit tests for src/monitoring/alerting.py
"""
import pytest

from src.monitoring.alerting import AlertManager


class TestAlertManager:
    """Tests for the AlertManager class (logic only, no DB)."""

    def test_build_message_contains_severity(self):
        manager = AlertManager.__new__(AlertManager)
        report = {
            "severity": "CRITICAL",
            "overall_drift_score": 0.35,
            "data_drift_score": 0.20,
            "prediction_drift_score": 0.15,
        }
        msg = manager._build_message(report)
        assert "CRITICAL" in msg
        assert "0.35" in msg

    def test_recommend_action_warning(self):
        manager = AlertManager.__new__(AlertManager)
        action = manager._recommend_action("WARNING")
        assert "Monitor" in action

    def test_recommend_action_alert(self):
        manager = AlertManager.__new__(AlertManager)
        action = manager._recommend_action("ALERT")
        assert "Investigate" in action or "retrain" in action.lower()

    def test_recommend_action_critical(self):
        manager = AlertManager.__new__(AlertManager)
        action = manager._recommend_action("CRITICAL")
        assert "Retrain" in action or "rollback" in action.lower()

    def test_process_ok_report_returns_none(self):
        manager = AlertManager.__new__(AlertManager)
        report = {"severity": "OK", "overall_drift_score": 0.05}
        result = manager.process_drift_report(report)
        assert result is None
