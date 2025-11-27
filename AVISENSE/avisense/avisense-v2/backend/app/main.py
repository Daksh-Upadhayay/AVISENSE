from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.api import health, predict
from app.ml.model_loader import load_model
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
    
    # Load ML model
    try:
        await load_model()
        logger.info("✅ Model loaded successfully")
    except Exception as e:
        logger.error(f"❌ Failed to load model: {e}")
        logger.warning("⚠️  API will start but predictions will fail")
    
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
