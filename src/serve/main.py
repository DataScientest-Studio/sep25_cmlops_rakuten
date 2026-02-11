"""
FastAPI Main Application

Rakuten Product Classification API with MLflow integration.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import sys

from . import config
from .routes import router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Rakuten Product Classification API",
    description="ML model serving with MLflow registry integration, Prometheus metrics, and inference logging",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(router)


@app.on_event("startup")
async def startup_event():
    """Startup event handler"""
    logger.info("=" * 80)
    logger.info("Rakuten Product Classification API Starting")
    logger.info("=" * 80)
    logger.info(f"MLflow URI: {config.MLFLOW_TRACKING_URI}")
    logger.info(f"Model: {config.MODEL_NAME} (stage={config.MODEL_STAGE})")
    logger.info(f"Inference log: {config.INFERENCE_LOG_PATH}")
    logger.info("=" * 80)

    # Pre-load model on startup (optional)
    try:
        from .model_loader import model_loader
        
        logger.info("Pre-loading model from registry...")
        model_loader._load_from_registry()
        logger.info("Model pre-loaded successfully")
    except Exception as e:
        logger.warning(f"Could not pre-load model (will load on first request): {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event handler"""
    logger.info("Rakuten API shutting down...")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=config.API_HOST,
        port=config.API_PORT,
        reload=False,
        log_level="info",
    )
