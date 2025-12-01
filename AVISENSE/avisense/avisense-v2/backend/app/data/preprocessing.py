"""
Preprocessing utilities for time-series data.

Handles scaling, missing data, validation, and optional augmentation.
"""

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler, RobustScaler
from typing import Dict, List, Optional, Tuple, Literal
import joblib
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class TimeSeriesScaler:
    """
    Scaler for time-series data with artifact persistence.
    
    Supports StandardScaler and RobustScaler per feature.
    """
    
    def __init__(self, scaler_type: Literal['standard', 'robust'] = 'standard'):
        """
        Initialize scaler.
        
        Args:
            scaler_type: 'standard' for StandardScaler, 'robust' for RobustScaler
        """
        self.scaler_type = scaler_type
        if scaler_type == 'standard':
            self.scaler = StandardScaler()
        elif scaler_type == 'robust':
            self.scaler = RobustScaler()
        else:
            raise ValueError(f"Unknown scaler_type: {scaler_type}")
        
        self.feature_names = None
        self.is_fitted = False
    
    def fit(self, data: np.ndarray, feature_names: Optional[List[str]] = None):
        """
        Fit scaler on training data.
        
        Args:
            data: (N, n_features) or (N, window_length, n_features)
            feature_names: Optional feature names for metadata
        """
        # Reshape if 3D (sequences)
        if data.ndim == 3:
            n_samples, window_length, n_features = data.shape
            data_2d = data.reshape(-1, n_features)
        else:
            data_2d = data
            n_features = data.shape[1]
        
        self.scaler.fit(data_2d)
        self.feature_names = feature_names or [f"feature_{i}" for i in range(n_features)]
        self.is_fitted = True
        
        logger.info(f"Fitted {self.scaler_type} scaler on {data_2d.shape[0]} samples, {n_features} features")
    
    def transform(self, data: np.ndarray) -> np.ndarray:
        """
        Transform data using fitted scaler.
        
        Args:
            data: (N, n_features) or (N, window_length, n_features)
            
        Returns:
            Scaled data with same shape as input
        """
        if not self.is_fitted:
            raise ValueError("Scaler not fitted. Call fit() first.")
        
        original_shape = data.shape
        
        # Reshape if 3D
        if data.ndim == 3:
            n_samples, window_length, n_features = data.shape
            data_2d = data.reshape(-1, n_features)
        else:
            data_2d = data
        
        scaled = self.scaler.transform(data_2d)
        
        # Reshape back
        return scaled.reshape(original_shape)
    
    def fit_transform(self, data: np.ndarray, feature_names: Optional[List[str]] = None) -> np.ndarray:
        """Fit and transform in one step."""
        self.fit(data, feature_names)
        return self.transform(data)
    
    def save(self, filepath: str):
        """Save scaler to disk."""
        if not self.is_fitted:
            raise ValueError("Cannot save unfitted scaler")
        
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        
        artifact = {
            'scaler': self.scaler,
            'scaler_type': self.scaler_type,
            'feature_names': self.feature_names
        }
        joblib.dump(artifact, filepath)
        logger.info(f"Saved scaler to {filepath}")
    
    @classmethod
    def load(cls, filepath: str) -> 'TimeSeriesScaler':
        """Load scaler from disk."""
        artifact = joblib.load(filepath)
        
        instance = cls(scaler_type=artifact['scaler_type'])
        instance.scaler = artifact['scaler']
        instance.feature_names = artifact['feature_names']
        instance.is_fitted = True
        
        logger.info(f"Loaded scaler from {filepath}")
        return instance


