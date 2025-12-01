"""
Enhanced model loader with GPU support and performance optimizations.
"""

import torch
from app.ml.performance import GPUManager, CircuitBreaker
from app.ml.model_loader import (
    _model, _scaler, _model_info, _anomaly_scorer, 
    _lstm_scorer, _vae_scorer, _sequence_handler
)
import logging

logger = logging.getLogger(__name__)

# Circuit breakers for each model
_rf_circuit_breaker = CircuitBreaker(failure_threshold=5, timeout_seconds=60)
_ae_circuit_breaker = CircuitBreaker(failure_threshold=5, timeout_seconds=60)
_vae_circuit_breaker = CircuitBreaker(failure_threshold=5, timeout_seconds=60)


async def load_model_with_gpu(prefer_gpu: bool = True):
    """
    Load RandomForest model (CPU only).
    
    Args:
        prefer_gpu: Ignored for RandomForest (always uses CPU)
    """
    from app.ml.model_loader import load_model
    await load_model()


async def load_autoencoder_with_gpu(prefer_gpu: bool = True):
    """
    Load autoencoder with GPU support.
    
    Args:
        prefer_gpu: Whether to use GPU if available
    """
    global _anomaly_scorer
    
    try:
        from app.ml.anomaly_scorer import load_autoencoder_scorer
        from pathlib import Path
        
        # Get device
        device = GPUManager.get_device(prefer_gpu)
        
        # Paths
        ae_model_path = Path("models/deep/dense_ae_v1.pt")
        ae_scaler_path = Path("data/processed/scaler.joblib")
        
        if not ae_model_path.exists():
            logger.warning(f"Autoencoder model not found at {ae_model_path}")
            return False
        
        logger.info(f"Loading autoencoder from {ae_model_path} on {device}")
        _anomaly_scorer = load_autoencoder_scorer(
            str(ae_model_path),
            str(ae_scaler_path),
            device=device
        )
        
        # Optimize for inference
        if _anomaly_scorer and hasattr(_anomaly_scorer, 'model'):
            _anomaly_scorer.model = GPUManager.optimize_for_inference(_anomaly_scorer.model)
        
        logger.info("✅ Autoencoder loaded successfully with GPU optimization")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to load autoencoder: {e}")
        return False


async def load_vae_with_gpu(prefer_gpu: bool = True):
    """
    Load VAE with GPU support.
    
    Args:
        prefer_gpu: Whether to use GPU if available
    """
    global _vae_scorer, _sequence_handler
    
    try:
        from app.ml.anomaly_scorer import VAEAnomalyScorer
        from app.ml.models.vae import VAE
        from app.ml.sequence_handler import SequenceHandler
        from pathlib import Path
        import yaml
        
        # Get device
        device = GPUManager.get_device(prefer_gpu)
        
        # Paths
        vae_model_path = Path("models/deep/vae_v1.pt")
        config_path = Path("configs/model_configs/vae_config.yaml")
        scaler_path = Path("data/processed/scaler.joblib")
        
        if not vae_model_path.exists():
            logger.warning(f"VAE model not found at {vae_model_path}")
            return False
        
        # Load config
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Initialize model
        model = VAE(
            input_dim=config['architecture']['input_dim'],
            hidden_dim1=config['architecture']['hidden_dim1'],
            hidden_dim2=config['architecture']['hidden_dim2'],
            latent_dim=config['architecture']['latent_dim'],
            sequence_length=config['architecture']['sequence_length']
        )
        
        # Load weights
        checkpoint = torch.load(vae_model_path, map_location=device)
        model.load_state_dict(checkpoint['model_state_dict'])
        model = model.to(device)
        
        # Optimize for inference
        model = GPUManager.optimize_for_inference(model)
        
        # Initialize scorer
        from app.data import TimeSeriesScaler
        ts_scaler = TimeSeriesScaler.load(str(scaler_path))
        
        _vae_scorer = VAEAnomalyScorer(model, ts_scaler, device=device)
        
        # Initialize sequence handler
        if _sequence_handler is None:
            _sequence_handler = SequenceHandler(
                window_length=config['architecture']['sequence_length'],
                n_features=config['architecture']['input_dim']
            )
        
        logger.info(f"✅ VAE model loaded successfully on {device}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to load VAE model: {e}")
        return False


async def predict_with_fallback(model_fn, fallback_fn, circuit_breaker, *args, **kwargs):
    """
    Execute prediction with circuit breaker and fallback.
    
    Args:
        model_fn: Primary model function
        fallback_fn: Fallback function if primary fails
        circuit_breaker: Circuit breaker instance
        *args, **kwargs: Arguments for prediction
        
    Returns:
        Prediction result with provenance
    """
    try:
        # Try primary model with circuit breaker
        result = await circuit_breaker.call(model_fn, *args, **kwargs)
        result['provenance'] = {'primary': model_fn.__name__, 'fallback': False}
        return result
        
    except Exception as e:
        logger.warning(f"Primary model failed: {e}, falling back...")
        
        # Use fallback
        try:
            result = await fallback_fn(*args, **kwargs)
            result['provenance'] = {
                'primary': model_fn.__name__,
                'fallback': True,
                'fallback_reason': str(e)
            }
            return result
        except Exception as fallback_error:
            logger.error(f"Fallback also failed: {fallback_error}")
            raise Exception(f"Both primary and fallback failed: {e}, {fallback_error}")


def get_circuit_breaker_status():
    """Get status of all circuit breakers."""
    return {
        'random_forest': _rf_circuit_breaker.state,
        'autoencoder': _ae_circuit_breaker.state,
        'vae': _vae_circuit_breaker.state
    }
