"""
Sequence Builder for Time-Series Data

This module provides utilities to build sequences from time-series telemetry data
for training deep learning models (LSTM, autoencoders, etc.).
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class SequenceBuilder:
    """
    Build sequences from time-series engine telemetry data.
    
    Supports:
    - Sliding windows with configurable length and stride
    - RUL (Remaining Useful Life) label generation
    - Engine-based train/val/test splitting (no leakage)
    """
    
    def __init__(
        self,
        window_length: int = 64,
        stride: int = 1,
        feature_columns: Optional[List[str]] = None
    ):
        """
        Initialize SequenceBuilder.
        
        Args:
            window_length: Number of time steps per sequence
            stride: Step size between consecutive windows
            feature_columns: List of feature column names (if None, auto-detect)
        """
        self.window_length = window_length
        self.stride = stride
        self.feature_columns = feature_columns
        
    def build_sequences(
        self,
        data: pd.DataFrame,
        engine_id_col: str = 'engine_id',
        cycle_col: str = 'cycle',
        label_col: Optional[str] = None
    ) -> Tuple[np.ndarray, np.ndarray, Optional[np.ndarray]]:
        """
        Build sequences from telemetry data using sliding windows.
        
        Args:
            data: DataFrame with columns [engine_id, cycle, features...]
            engine_id_col: Name of engine identifier column
            cycle_col: Name of time/cycle column
            label_col: Optional binary label column (0=safe, 1=failure)
            
        Returns:
            Tuple of (sequences, labels, engine_ids)
            - sequences: (N, window_length, n_features)
            - labels: (N,) binary labels for each sequence
            - engine_ids: (N,) engine IDs for each sequence
        """
        if self.feature_columns is None:
            # Auto-detect feature columns (exclude metadata)
            exclude_cols = {engine_id_col, cycle_col, label_col, 'timestamp', 'id'}
            self.feature_columns = [col for col in data.columns if col not in exclude_cols]
        
        logger.info(f"Building sequences with window={self.window_length}, stride={self.stride}")
        logger.info(f"Using {len(self.feature_columns)} features: {self.feature_columns[:5]}...")
        
        sequences = []
        labels = []
        engine_ids = []
        
        # Group by engine and process each separately
        for engine_id, engine_data in data.groupby(engine_id_col):
            # Sort by cycle
            engine_data = engine_data.sort_values(cycle_col)
            
            # Extract features
            features = engine_data[self.feature_columns].values
            n_cycles = len(features)
            
            # Create sliding windows
            for start_idx in range(0, n_cycles - self.window_length + 1, self.stride):
                end_idx = start_idx + self.window_length
                window = features[start_idx:end_idx]
                
                sequences.append(window)
                engine_ids.append(engine_id)
                
                # Label is from the last time step of the window
                if label_col and label_col in engine_data.columns:
                    label = engine_data.iloc[end_idx - 1][label_col]
                    labels.append(label)
        
        sequences = np.array(sequences, dtype=np.float32)
        engine_ids = np.array(engine_ids)
        labels = np.array(labels) if labels else None
        
        logger.info(f"Created {len(sequences)} sequences from {data[engine_id_col].nunique()} engines")
        logger.info(f"Sequence shape: {sequences.shape}")
        
        return sequences, labels, engine_ids
    
    def generate_rul_labels(
        self,
        data: pd.DataFrame,
        engine_id_col: str = 'engine_id',
        cycle_col: str = 'cycle',
        max_rul: Optional[int] = 125
    ) -> pd.DataFrame:
        """
        Generate RUL (Remaining Useful Life) labels for each time step.
        
        RUL = number of cycles until failure for that engine.
        Optionally capped at max_rul for linear scaling.
        
        Args:
            data: DataFrame with engine telemetry
            engine_id_col: Engine identifier column
            cycle_col: Time/cycle column
            max_rul: Cap RUL at this value (None for no cap)
            
        Returns:
            DataFrame with added 'rul' column
        """
        data = data.copy()
        
        def calculate_rul(group):
            max_cycle = group[cycle_col].max()
            group['rul'] = max_cycle - group[cycle_col]
            if max_rul is not None:
                group['rul'] = group['rul'].clip(upper=max_rul)
            return group
        
        data = data.groupby(engine_id_col, group_keys=False).apply(calculate_rul)
        
        logger.info(f"Generated RUL labels (max_rul={max_rul})")
        logger.info(f"RUL range: [{data['rul'].min():.1f}, {data['rul'].max():.1f}]")
        
        return data
    
    def build_rul_sequences(
        self,
        data: pd.DataFrame,
        engine_id_col: str = 'engine_id',
        cycle_col: str = 'cycle'
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Build sequences with RUL targets for regression.
        
        Args:
            data: DataFrame with 'rul' column
            engine_id_col: Engine identifier column
            cycle_col: Time/cycle column
            
        Returns:
            Tuple of (sequences, rul_targets, engine_ids)
        """
        if 'rul' not in data.columns:
            raise ValueError("Data must have 'rul' column. Call generate_rul_labels() first.")
        
        sequences, _, engine_ids = self.build_sequences(
            data, engine_id_col, cycle_col, label_col=None
        )
        
        # Extract RUL target from last time step of each window
        rul_targets = []
        for engine_id, engine_data in data.groupby(engine_id_col):
            engine_data = engine_data.sort_values(cycle_col)
            rul_values = engine_data['rul'].values
            
            for start_idx in range(0, len(rul_values) - self.window_length + 1, self.stride):
                end_idx = start_idx + self.window_length
                # RUL target is from the last time step
                rul_targets.append(rul_values[end_idx - 1])
        
        rul_targets = np.array(rul_targets, dtype=np.float32)
        
        logger.info(f"Created {len(sequences)} sequences with RUL targets")
        logger.info(f"RUL target range: [{rul_targets.min():.1f}, {rul_targets.max():.1f}]")
        
        return sequences, rul_targets, engine_ids
    
    def split_by_engines(
        self,
        sequences: np.ndarray,
        labels: np.ndarray,
        engine_ids: np.ndarray,
        train_ratio: float = 0.7,
        val_ratio: float = 0.15,
        random_seed: int = 42
    ) -> Dict[str, Tuple[np.ndarray, np.ndarray]]:
        """
        Split sequences by engines to prevent data leakage.
        
        Args:
            sequences: (N, window_length, n_features)
            labels: (N,) labels or RUL targets
            engine_ids: (N,) engine identifiers
            train_ratio: Fraction for training
            val_ratio: Fraction for validation (rest goes to test)
            random_seed: Random seed for reproducibility
            
        Returns:
            Dict with keys 'train', 'val', 'test', each containing (X, y)
        """
        np.random.seed(random_seed)
        
        unique_engines = np.unique(engine_ids)
        n_engines = len(unique_engines)
        
        # Shuffle engines
        shuffled_engines = np.random.permutation(unique_engines)
        
        # Split engines
        n_train = int(n_engines * train_ratio)
        n_val = int(n_engines * val_ratio)
        
        train_engines = set(shuffled_engines[:n_train])
        val_engines = set(shuffled_engines[n_train:n_train + n_val])
        test_engines = set(shuffled_engines[n_train + n_val:])
        
        # Create masks
        train_mask = np.array([eid in train_engines for eid in engine_ids])
        val_mask = np.array([eid in val_engines for eid in engine_ids])
        test_mask = np.array([eid in test_engines for eid in engine_ids])
        
        # Handle None labels
        if labels is not None:
            splits = {
                'train': (sequences[train_mask], labels[train_mask]),
                'val': (sequences[val_mask], labels[val_mask]),
                'test': (sequences[test_mask], labels[test_mask])
            }
        else:
            splits = {
                'train': (sequences[train_mask], None),
                'val': (sequences[val_mask], None),
                'test': (sequences[test_mask], None)
            }
        
        logger.info(f"Split {n_engines} engines: train={len(train_engines)}, val={len(val_engines)}, test={len(test_engines)}")
        logger.info(f"Sequence counts: train={train_mask.sum()}, val={val_mask.sum()}, test={test_mask.sum()}")
        
        return splits