def handle_missing_data(
    data: pd.DataFrame,
    strategy: Literal['ffill', 'interpolate', 'drop'] = 'ffill',
    feature_columns: Optional[List[str]] = None
) -> pd.DataFrame:
    """
    Handle missing data in time-series.
    
    Args:
        data: DataFrame with potential missing values
        strategy: 'ffill' (forward-fill), 'interpolate' (linear), or 'drop'
        feature_columns: Columns to apply strategy to (None = all numeric)
        
    Returns:
        DataFrame with missing data handled
    """
    data = data.copy()
    
    if feature_columns is None:
        feature_columns = data.select_dtypes(include=[np.number]).columns.tolist()
    
    missing_before = data[feature_columns].isnull().sum().sum()
    
    if strategy == 'ffill':
        data[feature_columns] = data[feature_columns].fillna(method='ffill')
        # Backfill any remaining (at start of series)
        data[feature_columns] = data[feature_columns].fillna(method='bfill')
    elif strategy == 'interpolate':
        data[feature_columns] = data[feature_columns].interpolate(method='linear', limit_direction='both')
    elif strategy == 'drop':
        data = data.dropna(subset=feature_columns)
    else:
        raise ValueError(f"Unknown strategy: {strategy}")
    
    missing_after = data[feature_columns].isnull().sum().sum()
    
    logger.info(f"Missing data: {missing_before} → {missing_after} (strategy={strategy})")
    
    return data


def validate_data(data: pd.DataFrame, label_col: Optional[str] = None) -> Dict[str, any]:
    """
    Validate data quality and return report.
    
    Args:
        data: DataFrame to validate
        label_col: Optional label column for class imbalance check
        
    Returns:
        Dict with validation metrics
    """
    report = {}
    
    # Missing data
    missing_counts = data.isnull().sum()
    missing_pct = (missing_counts / len(data) * 100).round(2)
    report['missing_data'] = {
        col: {'count': int(count), 'percent': float(pct)}
        for col, count, pct in zip(missing_counts.index, missing_counts.values, missing_pct.values)
        if count > 0
    }
    
    # Class imbalance (if label provided)
    if label_col and label_col in data.columns:
        class_counts = data[label_col].value_counts()
        report['class_distribution'] = {
            int(cls): int(count) for cls, count in class_counts.items()
        }
        if len(class_counts) == 2:
            minority_class = class_counts.min()
            majority_class = class_counts.max()
            report['imbalance_ratio'] = float(majority_class / minority_class)
    
    # Feature statistics
    numeric_cols = data.select_dtypes(include=[np.number]).columns
    report['feature_stats'] = {
        'n_features': len(numeric_cols),
        'n_samples': len(data)
    }
    
    # Distribution summary (mean, std, min, max for each feature)
    stats = data[numeric_cols].describe().loc[['mean', 'std', 'min', 'max']].to_dict()
    report['distributions'] = {
        col: {stat: float(val) for stat, val in stats_dict.items()}
        for col, stats_dict in stats.items()
    }
    
    logger.info(f"Data validation: {len(data)} samples, {len(numeric_cols)} features")
    if report['missing_data']:
        logger.warning(f"Found missing data in {len(report['missing_data'])} columns")
    
    return report


def augment_sequences(
    sequences: np.ndarray,
    labels: np.ndarray,
    methods: List[str] = ['jitter'],
    jitter_std: float = 0.01,
    noise_std: float = 0.05,
    augmentation_factor: int = 1
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Augment sequences with synthetic variations.
    
    Args:
        sequences: (N, window_length, n_features)
        labels: (N,) corresponding labels
        methods: List of augmentation methods ['jitter', 'noise', 'scale']
        jitter_std: Standard deviation for jitter
        noise_std: Standard deviation for Gaussian noise
        augmentation_factor: Number of augmented copies per original
        
    Returns:
        Augmented (sequences, labels)
    """
    augmented_sequences = [sequences]
    augmented_labels = [labels]
    
    for _ in range(augmentation_factor):
        aug_seq = sequences.copy()
        
        for method in methods:
            if method == 'jitter':
                # Add small random jitter
                jitter = np.random.normal(0, jitter_std, aug_seq.shape)
                aug_seq += jitter
            elif method == 'noise':
                # Add Gaussian noise
                noise = np.random.normal(0, noise_std, aug_seq.shape)
                aug_seq += noise
            elif method == 'scale':
                # Random scaling
                scale = np.random.uniform(0.95, 1.05, (aug_seq.shape[0], 1, aug_seq.shape[2]))
                aug_seq *= scale
        
        augmented_sequences.append(aug_seq)
        augmented_labels.append(labels)
    
    final_sequences = np.concatenate(augmented_sequences, axis=0)
    final_labels = np.concatenate(augmented_labels, axis=0)
    
    logger.info(f"Augmented {len(sequences)} → {len(final_sequences)} sequences (factor={augmentation_factor}, methods={methods})")
    
    return final_sequences, final_labels
