"""
Unit tests for src/models/auto_trainer.py

Note: Full integration tests require PostgreSQL and MLflow running.
These unit tests validate the class structure and configuration.
"""
import pytest
import os


class TestAutoTrainerConfig:
    """Test AutoTrainer configuration and initialization."""

    def test_auto_trainer_module_importable(self):
        """Verify auto_trainer module can be imported (needs mlflow)."""
        mlflow = pytest.importorskip("mlflow", reason="mlflow not installed")
        from src.models import auto_trainer

        assert hasattr(auto_trainer, "AutoTrainer")

    def test_pipeline_config_loaded(self):
        """Verify pipeline config is accessible."""
        from src.config import PIPELINE_CONFIG

        assert "initial_percentage" in PIPELINE_CONFIG
        assert "increment_percentage" in PIPELINE_CONFIG
        assert "balancing_strategy" in PIPELINE_CONFIG
        assert PIPELINE_CONFIG["increment_percentage"] == 3.0

    def test_automation_config_loaded(self):
        """Verify automation config is accessible."""
        from src.config import AUTOMATION_CONFIG

        assert "auto_promotion_enabled" in AUTOMATION_CONFIG
        assert "min_f1_threshold" in AUTOMATION_CONFIG
        assert isinstance(AUTOMATION_CONFIG["min_f1_threshold"], float)

    def test_mlflow_config_loaded(self):
        """Verify MLflow config is accessible."""
        from src.config import MLFLOW_CONFIG

        assert "tracking_uri" in MLFLOW_CONFIG
        assert "experiment_training" in MLFLOW_CONFIG
