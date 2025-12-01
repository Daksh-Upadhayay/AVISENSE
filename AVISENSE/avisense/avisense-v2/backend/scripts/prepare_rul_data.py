#!/usr/bin/env python3
"""
Prepare CMAPSS data for RUL training.
This script:
1. Loads raw CMAPSS training data
2. Calculates RUL for each cycle
3. Creates sequences for LSTM
4. Normalizes features
5. Saves processed data and scaler
"""

import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
import joblib
from pathlib import Path

# Column names for CMAPSS dataset
COLUMN_NAMES = [
    'engine_id', 'cycle',
    'setting_1', 'setting_2', 'setting_3',
    'sensor_1', 'sensor_2', 'sensor_3', 'sensor_4', 'sensor_5',
    'sensor_6', 'sensor_7', 'sensor_8', 'sensor_9', 'sensor_10',
    'sensor_11', 'sensor_12', 'sensor_13', 'sensor_14', 'sensor_15',
    'sensor_16', 'sensor_17', 'sensor_18', 'sensor_19', 'sensor_20',
    'sensor_21'
]

# Sensors to drop (constant or low variance in FD001)
SENSORS_TO_DROP = ['sensor_1', 'sensor_5', 'sensor_10', 'sensor_16', 'sensor_18', 'sensor_19']

# Sequence parameters
SEQUENCE_LENGTH = 30
MAX_RUL = 130  # Cap RUL at this value

def load_cmapss_data(filepath):
    """Load CMAPSS training data."""
    print(f"Loading data from {filepath}")
    df = pd.read_csv(filepath, sep='\s+', header=None, names=COLUMN_NAMES)
    print(f"Loaded {len(df)} rows, {df['engine_id'].nunique()} engines")
    return df

def calculate_rul(df):
    """Calculate RUL for each cycle."""
    print("Calculating RUL...")
    
    # For each engine, RUL = max_cycle - current_cycle
    df['RUL'] = 0
    for engine_id in df['engine_id'].unique():
        engine_data = df[df['engine_id'] == engine_id]
        max_cycle = engine_data['cycle'].max()
        df.loc[df['engine_id'] == engine_id, 'RUL'] = max_cycle - engine_data['cycle']
    
    # Cap RUL at MAX_RUL
    df['RUL'] = df['RUL'].clip(upper=MAX_RUL)
    
    print(f"RUL range: {df['RUL'].min():.1f} to {df['RUL'].max():.1f}")
    return df

def create_sequences(df, sequence_length):
    """Create sequences for LSTM training."""
    print(f"Creating sequences of length {sequence_length}...")
    
    # Features to use
    feature_cols = [col for col in df.columns if col.startswith('setting_') or col.startswith('sensor_')]
    feature_cols = [col for col in feature_cols if col not in SENSORS_TO_DROP]
    
    print(f"Using {len(feature_cols)} features: {feature_cols}")
    
    sequences = []
    targets = []
    
    for engine_id in df['engine_id'].unique():
        engine_data = df[df['engine_id'] == engine_id].sort_values('cycle')
        
        # Extract features and RUL
        features = engine_data[feature_cols].values
        rul_values = engine_data['RUL'].values
        
        # Create sequences
        for i in range(len(features) - sequence_length + 1):
            seq = features[i:i+sequence_length]
            target = rul_values[i+sequence_length-1]  # RUL at end of sequence
            
            sequences.append(seq)
            targets.append(target)
    
    X = np.array(sequences)
    y = np.array(targets)
    
    print(f"Created {len(X)} sequences")
    print(f"X shape: {X.shape}, y shape: {y.shape}")
    
    return X, y, feature_cols

def normalize_features(X_train, X_val):
    """Normalize features using MinMaxScaler."""
    print("Normalizing features...")
    
    # Reshape for scaling: (samples * timesteps, features)
    n_samples, n_timesteps, n_features = X_train.shape
    X_train_reshaped = X_train.reshape(-1, n_features)
    X_val_reshaped = X_val.reshape(-1, n_features)
    
    # Fit scaler on training data
    scaler = MinMaxScaler(feature_range=(0, 1))
    X_train_scaled = scaler.fit_transform(X_train_reshaped)
    X_val_scaled = scaler.transform(X_val_reshaped)
    
    # Reshape back
    X_train_scaled = X_train_scaled.reshape(n_samples, n_timesteps, n_features)
    X_val_scaled = X_val_scaled.reshape(-1, n_timesteps, n_features)
    
    print(f"Scaled data range: [{X_train_scaled.min():.3f}, {X_train_scaled.max():.3f}]")
    
    return X_train_scaled, X_val_scaled, scaler

def main():
    # Paths
    data_path = Path("/Users/dakshupadhayay/Desktop/engine-failure-detection-/AVISENSE/avisense/CMaps/train_FD001.txt")
    output_dir = Path("backend/data/processed")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load and process data
    df = load_cmapss_data(data_path)
    df = calculate_rul(df)
    
    # Create sequences
    X, y, feature_cols = create_sequences(df, SEQUENCE_LENGTH)
    
    # Split into train/val (80/20)
    split_idx = int(0.8 * len(X))
    X_train, X_val = X[:split_idx], X[split_idx:]
    y_train, y_val = y[:split_idx], y[split_idx:]
    
    print(f"\nTrain: {len(X_train)} sequences")
    print(f"Val: {len(X_val)} sequences")
    
    # Normalize
    X_train_scaled, X_val_scaled, scaler = normalize_features(X_train, X_val)
    
    # Save processed data
    output_file = output_dir / "train_rul.npz"
    np.savez(
        output_file,
        X_train=X_train_scaled,
        y_train_rul=y_train,
        X_val=X_val_scaled,
        y_val_rul=y_val
    )
    print(f"\n✅ Saved processed data to {output_file}")
    
    # Save scaler
    scaler_file = output_dir / "rul_scaler.joblib"
    joblib.dump(scaler, scaler_file)
    print(f"✅ Saved scaler to {scaler_file}")
    
    # Save feature names for reference
    feature_file = output_dir / "rul_features.txt"
    with open(feature_file, 'w') as f:
        f.write('\n'.join(feature_cols))
    print(f"✅ Saved feature names to {feature_file}")
    
    print(f"\n📊 Summary:")
    print(f"  Features: {len(feature_cols)}")
    print(f"  Sequence length: {SEQUENCE_LENGTH}")
    print(f"  Training samples: {len(X_train)}")
    print(f"  Validation samples: {len(X_val)}")
    print(f"  RUL range: 0-{MAX_RUL} cycles")

if __name__ == "__main__":
    main()
