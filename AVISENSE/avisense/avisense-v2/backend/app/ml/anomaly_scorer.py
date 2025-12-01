"""
Anomaly Scoring Service

Calculates anomaly scores and reconstruction errors using trained autoencoders.
"""

import torch
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging
from pathlib import Path

from app.ml.models import DenseAutoencoder
from app.data import TimeSeriesScaler

logger = logging.getLogger(__name__)


class AnomalyScorer:
    """
    Service for calculating anomaly scores using autoencoders.
    
    Provides:
    - Reconstruction error calculation
    - Per-feature error analysis
    - Anomaly score normalization
    """
    
    def __init__(
        self,
        model: DenseAutoencoder,
        scaler: TimeSeriesScaler,
        device: str = 'cpu'
    ):
        """
        Initialize anomaly scorer.
        
        Args:
            model: Trained autoencoder model
            scaler: Fitted scaler for input normalization
            device: 'cpu' or 'cuda'
        """
        self.model = model.to(device)
        self.model.eval()
        self.scaler = scaler
        self.device = device
        
        logger.info(f"Initialized AnomalyScorer on {device}")
    
    def score(
        self,
        input_data: Dict[str, float],
        return_details: bool = True
    ) -> Dict[str, any]:
        """
        Calculate anomaly score for input data.
        
        Args:
            input_data: Dict of sensor readings
            return_details: Include per-feature errors
            
        Returns:
            Dict with anomaly_score and optional reconstruction_errors
        """
        # Convert input to array
        feature_names = self.scaler.feature_names
        input_array = np.array([input_data.get(name, 0.0) for name in feature_names])
        
        # The autoencoder was trained on sequences (window_length, n_features)
        # But we're getting single timestep data
        # Solution: Repeat the single timestep to create a pseudo-sequence
        # This is a simplification - in production, you'd want actual historical data
        
        # Get window length from model input dimension
        # input_dim = window_length * n_features
        # For our model: 448 = 32 * 14
        window_length = self.model.input_dim // len(feature_names)
        
        # Create sequence by repeating the current reading
        # Shape: (window_length, n_features)
        sequence = np.tile(input_array, (window_length, 1))
        
        # Scale each timestep (scaler expects shape: (n_samples, n_features))
        # We need to scale the sequence as if each timestep is a sample
        scaled_sequence = self.scaler.scaler.transform(sequence)  # Use the underlying sklearn scaler
        
        # Flatten to match model input: (1, window_length * n_features)
        flattened = scaled_sequence.flatten().reshape(1, -1)
        
        # Convert to tensor
        input_tensor = torch.FloatTensor(flattened).to(self.device)
        
        # Calculate reconstruction error
        with torch.no_grad():
            reconstruction, _ = self.model(input_tensor)
            
            # Overall anomaly score (MSE)
            mse = torch.mean((input_tensor - reconstruction) ** 2).item()
            
            # Per-feature errors (average across time window)
            if return_details:
                # Reshape back to (window_length, n_features)
                input_reshaped = input_tensor.reshape(window_length, len(feature_names))
                recon_reshaped = reconstruction.reshape(window_length, len(feature_names))
                
                # Average error per feature across time
                per_feature_errors = torch.mean((input_reshaped - recon_reshaped) ** 2, dim=0).cpu().numpy()
            else:
                per_feature_errors = None
        
        result = {
            'anomaly_score': float(mse),
            'anomaly_score_normalized': self._normalize_score(mse)
        }
        
        if return_details and per_feature_errors is not None:
            # Create per-feature error dict
            reconstruction_errors = {}
            total_error = np.sum(per_feature_errors)
            
            for name, error in zip(feature_names, per_feature_errors):
                reconstruction_errors[name] = {
                    'error': float(error),
                    'percent': float((error / total_error * 100) if total_error > 0 else 0)
                }
            
            result['reconstruction_errors'] = reconstruction_errors
        
        return result
    
    def _normalize_score(self, score: float, min_score: float = 0.0, max_score: float = 2.0) -> float:
        """
        Normalize anomaly score to 0-1 range.
        
        Args:
            score: Raw MSE score
            min_score: Minimum expected score
            max_score: Maximum expected score (for normalization)
            
        Returns:
            Normalized score in [0, 1]
        """
        normalized = (score - min_score) / (max_score - min_score)
        return float(np.clip(normalized, 0, 1))
    
    def batch_score(
        self,
        input_batch: List[Dict[str, float]]
    ) -> List[Dict[str, any]]:
        """
        Score multiple inputs in batch.
        
        Args:
            input_batch: List of input dicts
            
        Returns:
            List of anomaly scores
        """
        return [self.score(input_data) for input_data in input_batch]


