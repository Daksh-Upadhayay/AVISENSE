from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.api import health, predict
from app.ml.model_loader import load_model, load_autoencoder, load_vae_model, load_rul_model
from app.config import settings
import logging
import sys

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Avisense API",
    description="Engine failure prediction API with ML model serving",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Rate limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    logger.info("=" * 80)
    logger.info("🚀 Avisense API Starting...")
    logger.info("=" * 80)
    
    # Load ML models
    try:
        await load_model()
        await load_autoencoder()
        await load_vae_model()
        await load_rul_model()
        logger.info("✅ All models loaded successfully")
    except Exception as e:
        logger.error(f"⚠️  Deep learning model loading failed: {e}")
        logger.info("ℹ️  Continuing with RandomForest only")
    
    logger.info(f"📡 API running on {settings.API_HOST}:{settings.API_PORT}")
    logger.info(f"🔒 CORS enabled for: {settings.ALLOWED_ORIGINS}")
    logger.info("=" * 80)


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("👋 Avisense API shutting down...")


# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(predict.router, tags=["Predictions"])

# Production integration routers
from app.api import models, monitoring, feedback
app.include_router(models.router, prefix="/api", tags=["Model Registry"])
app.include_router(monitoring.router, prefix="/api", tags=["Monitoring"])
app.include_router(feedback.router, prefix="/api", tags=["Feedback"])

# Test endpoint (no auth required)
from app.api import test_predict
app.include_router(test_predict.router, tags=["Testing"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Avisense API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True,
        log_level=settings.LOG_LEVEL.lower()
    )
