"""
Pydantic Schemas for Request/Response Models
"""
from typing import Dict, Optional
from pydantic import BaseModel, Field


class PredictionRequest(BaseModel):
    """Request model for prediction endpoint"""

    designation: str = Field(
        ..., description="Product name/title", min_length=1, max_length=1000
    )
    description: str = Field(
        ..., description="Product description", min_length=1, max_length=10000
    )
    imageid: Optional[int] = Field(
        None, description="Image ID (optional, not used in baseline model)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "designation": "iPhone 13 Pro 128GB",
                "description": "Smartphone Apple iPhone 13 Pro, 128GB storage, 5G, ProMotion display",
                "imageid": 1234567890,
            }
        }


class PredictionResponse(BaseModel):
    """Response model for prediction endpoint"""

    predicted_class: int = Field(..., description="Predicted product category code")
    probabilities: Dict[str, float] = Field(
        ..., description="Top 5 class probabilities"
    )
    confidence: float = Field(
        ..., description="Confidence score (max probability)", ge=0.0, le=1.0
    )
    prediction_id: str = Field(
        ..., description="Unique prediction ID for tracking"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "predicted_class": 2280,
                "probabilities": {
                    "2280": 0.87,
                    "40": 0.08,
                    "2403": 0.03,
                    "1280": 0.01,
                    "2705": 0.01,
                },
                "confidence": 0.87,
                "prediction_id": "pred_20260211_143022_abc123",
            }
        }


class HealthResponse(BaseModel):
    """Response model for health check endpoint"""

    status: str = Field(..., description="Overall service status")
    model: Dict = Field(..., description="Model information")
    mlflow: Dict = Field(..., description="MLflow connectivity status")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "model": {
                    "name": "rakuten_classifier",
                    "version": "3",
                    "stage": "Production",
                    "loaded": True,
                },
                "mlflow": {"reachable": True, "uri": "http://mlflow:5000"},
            }
        }
