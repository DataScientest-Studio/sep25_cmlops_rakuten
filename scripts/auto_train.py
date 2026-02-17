#!/usr/bin/env python3
"""
Auto Train Script

Automated training pipeline:
  1. Generate balanced dataset from current DB state
  2. Train TF-IDF + LogisticRegression model
  3. Register model in MLflow

Usage:
    python scripts/auto_train.py
    python scripts/auto_train.py --max-features 5000 --C 1.0
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
    parser = argparse.ArgumentParser(description="Auto-train Rakuten classifier")
    parser.add_argument(
        "--max-features", type=int, default=5000, help="Max TF-IDF features"
    )
    parser.add_argument(
        "--C", type=float, default=1.0, help="Regularization parameter"
    )
    parser.add_argument(
        "--max-iter", type=int, default=1000, help="Max solver iterations"
    )
    args = parser.parse_args()

    from src.models.auto_trainer import AutoTrainer

    trainer = AutoTrainer(
        max_features=args.max_features,
        C=args.C,
        max_iter=args.max_iter,
    )

    try:
        result = trainer.run()
        logger.info(
            f"Training complete: run_id={result['run_id']}, "
            f"version={result['model_version']}, "
            f"f1={result['f1_score']:.4f}"
        )
    except Exception as e:
        logger.error(f"Auto-training failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
