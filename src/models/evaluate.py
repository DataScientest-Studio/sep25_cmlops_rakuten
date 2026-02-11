"""
Model Evaluation

Calculate classification metrics and generate evaluation reports.
"""
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    classification_report,
    confusion_matrix,
)
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import pandas as pd
import logging

logger = logging.getLogger(__name__)


def calculate_metrics(y_true, y_pred, average="weighted"):
    """
    Calculate classification metrics.

    Args:
        y_true: True labels
        y_pred: Predicted labels
        average: Averaging strategy for multiclass

    Returns:
        Dictionary of metrics
    """
    metrics = {
        "accuracy": accuracy_score(y_true, y_pred),
        "f1_macro": f1_score(y_true, y_pred, average="macro", zero_division=0),
        "f1_weighted": f1_score(y_true, y_pred, average="weighted", zero_division=0),
        "precision_macro": precision_score(
            y_true, y_pred, average="macro", zero_division=0
        ),
        "precision_weighted": precision_score(
            y_true, y_pred, average="weighted", zero_division=0
        ),
        "recall_macro": recall_score(y_true, y_pred, average="macro", zero_division=0),
        "recall_weighted": recall_score(
            y_true, y_pred, average="weighted", zero_division=0
        ),
    }

    logger.info(
        f"Metrics calculated: accuracy={metrics['accuracy']:.4f}, "
        f"f1_weighted={metrics['f1_weighted']:.4f}"
    )

    return metrics


def calculate_per_class_metrics(y_true, y_pred, class_names=None):
    """
    Calculate per-class F1 scores.

    Args:
        y_true: True labels
        y_pred: Predicted labels
        class_names: Optional class names (if None, uses unique labels)

    Returns:
        Dictionary of per-class metrics
    """
    # Get unique classes
    if class_names is None:
        class_names = np.unique(np.concatenate([y_true, y_pred]))

    # Calculate per-class F1
    f1_per_class = f1_score(y_true, y_pred, labels=class_names, average=None, zero_division=0)

    per_class_metrics = {
        f"class_{cls}_f1": float(f1) for cls, f1 in zip(class_names, f1_per_class)
    }

    logger.info(f"Per-class metrics calculated for {len(class_names)} classes")

    return per_class_metrics


def generate_classification_report(y_true, y_pred, class_names=None):
    """
    Generate detailed classification report.

    Args:
        y_true: True labels
        y_pred: Predicted labels
        class_names: Optional class names

    Returns:
        String report
    """
    report = classification_report(
        y_true, y_pred, labels=class_names, zero_division=0, digits=4
    )
    return report


def plot_confusion_matrix(y_true, y_pred, class_names=None, figsize=(12, 10), normalize=True):
    """
    Plot confusion matrix.

    Args:
        y_true: True labels
        y_pred: Predicted labels
        class_names: Optional class names
        figsize: Figure size
        normalize: Whether to normalize (show percentages)

    Returns:
        Matplotlib figure
    """
    cm = confusion_matrix(y_true, y_pred, labels=class_names)

    if normalize:
        cm = cm.astype("float") / cm.sum(axis=1)[:, np.newaxis]

    fig, ax = plt.subplots(figsize=figsize)

    # Plot heatmap
    sns.heatmap(
        cm,
        annot=True,
        fmt=".2f" if normalize else "d",
        cmap="Blues",
        xticklabels=class_names if class_names is not None else "auto",
        yticklabels=class_names if class_names is not None else "auto",
        ax=ax,
        cbar_kws={"label": "Percentage" if normalize else "Count"},
    )

    ax.set_xlabel("Predicted Label")
    ax.set_ylabel("True Label")
    ax.set_title("Confusion Matrix" + (" (Normalized)" if normalize else ""))

    plt.tight_layout()

    logger.info("Confusion matrix plot generated")

    return fig


def plot_class_distribution(y_true, y_pred, class_names=None, figsize=(14, 6)):
    """
    Plot class distribution comparison (true vs predicted).

    Args:
        y_true: True labels
        y_pred: Predicted labels
        class_names: Optional class names
        figsize: Figure size

    Returns:
        Matplotlib figure
    """
    if class_names is None:
        class_names = np.unique(np.concatenate([y_true, y_pred]))

    # Count occurrences
    true_counts = pd.Series(y_true).value_counts().reindex(class_names, fill_value=0)
    pred_counts = pd.Series(y_pred).value_counts().reindex(class_names, fill_value=0)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=figsize)

    # True distribution
    ax1.bar(range(len(class_names)), true_counts.values)
    ax1.set_xlabel("Class")
    ax1.set_ylabel("Count")
    ax1.set_title("True Class Distribution")
    ax1.set_xticks(range(len(class_names)))
    ax1.set_xticklabels(class_names, rotation=45, ha="right")

    # Predicted distribution
    ax2.bar(range(len(class_names)), pred_counts.values, color="orange")
    ax2.set_xlabel("Class")
    ax2.set_ylabel("Count")
    ax2.set_title("Predicted Class Distribution")
    ax2.set_xticks(range(len(class_names)))
    ax2.set_xticklabels(class_names, rotation=45, ha="right")

    plt.tight_layout()

    logger.info("Class distribution plot generated")

    return fig
