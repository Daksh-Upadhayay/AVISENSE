from fastapi import APIRouter
from app.models import HealthResponse
from app.ml.model_loader import is_model_loaded, get_model_info
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.
    
    Returns model status and version information.
    """
    try:
        model_loaded = is_model_loaded()
        
        if model_loaded:
            model_info = get_model_info()
            model_version = model_info.get('version', 'v1.0.0')
        else:
            model_version = "unknown"
        
        return HealthResponse(
            ok=True,
            model_loaded=model_loaded,
            model_version=model_version,
            timestamp=datetime.now()
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            ok=False,
            model_loaded=False,
            model_version="error",
            timestamp=datetime.now()
        )
