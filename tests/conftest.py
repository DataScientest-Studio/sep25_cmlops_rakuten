"""
Shared test fixtures for the Rakuten MLOps pipeline tests.
"""
import sys
from pathlib import Path
import pytest
import pandas as pd
import numpy as np

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def sample_training_data():
    """Generate a small synthetic training DataFrame."""
    np.random.seed(42)
    n = 200
    classes = [10, 20, 30, 40, 50]

    data = {
        "productid": range(1, n + 1),
        "designation": [f"Product {i} designation text" for i in range(n)],
        "description": [f"Description for product {i} with details" for i in range(n)],
        "imageid": np.random.randint(1000, 9999, n),
        "image_path": [f"images/img_{i}.jpg" for i in range(n)],
        "prdtypecode": np.random.choice(classes, n),
    }
    return pd.DataFrame(data)


@pytest.fixture
def sample_inference_log():
    """Generate a synthetic inference log DataFrame."""
    np.random.seed(42)
    n = 200
    classes = [10, 20, 30, 40, 50]

    timestamps = pd.date_range(end=pd.Timestamp.now(), periods=n, freq="1h")

    data = {
        "timestamp": timestamps,
        "prediction_id": [f"pred_{i:06d}" for i in range(n)],
        "designation": [f"Product {i}" for i in range(n)],
        "description": [f"Description {i}" for i in range(n)],
        "predicted_class": np.random.choice(classes, n),
        "confidence": np.random.uniform(0.4, 0.99, n),
        "text_length": np.random.randint(10, 500, n),
        "model_version": ["3"] * n,
        "model_stage": ["Production"] * n,
    }
    return pd.DataFrame(data)


@pytest.fixture
def reference_inference_log():
    """Generate a reference period inference log (older data)."""
    np.random.seed(21)
    n = 150
    classes = [10, 20, 30, 40, 50]

    timestamps = pd.date_range(
        end=pd.Timestamp.now() - pd.Timedelta(days=10), periods=n, freq="2h"
    )

    data = {
        "timestamp": timestamps,
        "prediction_id": [f"pred_ref_{i:06d}" for i in range(n)],
        "designation": [f"Ref product {i}" for i in range(n)],
        "description": [f"Ref description {i}" for i in range(n)],
        "predicted_class": np.random.choice(classes, n),
        "confidence": np.random.uniform(0.5, 0.95, n),
        "text_length": np.random.randint(20, 400, n),
        "model_version": ["2"] * n,
        "model_stage": ["Production"] * n,
    }
    return pd.DataFrame(data)
