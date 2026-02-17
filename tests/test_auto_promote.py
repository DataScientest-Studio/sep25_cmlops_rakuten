"""
Unit tests for src/models/promotion_engine.py
"""
import pytest
import os

mlflow = pytest.importorskip("mlflow", reason="mlflow not installed")
from src.models.promotion_engine import PromotionEngine


class TestPromotionEngine:
    """Tests for PromotionEngine logic (no MLflow server required)."""

    def test_disabled_returns_not_promoted(self):
        engine = PromotionEngine.__new__(PromotionEngine)
        engine.enabled = False
        engine.model_name = "test_model"
        engine.min_f1_threshold = 0.75
        engine.decision_log_path = "/dev/null"

        result = engine.evaluate_and_promote(
            model_version=1, f1_score=0.90, run_id=None
        )
        assert result["promoted"] is False
        assert "disabled" in result["reason"].lower()

    def test_none_version_returns_not_promoted(self):
        engine = PromotionEngine.__new__(PromotionEngine)
        engine.enabled = True
        engine.model_name = "test_model"
        engine.min_f1_threshold = 0.75
        engine.decision_log_path = "/dev/null"

        result = engine.evaluate_and_promote(
            model_version=None, f1_score=0.90, run_id=None
        )
        assert result["promoted"] is False

    def test_threshold_from_env(self, monkeypatch):
        monkeypatch.setenv("MIN_F1_THRESHOLD", "0.80")
        monkeypatch.setenv("AUTO_PROMOTION_ENABLED", "true")
        monkeypatch.setenv("MLFLOW_TRACKING_URI", "http://localhost:5000")

        assert float(os.getenv("MIN_F1_THRESHOLD")) == 0.80


class TestPromotionDecisionLog:
    """Tests for decision logging."""

    def test_log_decision_writes_to_file(self, tmp_path):
        log_path = tmp_path / "decisions.jsonl"

        engine = PromotionEngine.__new__(PromotionEngine)
        engine.decision_log_path = log_path

        engine._log_decision({"promoted": True, "reason": "test"})

        content = log_path.read_text()
        assert "promoted" in content
        assert "test" in content
