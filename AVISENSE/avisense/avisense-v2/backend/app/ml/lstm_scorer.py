import torch
import numpy as np
from typing import Dict, List, Optional
import logging
from app.ml.models.autoencoder import LSTMAutoencoder
from app.data import TimeSeriesScaler

logger = logging.getLogger(__name__)

class LSTMAnomalyScorer:
    """
    Anomaly scoring service for LSTM Autoencoder.
    """
    
    def __init__(
        self,
        model: LSTMAutoencoder,
        scaler: TimeSeriesScaler,
        device: str = 'cpu'
    ):
        self.model = model.to(device)
        self.model.eval()
        self.scaler = scaler
        self.device = device
        logger.info(f"Initialized LSTMAnomalyScorer on {device}")
        
    def score(
        self,
        sequence: np.ndarray,
        return_details: bool = True
    ) -> Dict[str, any]:
        """
        Calculate anomaly score for a sequence.
        
        Args:
            sequence: Input sequence of shape (window_length, n_features)
            return_details: Include per-feature errors
            
        Returns:
            Dict with anomaly_score and details
        """
        # Scale the sequence
        # Scaler expects (n_samples, n_features), so we treat timesteps as samples
        scaled_sequence = self.scaler.scaler.transform(sequence)
        
        # Add batch dimension: (1, window_length, n_features)
        input_tensor = torch.FloatTensor(scaled_sequence).unsqueeze(0).to(self.device)
        
        with torch.no_grad():
            # Get reconstruction error
            # reconstruction_error method returns scalar (mean MSE)
            # But we might want per-feature errors too
            
            reconstruction, _ = self.model(input_tensor)
            
            # Overall MSE
            mse = torch.mean((input_tensor - reconstruction) ** 2).item()
            
            result = {
                "anomaly_score": float(mse),
                "model_type": "lstm_ae"
            }
            
            if return_details:
                # Per-feature error (averaged over time)
                # Shape: (1, window_length, n_features) -> (n_features,)
                per_feature_mse = torch.mean((input_tensor - reconstruction) ** 2, dim=(0, 1))
                
                # Map to feature names
                feature_names = self.scaler.feature_names
                errors = {
                    name: float(err)
                    for name, err in zip(feature_names, per_feature_mse.cpu().numpy())
                }
                result["reconstruction_errors"] = errors
                
                # SHAP-like values (using reconstruction error as proxy for contribution)
                total_error = sum(errors.values())
                if total_error > 0:
                    shap_values = {k: v / total_error for k, v in errors.items()}
                else:
                    shap_values = {k: 0.0 for k in errors}
                result["shap_values"] = shap_values
                
            return result
