"""
FastAPI Routes

Implements /health, /predict, and /metrics endpoints.
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
import mlflow
import numpy as np
from datetime import datetime
import logging

from schemas import PredictionRequest, PredictionResponse, HealthResponse
from model_loader import model_loader
from inference_logger import inference_logger
from metrics import track_prediction_latency, record_prediction
import config

# Add parent directory to path for src imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from src.utils.text_preprocessing import preprocess_text
except ImportError:
    # Fallback simple preprocessing
    def preprocess_text(text: str) -> str:
        return text.lower().strip()

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Health check endpoint.

    Returns service status, model information, and MLflow connectivity.
    """
    # Check MLflow connectivity
    mlflow_reachable = False
    try:
        mlflow.set_tracking_uri(config.MLFLOW_TRACKING_URI)
        # Try to ping MLflow
        from mlflow.tracking import MlflowClient
        client = MlflowClient()
        client.search_experiments(max_results=1)
        mlflow_reachable = True
    except Exception as e:
        logger.warning(f"MLflow not reachable: {e}")

    # Get model info
    model_info = model_loader.get_model_info()

    # Determine overall status
    if mlflow_reachable and model_info["loaded"]:
        status = "healthy"
    elif model_info["loaded"]:
        status = "degraded"  # Model loaded but MLflow unreachable
    else:
        status = "unhealthy"  # No model loaded

    return HealthResponse(
        status=status,
        model=model_info,
        mlflow={
            "reachable": mlflow_reachable,
            "uri": config.MLFLOW_TRACKING_URI,
        },
    )


@router.post("/predict", response_model=PredictionResponse, tags=["Prediction"])
@track_prediction_latency
async def predict(request: PredictionRequest):
    """
    Prediction endpoint.

    Accepts product designation and description, returns predicted class and probabilities.
    """
    try:
        # Load model
        model, vectorizer, model_version = model_loader.get_model()

        if model is None:
            raise HTTPException(
                status_code=503,
                detail="Model not loaded. Check /health endpoint.",
            )

        # Preprocess text
        designation_clean = preprocess_text(request.designation)
        description_clean = preprocess_text(request.description)
        combined_text = f"{designation_clean} {description_clean}"

        # Transform text to features
        if vectorizer is not None:
            X = vectorizer.transform([combined_text])
        else:
            # If no vectorizer, model must handle text directly
            # (This shouldn't happen with our setup, but handle gracefully)
            X = [[combined_text]]

        # Make prediction
        if hasattr(model, "predict_proba"):
            probabilities = model.predict_proba(X)[0]
            predicted_class_idx = int(np.argmax(probabilities))
            predicted_class = model.classes_[predicted_class_idx]
        else:
            # Model doesn't support probabilities
            predicted_class = int(model.predict(X)[0])
            probabilities = None

        # Get top 5 probabilities
        if probabilities is not None:
            top_indices = np.argsort(probabilities)[-5:][::-1]
            top_probs = {
                str(model.classes_[idx]): float(probabilities[idx])
                for idx in top_indices
            }
            confidence = float(probabilities[predicted_class_idx])
        else:
            top_probs = {str(predicted_class): 1.0}
            confidence = 1.0

        # Generate prediction ID
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        prediction_id = f"pred_{timestamp}_{hash(combined_text) % 1000000:06d}"

        # Record metrics
        text_len = len(request.designation) + len(request.description)
        record_prediction(int(predicted_class), text_len)

        # Log inference
        inference_logger.log_prediction(
            prediction_id=prediction_id,
            designation=request.designation,
            description=request.description,
            predicted_class=int(predicted_class),
            confidence=confidence,
            model_version=model_version,
            model_stage=config.MODEL_STAGE,
        )

        return PredictionResponse(
            predicted_class=int(predicted_class),
            probabilities=top_probs,
            confidence=confidence,
            prediction_id=prediction_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Prediction failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Prediction failed: {str(e)}"
        )


@router.get("/metrics", tags=["Metrics"])
async def metrics():
    """
    Prometheus metrics endpoint.

    Exports metrics in Prometheus format for scraping.
    """
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@router.get("/", tags=["Info"])
async def root():
    """Root endpoint with API information"""
    return {
        "service": "Rakuten Product Classification API",
        "version": "1.0.0",
        "model": config.MODEL_NAME,
        "stage": config.MODEL_STAGE,
        "endpoints": {
            "health": "/health",
            "predict": "/predict",
            "metrics": "/metrics",
            "docs": "/docs",
        },
    }
