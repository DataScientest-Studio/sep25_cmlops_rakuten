#!/usr/bin/env python3
"""
Auto Promote Script

Evaluates a model and promotes to Production if it meets the criteria:
  - F1 >= MIN_F1_THRESHOLD (default 0.75)
  - F1 > current Production model's F1

Usage:
    python scripts/auto_promote.py --latest
    python scripts/auto_promote.py --model-version 5 --f1-score 0.82 --run-id abc123
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Auto-promote Rakuten classifier")
    parser.add_argument("--run-id", type=str, help="MLflow run ID")
    parser.add_argument("--model-version", type=int, help="Model version to evaluate")
    parser.add_argument("--f1-score", type=float, help="F1 score of the model")
    parser.add_argument(
        "--latest",
        action="store_true",
        help="Evaluate the latest registered model version",
    )
    parser.add_argument(
        "--min-f1", type=float, default=None, help="Override minimum F1 threshold"
    )
    args = parser.parse_args()

    from src.models.promotion_engine import PromotionEngine

    engine = PromotionEngine(min_f1_threshold=args.min_f1)

    if args.latest:
        import mlflow
        from mlflow.tracking import MlflowClient
        from src.models.model_registry import get_latest_model_version

        latest = get_latest_model_version("rakuten_classifier")
        if latest is None:
            logger.error("No model versions found in registry")
            sys.exit(1)

        client = MlflowClient()
        run = client.get_run(latest["run_id"])
        f1_score = run.data.metrics.get("test_f1_weighted", 0.0)

        result = engine.evaluate_and_promote(
            model_version=latest["version"],
            f1_score=f1_score,
            run_id=latest["run_id"],
        )
    elif args.model_version is not None and args.f1_score is not None:
        result = engine.evaluate_and_promote(
            model_version=args.model_version,
            f1_score=args.f1_score,
            run_id=args.run_id,
        )
    else:
        parser.error("Provide either --latest or both --model-version and --f1-score")

    if result["promoted"]:
        logger.info("Model promoted to Production")
    else:
        logger.info(f"Model not promoted: {result.get('reason')}")


if __name__ == "__main__":
    main()
