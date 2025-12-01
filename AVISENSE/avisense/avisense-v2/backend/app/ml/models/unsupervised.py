"""
Unsupervised Anomaly Detection Models

Baseline models: IsolationForest, OneClassSVM
"""

from sklearn.ensemble import IsolationForest
from sklearn.svm import OneClassSVM
import numpy as np
from typing import Optional, Dict
import joblib
import logging

logger = logging.getLogger(__name__)


class IsolationForestDetector:
    """
    Isolation Forest for anomaly detection on windowed features.
    
    Good baseline for comparison with deep models.
    """
    
    def __init__(
        self,
        n_estimators: int = 100,
        contamination: float = 0.1,
        max_samples: str = 'auto',
        random_state: int = 42
    ):
        """
        Initialize Isolation Forest.
        
        Args:
            n_estimators: Number of trees
            contamination: Expected proportion of anomalies
            max_samples: Number of samples to draw for each tree
            random_state: Random seed
        """
        self.model = IsolationForest(
            n_estimators=n_estimators,
            contamination=contamination,
            max_samples=max_samples,
            random_state=random_state,
            n_jobs=-1
        )
        
        self.is_fitted = False
        logger.info(f"Created IsolationForest: n_estimators={n_estimators}, contamination={contamination}")
    
    def fit(self, X: np.ndarray):
        """
        Fit on training data.
        
        Args:
            X: Training data (N, n_features) or (N, window_length, n_features)
        """
        # Flatten if 3D (sequences)
        if X.ndim == 3:
            n_samples, window_length, n_features = X.shape
            X_flat = X.reshape(n_samples, window_length * n_features)
        else:
            X_flat = X
        
        self.model.fit(X_flat)
        self.is_fitted = True
        logger.info(f"Fitted IsolationForest on {len(X_flat)} samples")
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Predict anomalies.
        
        Args:
            X: Data to predict on
            
        Returns:
            Predictions: 1 for normal, -1 for anomaly
        """
        if not self.is_fitted:
            raise ValueError("Model not fitted. Call fit() first.")
        
        if X.ndim == 3:
            n_samples, window_length, n_features = X.shape
            X_flat = X.reshape(n_samples, window_length * n_features)
        else:
            X_flat = X
        
        return self.model.predict(X_flat)
    
    def score_samples(self, X: np.ndarray) -> np.ndarray:
        """
        Compute anomaly scores.
        
        Args:
            X: Data to score
            
        Returns:
            Anomaly scores (lower = more anomalous)
        """
        if not self.is_fitted:
            raise ValueError("Model not fitted. Call fit() first.")
        
        if X.ndim == 3:
            n_samples, window_length, n_features = X.shape
            X_flat = X.reshape(n_samples, window_length * n_features)
        else:
            X_flat = X
        
        # Negative scores: lower = more anomalous
        scores = self.model.score_samples(X_flat)
        
        # Convert to 0-1 scale (higher = more anomalous)
        # Use sigmoid transformation
        anomaly_scores = 1 / (1 + np.exp(scores))
        
        return anomaly_scores
    
    def save(self, filepath: str):
        """Save model to disk."""
        if not self.is_fitted:
            raise ValueError("Cannot save unfitted model")
        
        joblib.dump(self.model, filepath)
        logger.info(f"Saved IsolationForest to {filepath}")
    
    @classmethod
    def load(cls, filepath: str) -> 'IsolationForestDetector':
        """Load model from disk."""
        instance = cls()
        instance.model = joblib.load(filepath)
        instance.is_fitted = True
        logger.info(f"Loaded IsolationForest from {filepath}")
        return instance


class OneClassSVMDetector:
    """
    One-Class SVM for anomaly detection.
    
    Alternative baseline to Isolation Forest.
    """
    
    def __init__(
        self,
        kernel: str = 'rbf',
        nu: float = 0.1,
        gamma: str = 'scale'
    ):
        """
        Initialize One-Class SVM.
        
        Args:
            kernel: Kernel type ('rbf', 'linear', 'poly')
            nu: Upper bound on fraction of outliers
            gamma: Kernel coefficient
        """
        self.model = OneClassSVM(
            kernel=kernel,
            nu=nu,
            gamma=gamma
        )
        
        self.is_fitted = False
        logger.info(f"Created OneClassSVM: kernel={kernel}, nu={nu}")
    
    def fit(self, X: np.ndarray):
        """Fit on training data."""
        if X.ndim == 3:
            n_samples, window_length, n_features = X.shape
            X_flat = X.reshape(n_samples, window_length * n_features)
        else:
            X_flat = X
        
        self.model.fit(X_flat)
        self.is_fitted = True
        logger.info(f"Fitted OneClassSVM on {len(X_flat)} samples")
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict anomalies (1=normal, -1=anomaly)."""
        if not self.is_fitted:
            raise ValueError("Model not fitted. Call fit() first.")
        
        if X.ndim == 3:
            n_samples, window_length, n_features = X.shape
            X_flat = X.reshape(n_samples, window_length * n_features)
        else:
            X_flat = X
        
        return self.model.predict(X_flat)
    
    def decision_function(self, X: np.ndarray) -> np.ndarray:
        """
        Compute decision function (distance to separating hyperplane).
        
        Returns:
            Scores (negative = anomaly)
        """
        if not self.is_fitted:
            raise ValueError("Model not fitted. Call fit() first.")
        
        if X.ndim == 3:
            n_samples, window_length, n_features = X.shape
            X_flat = X.reshape(n_samples, window_length * n_features)
        else:
            X_flat = X
        
        scores = self.model.decision_function(X_flat)
        
        # Convert to 0-1 scale (higher = more anomalous)
        anomaly_scores = 1 / (1 + np.exp(scores))
        
        return anomaly_scores
    
    def save(self, filepath: str):
        """Save model to disk."""
        if not self.is_fitted:
            raise ValueError("Cannot save unfitted model")
        
        joblib.dump(self.model, filepath)
        logger.info(f"Saved OneClassSVM to {filepath}")
    
    @classmethod
    def load(cls, filepath: str) -> 'OneClassSVMDetector':
        """Load model from disk."""
        instance = cls()
        instance.model = joblib.load(filepath)
        instance.is_fitted = True
        logger.info(f"Loaded OneClassSVM from {filepath}")
        return instance
