"""
Prometheus Metrics Instrumentation
"""
from prometheus_client import Counter, Histogram, Gauge, Info
import time
from functools import wraps


# Metrics definitions
predictions_total = Counter(
    "rakuten_predictions_total",
    "Total number of predictions made",
    ["prdtypecode"],
)

prediction_latency = Histogram(
    "rakuten_prediction_latency_seconds",
    "Prediction latency in seconds",
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

text_length = Histogram(
    "rakuten_text_len_chars",
    "Input text length in characters",
    buckets=(50, 100, 250, 500, 1000, 2500, 5000, 10000),
)

model_version_gauge = Gauge(
    "rakuten_model_version",
    "Current model version number",
)

model_load_timestamp = Gauge(
    "rakuten_model_load_timestamp",
    "Timestamp of last model load",
)

model_info = Info(
    "rakuten_model",
    "Model metadata"
)

api_errors_total = Counter(
    "rakuten_api_errors_total",
    "Total API errors",
    ["error_type"],
)


def track_prediction_latency(func):
    """Decorator to track prediction latency"""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            duration = time.time() - start_time
            prediction_latency.observe(duration)
            return result
        except Exception as e:
            api_errors_total.labels(error_type=type(e).__name__).inc()
            raise

    return wrapper


def update_model_metrics(model_name: str, version: str, stage: str):
    """Update model metadata metrics"""
    try:
        # Try to extract numeric version
        version_num = int(version) if version.isdigit() else 0
        model_version_gauge.set(version_num)
    except:
        model_version_gauge.set(0)

    model_load_timestamp.set(time.time())
    model_info.info({
        "name": model_name,
        "version": str(version),
        "stage": stage,
    })


def record_prediction(predicted_class: int, text_len: int):
    """Record prediction metrics"""
    predictions_total.labels(prdtypecode=str(predicted_class)).inc()
    text_length.observe(text_len)
