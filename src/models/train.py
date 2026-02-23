"""
Model Training Module

Trains TF-IDF + LogisticRegression classifier and logs to MLflow.
"""
import sys
from pathlib import Path
import logging
import os

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

import mlflow
import mlflow.sklearn
import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
import pickle

from src.features.text_features import TextFeatureExtractor
from src.models.evaluate import (
    calculate_metrics,
    calculate_per_class_metrics,
    plot_confusion_matrix,
    plot_class_distribution,
)
from src.models.model_registry import register_model, promote_model, auto_promote_if_better

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def _resolve_git_sha() -> str:
    """Resolve git commit SHA from env var, .git/HEAD file, or subprocess."""
    sha = os.getenv("GIT_COMMIT_SHA", "")
    if sha and sha != "unknown":
        return sha

    for git_dir in ["/opt/airflow/.git", str(Path(__file__).parent.parent.parent / ".git")]:
        try:
            head_path = Path(git_dir) / "HEAD"
            content = head_path.read_text().strip()
            if content.startswith("ref:"):
                ref_path = Path(git_dir) / content.split("ref:", 1)[1].strip()
                return ref_path.read_text().strip()
            return content
        except (OSError, IOError):
            continue

    try:
        import subprocess
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass

    return "unknown"


def load_dataset_from_mlflow(dataset_run_id: str) -> tuple:
    """
    Load dataset from MLflow artifacts.

    Args:
        dataset_run_id: MLflow run ID of the dataset

    Returns:
        Tuple of (train_df, test_df)
    """
    logger.info(f"Loading dataset from MLflow run: {dataset_run_id}")

    try:
        # Download train dataset artifact
        train_path = mlflow.artifacts.download_artifacts(
            artifact_uri=f"runs:/{dataset_run_id}/train_dataset.parquet"
        )
        train_df = pd.read_parquet(train_path)

        # Try to download test dataset (may not exist in dataset run)
        try:
            test_path = mlflow.artifacts.download_artifacts(
                artifact_uri=f"runs:/{dataset_run_id}/test_dataset.parquet"
            )
            test_df = pd.read_parquet(test_path)
        except:
            logger.warning("Test dataset not found in MLflow, will use split")
            test_df = None

        logger.info(f"Loaded dataset: train={len(train_df)} rows")
        if test_df is not None:
            logger.info(f"                 test={len(test_df)} rows")

        return train_df, test_df

    except Exception as e:
        logger.error(f"Failed to load dataset from MLflow: {e}")
        raise