def load_autoencoder_scorer(
    model_path: str,
    scaler_path: str,
    device: str = 'cpu'
) -> AnomalyScorer:
    """
    Load trained autoencoder and create scorer.
    
    Args:
        model_path: Path to saved model (.pt file)
        scaler_path: Path to saved scaler (.joblib file)
        device: 'cpu' or 'cuda'
        
    Returns:
        Initialized AnomalyScorer
    """
    logger.info(f"Loading autoencoder from {model_path}")
    
    # Load model checkpoint (weights_only=False for compatibility with older PyTorch saves)
    checkpoint = torch.load(model_path, map_location=device, weights_only=False)
    
    # Get model config
    config = checkpoint['config']
    input_dim = checkpoint['input_dim']
    
    # Create model
    model = DenseAutoencoder(
        input_dim=input_dim,
        encoder_dims=config['model']['encoder_dims'],
        latent_dim=config['model']['latent_dim'],
        activation=config['model']['activation'],
        dropout=config['model']['dropout']
    )
    
    # Load weights
    model.load_state_dict(checkpoint['model_state_dict'])
    
    # Load scaler
    logger.info(f"Loading scaler from {scaler_path}")
    scaler = TimeSeriesScaler.load(scaler_path)
    
    # Create scorer
    scorer = AnomalyScorer(model, scaler, device)
    
    logger.info("✅ Autoencoder scorer loaded successfully")
    
    return scorer

class VAEAnomalyScorer(AnomalyScorer):
    """
    Anomaly scorer using Variational Autoencoder.
    Uses ELBO (Evidence Lower Bound) or Reconstruction Probability.
    """
    
    def score(
        self,
        input_data: Dict[str, float],
        return_details: bool = True
    ) -> Dict[str, any]:
        """
        Calculate anomaly score using VAE.
        
        Args:
            input_data: Dict of sensor readings
            return_details: Include per-feature errors
            
        Returns:
            Dict with anomaly_score (ELBO-based)
        """
        # Convert input to array
        feature_names = self.scaler.feature_names
        input_array = np.array([input_data.get(name, 0.0) for name in feature_names])
        
        # Create sequence (same logic as base Scorer)
        window_length = self.model.sequence_length
        sequence = np.tile(input_array, (window_length, 1))
        
        # Scale
        scaled_sequence = self.scaler.scaler.transform(sequence)
        
        # Reshape for VAE: (1, seq_len, n_features)
        # Note: VAE expects (batch, seq_len, input_dim)
        input_tensor = torch.FloatTensor(scaled_sequence).unsqueeze(0).to(self.device)
        
        with torch.no_grad():
            # Forward pass
            x_recon, mu, logvar = self.model(input_tensor)
            
            # Calculate Loss Components
            # 1. Reconstruction Loss (MSE)
            recon_loss = torch.mean((input_tensor - x_recon) ** 2).item()
            
            # 2. KL Divergence (Regularization)
            # KLD = -0.5 * sum(1 + log(sigma^2) - mu^2 - sigma^2)
            # We average it to keep scale similar to MSE
            kld_loss = -0.5 * torch.mean(1 + logvar - mu.pow(2) - logvar.exp()).item()
            
            # Total Anomaly Score = Reconstruction + beta * KLD
            # We use a small beta for scoring to prioritize reconstruction accuracy
            beta = 0.1
            anomaly_score = recon_loss + beta * kld_loss
            
            # Per-feature errors (based on reconstruction only)
            if return_details:
                # Average error per feature across time
                per_feature_errors = torch.mean((input_tensor - x_recon) ** 2, dim=1).squeeze(0).cpu().numpy()
            else:
                per_feature_errors = None
        
        result = {
            'anomaly_score': float(anomaly_score),
            'anomaly_score_normalized': self._normalize_score(anomaly_score, max_score=5.0), # VAE scores might be higher
            'reconstruction_loss': float(recon_loss),
            'kld_loss': float(kld_loss)
        }
        
        if return_details and per_feature_errors is not None:
            reconstruction_errors = {}
            total_error = np.sum(per_feature_errors)
            
            for name, error in zip(feature_names, per_feature_errors):
                reconstruction_errors[name] = {
                    'error': float(error),
                    'percent': float((error / total_error * 100) if total_error > 0 else 0)
                }
            
            result['reconstruction_errors'] = reconstruction_errors
            
        return result
