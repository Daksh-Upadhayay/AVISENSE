import joblib
import numpy as np
from pathlib import Path
import logging
from typing import Optional
from app.config import settings

logger = logging.getLogger(__name__)

# Global model storage
_model = None
_scaler = None
_model_info = None
_anomaly_scorer = None  # For deep learning autoencoder
_lstm_scorer = None     # For LSTM autoencoder
_sequence_handler = None # For managing LSTM sequences


async def load_model():
    """Load ML model and scaler from disk or Supabase Storage."""
    global _model, _scaler, _model_info
    
    try:
        model_path = Path(settings.MODEL_PATH)
        
        # Load RandomForest model
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


async def load_autoencoder():
    """Load deep learning autoencoder for anomaly detection."""
    global _anomaly_scorer
    
    try:
        from app.ml.anomaly_scorer import load_autoencoder_scorer
        
        # Paths to autoencoder artifacts
        ae_model_path = Path("models/deep/dense_ae_v1.pt")
        ae_scaler_path = Path("data/processed/scaler.joblib")
        
        if not ae_model_path.exists():
            logger.warning(f"Autoencoder model not found at {ae_model_path}")
            logger.warning("Deep learning features will be disabled")
            return False
        
        logger.info(f"Loading autoencoder from {ae_model_path}")
        _anomaly_scorer = load_autoencoder_scorer(
            str(ae_model_path),
            str(ae_scaler_path),
            device='cpu'
        )
        
        logger.info("✅ Autoencoder loaded successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to load autoencoder: {e}")
        logger.warning("Deep learning features will be disabled")
        return False


async def load_lstm_autoencoder():
    """Load LSTM autoencoder for temporal anomaly detection."""
    global _lstm_scorer, _sequence_handler
    
    try:
        from app.ml.lstm_scorer import LSTMAnomalyScorer
        from app.ml.models.autoencoder import LSTMAutoencoder
        from app.ml.sequence_handler import SequenceHandler
        import torch
        import yaml
        
        # Paths
        lstm_model_path = Path("models/deep/lstm_ae_v1.pt")
        config_path = Path("configs/model_configs/lstm_autoencoder_config.yaml")
        scaler_path = Path("data/processed/scaler.joblib")
        
        if not lstm_model_path.exists():
            logger.warning(f"LSTM model not found at {lstm_model_path}")
            return False
            
        # Load config
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            
        # Initialize model
        input_dim = config['model']['input_dim']
        hidden_dims = config['model']['hidden_dims']
        latent_dim = config['model']['latent_dim']
        bidirectional = config['model']['bidirectional']
        
        model = LSTMAutoencoder(
            input_dim=input_dim,
            hidden_dims=hidden_dims,
            latent_dim=latent_dim,
            bidirectional=bidirectional
        )
        
        # Load weights
        checkpoint = torch.load(lstm_model_path, map_location='cpu')
        model.load_state_dict(checkpoint['model_state_dict'])
        
        # Initialize scorer
        # We reuse the scaler from the dense AE (or load it again)
        # Assuming scaler is compatible (same features)
        if _scaler is None:
            # Need to load scaler if not already loaded
            # But usually load_model() is called first
            pass
            
        # We need a TimeSeriesScaler wrapper for the scorer
        from app.data import TimeSeriesScaler
        # Load the scaler used for LSTM training
        ts_scaler = TimeSeriesScaler.load(str(scaler_path))
        
        _lstm_scorer = LSTMAnomalyScorer(model, ts_scaler, device='cpu')
        
        # Initialize sequence handler
        _sequence_handler = SequenceHandler(
            window_length=config['data']['window_length'],
            n_features=input_dim
        )
        
        logger.info("✅ LSTM Autoencoder loaded successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to load LSTM autoencoder: {e}")
        return False


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


def get_lstm_scorer():
    """Get the loaded LSTM scorer."""
    return _lstm_scorer


def get_sequence_handler():
    """Get the sequence handler."""
    return _sequence_handler


def get_anomaly_scorer() -> Optional[any]:
    """Get the anomaly scorer (autoencoder)."""
    return _anomaly_scorer


def is_model_loaded():
    """Check if model is loaded."""
    return _model is not None and _scaler is not None



_vae_scorer = None # For VAE

async def load_vae_model():
    """Load Variational Autoencoder for probabilistic anomaly detection."""
    global _vae_scorer, _sequence_handler
    
    try:
        from app.ml.anomaly_scorer import VAEAnomalyScorer
        from app.ml.models.vae import VAE
        from app.ml.sequence_handler import SequenceHandler
        import torch
        import yaml
        
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
        checkpoint = torch.load(vae_model_path, map_location='cpu')
        model.load_state_dict(checkpoint['model_state_dict'])
        
        # Initialize scorer
        from app.data import TimeSeriesScaler
        ts_scaler = TimeSeriesScaler.load(str(scaler_path))
        
        _vae_scorer = VAEAnomalyScorer(model, ts_scaler, device='cpu')
        
        # Initialize sequence handler (shared if compatible, or new)
        # VAE and LSTM use same sequence length (32) and features
        if _sequence_handler is None:
            _sequence_handler = SequenceHandler(
                window_length=config['architecture']['sequence_length'],
                n_features=config['architecture']['input_dim']
            )
        
        logger.info("✅ VAE model loaded successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to load VAE model: {e}")
        return False

def get_vae_scorer():
    """Get the loaded VAE scorer."""
    return _vae_scorer

def is_autoencoder_loaded():
    """Check if autoencoder is loaded."""
    return _anomaly_scorer is not None

_rul_model = None # For RUL regression
_rul_scaler = None # Scaler for RUL model (18 features)

async def load_rul_model():
    """Load RUL regression model."""
    global _rul_model, _sequence_handler, _rul_scaler
    
    try:
        from app.ml.models.rul_regressor import RULRegressor
        from app.ml.sequence_handler import SequenceHandler
        import torch
        import yaml
        
        # Paths
        rul_model_path = Path("models/deep/rul_lstm_v1.pt")
        config_path = Path("configs/model_configs/rul_regressor_config.yaml")
        scaler_path = Path("data/processed/scaler.joblib")
        
        if not rul_model_path.exists():
            logger.warning(f"RUL model not found at {rul_model_path}")
            return False
            
        # Load config
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            
        # Initialize model
        model = RULRegressor(
            input_dim=config['model']['input_dim'],
            hidden_dim=config['model']['hidden_dim'],
            num_layers=config['model']['num_layers'],
            dropout=config['model']['dropout']
        )
        
        # Load weights
        checkpoint = torch.load(rul_model_path, map_location='cpu')
        model.load_state_dict(checkpoint)
        model.eval()
        
        _rul_model = model
        
        # Load RUL-specific scaler (18 features)
        rul_scaler_path = Path("data/processed/rul_scaler.joblib")
        if rul_scaler_path.exists():
            _rul_scaler = joblib.load(rul_scaler_path)
            logger.info(f"✅ RUL scaler loaded ({_rul_scaler.n_features_in_} features)")
        else:
            logger.warning(f"RUL scaler not found at {rul_scaler_path}")
        
        # Initialize sequence handler if not already done
        if _sequence_handler is None:
            _sequence_handler = SequenceHandler(
                window_length=config['data']['window_length'],
                n_features=config['model']['input_dim']
            )
        
        logger.info("✅ RUL model loaded successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to load RUL model: {e}")
        return False

def get_rul_model():
    """Get the loaded RUL model."""
    return _rul_model

def get_rul_scaler():
    """Get the loaded RUL scaler."""
    return _rul_scaler