def train_model(
    dataset_run_id: str = None,
    week_number: int = None,
    train_df: pd.DataFrame = None,
    test_df: pd.DataFrame = None,
    max_features: int = 5000,
    ngram_range: tuple = (1, 2),
    C: float = 1.0,
    max_iter: int = 1000,
    auto_register: bool = True,
    auto_promote: bool = False,
):
    """
    Train TF-IDF + LogisticRegression classifier.

    Args:
        dataset_run_id: MLflow run ID of the dataset (if loading from MLflow)
        week_number: Week number (for tagging)
        train_df: Training dataframe (alternative to loading from MLflow)
        test_df: Test dataframe (alternative to loading from MLflow)
        max_features: Max TF-IDF features
        ngram_range: N-gram range for TF-IDF
        C: Regularization parameter for LogisticRegression
        max_iter: Max iterations for LogisticRegression
        auto_register: Whether to register model in registry
        auto_promote: Whether to auto-promote to Production

    Returns:
        str: MLflow run ID of the trained model
    """
    logger.info("=" * 80)
    logger.info("🚀 Starting Model Training")
    logger.info("=" * 80)

    # Load dataset if not provided
    if train_df is None:
        if dataset_run_id is None:
            raise ValueError("Either dataset_run_id or train_df must be provided")
        train_df, test_df = load_dataset_from_mlflow(dataset_run_id)

    # Split test set if not provided
    if test_df is None:
        logger.info("Splitting train/test (80/20)")
        train_df, test_df = train_test_split(
            train_df, test_size=0.2, random_state=42, stratify=train_df["prdtypecode"]
        )

    # Prepare data
    X_train = train_df
    y_train = train_df["prdtypecode"].values
    X_test = test_df
    y_test = test_df["prdtypecode"].values

    logger.info(f"Train samples: {len(X_train)}")
    logger.info(f"Test samples: {len(X_test)}")
    logger.info(f"Number of classes: {len(np.unique(y_train))}")

    # Start MLflow run
    experiment_name = "rakuten_model_training"
    mlflow.set_experiment(experiment_name)

    with mlflow.start_run() as run:
        run_id = run.info.run_id
        logger.info(f"MLflow run started: {run_id}")

        # Log parameters
        params = {
            "max_features": max_features,
            "ngram_range_min": ngram_range[0],
            "ngram_range_max": ngram_range[1],
            "C": C,
            "max_iter": max_iter,
            "model_type": "tfidf_logreg",
            "n_train_samples": len(X_train),
            "n_test_samples": len(X_test),
            "n_classes": len(np.unique(y_train)),
        }

        if dataset_run_id:
            params["dataset_run_id"] = dataset_run_id
        if week_number:
            params["week_number"] = week_number

        mlflow.log_params(params)

        # Extract features
        logger.info("Extracting TF-IDF features...")
        feature_extractor = TextFeatureExtractor(
            max_features=max_features,
            ngram_range=ngram_range,
            min_df=2,
            max_df=0.95,
        )

        X_train_features = feature_extractor.fit_transform(X_train)
        X_test_features = feature_extractor.transform(X_test)

        logger.info(
            f"Features shape: train={X_train_features.shape}, test={X_test_features.shape}"
        )

        # Train model
        logger.info("Training LogisticRegression...")
        model = LogisticRegression(
            C=C,
            max_iter=max_iter,
            multi_class="multinomial",
            solver="lbfgs",
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
            verbose=0,
        )

        model.fit(X_train_features, y_train)
        logger.info("Model training complete")

        # Make predictions
        logger.info("Evaluating model...")
        y_pred_train = model.predict(X_train_features)
        y_pred_test = model.predict(X_test_features)

        # Calculate metrics
        train_metrics = calculate_metrics(y_train, y_pred_train)
        test_metrics = calculate_metrics(y_test, y_pred_test)

        # Log metrics
        mlflow.log_metrics({f"train_{k}": v for k, v in train_metrics.items()})
        mlflow.log_metrics({f"test_{k}": v for k, v in test_metrics.items()})

        logger.info(f"Train Accuracy: {train_metrics['accuracy']:.4f}")
        logger.info(f"Train F1 (weighted): {train_metrics['f1_weighted']:.4f}")
        logger.info(f"Test Accuracy: {test_metrics['accuracy']:.4f}")
        logger.info(f"Test F1 (weighted): {test_metrics['f1_weighted']:.4f}")

        # Per-class metrics (log only top classes to avoid too many metrics)
        test_per_class = calculate_per_class_metrics(y_test, y_pred_test)
        # Log only top 10 classes by support
        top_classes = pd.Series(y_test).value_counts().head(10).index
        for cls in top_classes:
            key = f"class_{cls}_f1"
            if key in test_per_class:
                mlflow.log_metric(f"test_{key}", test_per_class[key])

        # Create and log confusion matrix
        logger.info("Generating confusion matrix...")
        fig_cm = plot_confusion_matrix(
            y_test, y_pred_test, class_names=model.classes_, normalize=True
        )
        mlflow.log_figure(fig_cm, "confusion_matrix.png")

        # Create and log class distribution
        logger.info("Generating class distribution plots...")
        fig_dist = plot_class_distribution(y_test, y_pred_test, class_names=model.classes_)
        mlflow.log_figure(fig_dist, "class_distribution.png")

        # Create sklearn Pipeline
        logger.info("Creating model pipeline...")
        pipeline = Pipeline(
            [
                ("vectorizer", feature_extractor.vectorizer),
                ("classifier", model),
            ]
        )

        # Log model as pipeline
        logger.info("Logging model to MLflow...")
        mlflow.sklearn.log_model(
            pipeline,
            "model",
            registered_model_name=None,  # Will register separately if needed
        )

        # Also save vectorizer separately for compatibility
        import tempfile

        with tempfile.NamedTemporaryFile(mode="wb", suffix=".pkl", delete=False) as f:
            pickle.dump(feature_extractor.vectorizer, f)
            vectorizer_path = f.name

        mlflow.log_artifact(vectorizer_path, "vectorizer.pkl")
        os.unlink(vectorizer_path)

        # Log class names
        class_names_dict = {
            "classes": model.classes_.tolist(),
            "n_classes": len(model.classes_),
        }
        mlflow.log_dict(class_names_dict, "class_names.json")

        # Add tags
        tags = {
            "model_type": "tfidf_logreg",
            "git_commit_sha": _resolve_git_sha(),
        }
        if dataset_run_id:
            tags["dataset_run_id"] = dataset_run_id
        if week_number:
            tags["week"] = str(week_number)

        mlflow.set_tags(tags)

        logger.info("=" * 80)
        logger.info("✅ Model Training Complete")
        logger.info(f"   Run ID: {run_id}")
        logger.info(f"   Test F1 (weighted): {test_metrics['f1_weighted']:.4f}")
        logger.info("=" * 80)

        # Register model if requested
        if auto_register:
            logger.info("Registering model to Model Registry...")
            try:
                version = register_model(run_id, model_name="rakuten_classifier")
                logger.info(f"Model registered: version {version}")

                # Auto-promote based on performance comparison
                if auto_promote:
                    logger.info("Evaluating model for auto-promotion...")
                    promotion_result = auto_promote_if_better(
                        model_name="rakuten_classifier",
                        new_version=version,
                        new_f1_score=test_metrics["f1_weighted"],
                        min_f1_threshold=0.70,
                    )
                    
                    # Log promotion decision
                    if promotion_result["promoted"]:
                        logger.info(f"✅ Model promoted to Production!")
                        logger.info(f"   Reason: {promotion_result['reason']}")
                    else:
                        logger.info(f"📦 Model archived")
                        logger.info(f"   Reason: {promotion_result['reason']}")
                        
            except Exception as e:
                logger.error(f"Failed to register/promote model: {e}")

        return run_id


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Train Rakuten classifier")
    parser.add_argument(
        "--dataset-run-id", type=str, help="MLflow run ID of dataset"
    )
    parser.add_argument("--week-number", type=int, help="Week number")
    parser.add_argument(
        "--max-features", type=int, default=5000, help="Max TF-IDF features"
    )
    parser.add_argument("--C", type=float, default=1.0, help="Regularization parameter")
    parser.add_argument(
        "--max-iter", type=int, default=1000, help="Max iterations"
    )
    parser.add_argument(
        "--auto-register", action="store_true", help="Auto-register to registry"
    )
    parser.add_argument(
        "--auto-promote", action="store_true", help="Auto-promote to Production"
    )

    args = parser.parse_args()

    try:
        run_id = train_model(
            dataset_run_id=args.dataset_run_id,
            week_number=args.week_number,
            max_features=args.max_features,
            C=args.C,
            max_iter=args.max_iter,
            auto_register=args.auto_register,
            auto_promote=args.auto_promote,
        )
        logger.info(f"Training completed successfully: {run_id}")
    except Exception as e:
        logger.error(f"Training failed: {e}", exc_info=True)
        sys.exit(1)
