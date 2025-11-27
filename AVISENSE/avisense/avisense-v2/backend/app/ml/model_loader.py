import joblib
import numpy as np
from pathlib import Path
import logging
from app.config import settings

logger = logging.getLogger(__name__)

# Global model storage
_model = None
_scaler = None
_model_info = None


async def load_model():
    """Load ML model and scaler from disk or Supabase Storage."""
    global _model, _scaler, _model_info
    
    try:
        model_path = Path(settings.MODEL_PATH)
        
        # Load model
        model_file = model_path / "avisense_model_cmapss.joblib"
        scaler_file = model_path / "avisense_scaler_cmapss.joblib"
        info_file = model_path / "avisense_model_cmapss_info.joblib"
        
        logger.info(f"Loading model from {model_file}")
        _model = joblib.load(model_file)
        
        logger.info(f"Loading scaler from {scaler_file}")
        _scaler = joblib.load(scaler_file)
        
        logger.info(f"Loading model info from {info_file}")
        _model_info = joblib.load(info_file)
        
        logger.info(f"✅ Model loaded successfully: {_model_info.get('model_type')}")
        logger.info(f"   Safe Recall: {_model_info.get('safe_recall', 0):.1%}")
        logger.info(f"   Failure Recall: {_model_info.get('failure_recall', 0):.1%}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to load model: {e}")
        raise


def get_model():
    """Get the loaded model."""
    if _model is None:
        raise RuntimeError("Model not loaded. Call load_model() first.")
    return _model


def get_scaler():
    """Get the loaded scaler."""
    if _scaler is None:
        raise RuntimeError("Scaler not loaded. Call load_model() first.")
    return _scaler


def get_model_info():
    """Get model metadata."""
    if _model_info is None:
        raise RuntimeError("Model info not loaded. Call load_model() first.")
    return _model_info


def is_model_loaded():
    """Check if model is loaded."""
    return _model is not None and _scaler is not None
