#!/usr/bin/env python3
"""
Canonical Training Script for Avisense RUL & Risk Pipeline.
Implements:
- Engine-wise Cross-Validation
- Optuna Hyperparameter Search
- Probability Calibration
- Deterministic Artifact Generation
"""

import yaml
import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from sklearn.preprocessing import MinMaxScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import mean_absolute_error, precision_recall_curve, auc, brier_score_loss
from sklearn.model_selection import GroupKFold
import optuna
import joblib
from pathlib import Path
import logging
import sys
import random
import json
from datetime import datetime

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
COLUMN_NAMES = [
    'engine_id', 'cycle',
    'setting_1', 'setting_2', 'setting_3',
    'sensor_1', 'sensor_2', 'sensor_3', 'sensor_4', 'sensor_5',
    'sensor_6', 'sensor_7', 'sensor_8', 'sensor_9', 'sensor_10',
    'sensor_11', 'sensor_12', 'sensor_13', 'sensor_14', 'sensor_15',
    'sensor_16', 'sensor_17', 'sensor_18', 'sensor_19', 'sensor_20',
    'sensor_21'
]

def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.use_deterministic_algorithms(True, warn_only=True)

class RULRegressor(nn.Module):
    def __init__(self, input_dim, hidden_dim, num_layers, dropout):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0
        )
        self.fc = nn.Linear(hidden_dim, 1)
        
    def forward(self, x):
        out, _ = self.lstm(x)
        out = out[:, -1, :] # Last time step
        return self.fc(out)

def load_config(path):
    # Adjust path if running from backend dir
    if Path(path).exists():
        load_path = path
    elif Path("configs") / Path(path).name in Path("configs").iterdir():
         load_path = Path("configs") / Path(path).name
    else:
        # Fallback to absolute path or assume running from root
        load_path = path
        
    with open(load_path, 'r') as f:
        return yaml.safe_load(f)

def process_data(config):
    logger.info("Loading and processing data...")
    # Fix regex warning
    df = pd.read_csv(config['data']['raw_path'], sep=r'\s+', header=None, names=COLUMN_NAMES)
    
    # Drop constant sensors
    df = df.drop(columns=config['data']['sensors_to_drop'])
    
    # Calculate RUL
    rul_list = []
    for engine_id in df['engine_id'].unique():
        engine_df = df[df['engine_id'] == engine_id]
        max_cycle = engine_df['cycle'].max()
        rul_list.append(max_cycle - engine_df['cycle'])
    df['RUL'] = pd.concat(rul_list)
    
    # Cap RUL
    df['RUL_clipped'] = df['RUL'].clip(upper=config['data']['rul_cap'])
    
    # Create Binary Label (1 = Prone to Failure, 0 = Safe)
    df['label'] = (df['RUL'] <= config['data']['failure_threshold']).astype(int)
    
    return df

def create_sequences(df, config, feature_cols):
    sequences = []
    targets_rul = []
    targets_cls = []
    groups = [] # Engine IDs for GroupKFold
    
    seq_len = config['data']['sequence_length']
    
    for engine_id in df['engine_id'].unique():
        engine_data = df[df['engine_id'] == engine_id].sort_values('cycle')
        features = engine_data[feature_cols].values
        ruls = engine_data['RUL_clipped'].values
        labels = engine_data['label'].values
        
        for i in range(len(features) - seq_len + 1):
            sequences.append(features[i:i+seq_len])
            targets_rul.append(ruls[i+seq_len-1])
            targets_cls.append(labels[i+seq_len-1])
            groups.append(engine_id)
            
    return np.array(sequences), np.array(targets_rul), np.array(targets_cls), np.array(groups)

def train_rul_model(X, y, groups, config):
    logger.info("Starting RUL Model Optimization...")
    
    def objective(trial):
        hidden_dim = trial.suggest_int('hidden_dim', *config['training']['rul_model']['hidden_dim_range'])
        num_layers = trial.suggest_int('num_layers', *config['training']['rul_model']['num_layers_range'])
        dropout = trial.suggest_float('dropout', *config['training']['rul_model']['dropout_range'])
        lr = trial.suggest_float('lr', *config['training']['rul_model']['lr_range'], log=True)
        
        gkf = GroupKFold(n_splits=3) # Use 3 folds for speed in Optuna
        scores = []
        
        for train_idx, val_idx in gkf.split(X, y, groups):
            # Split
            X_train, X_val = X[train_idx], X[val_idx]
            y_train, y_val = y[train_idx], y[val_idx]
            
            # Scale (Fit on Train ONLY)
            # Flatten for scaling
            n_samples, n_timesteps, n_features = X_train.shape
            scaler = MinMaxScaler()
            X_train_flat = X_train.reshape(-1, n_features)
            X_train_scaled = scaler.fit_transform(X_train_flat).reshape(n_samples, n_timesteps, n_features)
            
            X_val_flat = X_val.reshape(-1, n_features)
            X_val_scaled = scaler.transform(X_val_flat).reshape(X_val.shape[0], n_timesteps, n_features)
            
            # Convert to Tensor
            train_dataset = TensorDataset(torch.FloatTensor(X_train_scaled), torch.FloatTensor(y_train))
            train_loader = DataLoader(train_dataset, batch_size=config['training']['rul_model']['batch_size'], shuffle=True)
            
            model = RULRegressor(n_features, hidden_dim, num_layers, dropout)
            optimizer = optim.Adam(model.parameters(), lr=lr)
            criterion = nn.MSELoss()
            
            # Train
            model.train()
            for epoch in range(10): # Reduced epochs for Optuna
                for batch_X, batch_y in train_loader:
                    optimizer.zero_grad()
                    pred = model(batch_X).squeeze()
                    loss = criterion(pred, batch_y)
                    loss.backward()
                    optimizer.step()
            
            # Eval
            model.eval()
            with torch.no_grad():
                val_pred = model(torch.FloatTensor(X_val_scaled)).squeeze()
                mae = mean_absolute_error(y_val, val_pred.numpy())
                scores.append(mae)
                
        return np.mean(scores)

    study = optuna.create_study(direction='minimize')
    study.optimize(objective, n_trials=config['training']['optuna_trials'])
    
    logger.info(f"Best RUL params: {study.best_params}")
    return study.best_params

def train_classifier(X, y, groups, config):
    logger.info("Starting Classifier Optimization...")
    
    # Flatten sequences for RF (take last timestep or flatten all?)
    # For RF, usually taking the last timestep features + some lag stats is better.
    # For simplicity/speed here, we'll take the flattened last timestep.
    X_flat = X[:, -1, :] 
    
    def objective(trial):
        n_estimators = trial.suggest_int('n_estimators', *config['training']['classifier_model']['n_estimators_range'])
        max_depth = trial.suggest_int('max_depth', *config['training']['classifier_model']['max_depth_range'])
        
        clf = RandomForestClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            random_state=config['training']['seed'],
            n_jobs=-1
        )
        
        gkf = GroupKFold(n_splits=3)
        scores = []
        
        for train_idx, val_idx in gkf.split(X_flat, y, groups):
            X_train, X_val = X_flat[train_idx], X_flat[val_idx]
            y_train, y_val = y[train_idx], y[val_idx]
            
            scaler = MinMaxScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_val_scaled = scaler.transform(X_val)
            
            clf.fit(X_train_scaled, y_train)
            probs = clf.predict_proba(X_val_scaled)[:, 1]
            
            # Metric: Precision-Recall AUC (better for imbalance)
            precision, recall, _ = precision_recall_curve(y_val, probs)
            pr_auc = auc(recall, precision)
            scores.append(pr_auc)
            
        return np.mean(scores)

    study = optuna.create_study(direction='maximize')
    study.optimize(objective, n_trials=config['training']['optuna_trials'])
    
    logger.info(f"Best Classifier params: {study.best_params}")
    return study.best_params

def main():
    config = load_config("configs/training_config.yaml")
    set_seed(config['training']['seed'])
    
    # 1. Process Data
    df = process_data(config)
    feature_cols = [c for c in df.columns if c.startswith('setting_') or c.startswith('sensor_')]
    X, y_rul, y_cls, groups = create_sequences(df, config, feature_cols)
    
    logger.info(f"Data shape: {X.shape}")
    
    # 2. Optimize & Train Final RUL Model
    # best_rul_params = train_rul_model(X, y_rul, groups, config)
    
    # USE CACHED BEST PARAMS (from previous run) to save time
    logger.info("Using cached best RUL params to skip optimization...")
    best_rul_params = {'hidden_dim': 90, 'num_layers': 1, 'dropout': 0.10515832626467185, 'lr': 0.0033757626717901526}
    
    # Train final RUL model on ALL data (or a large train split)
    # Ideally we keep a hold-out test set. Let's do a simple 80/20 split by engine for final artifacts.
    gkf = GroupKFold(n_splits=5)
    train_idx, test_idx = next(gkf.split(X, y_rul, groups))
    
    X_train, X_test = X[train_idx], X[test_idx]
    y_rul_train, y_rul_test = y_rul[train_idx], y_rul[test_idx]
    y_cls_train, y_cls_test = y_cls[train_idx], y_cls[test_idx]
    
    # Scale RUL Data
    n_samples, n_timesteps, n_features = X_train.shape
    rul_scaler = MinMaxScaler()
    X_train_flat = X_train.reshape(-1, n_features)
    X_train_scaled = rul_scaler.fit_transform(X_train_flat).reshape(n_samples, n_timesteps, n_features)
    X_test_scaled = rul_scaler.transform(X_test.reshape(-1, n_features)).reshape(X_test.shape[0], n_timesteps, n_features)
    
    # Train RUL
    # Extract LR from params as it's not a model arg
    train_params = best_rul_params.copy()
    lr = train_params.pop('lr')
    
    rul_model = RULRegressor(n_features, **train_params)
    optimizer = optim.Adam(rul_model.parameters(), lr=lr)
    criterion = nn.MSELoss()
    
    train_dataset = TensorDataset(torch.FloatTensor(X_train_scaled), torch.FloatTensor(y_rul_train))
    train_loader = DataLoader(train_dataset, batch_size=config['training']['rul_model']['batch_size'], shuffle=True)
    
    logger.info("Training Final RUL Model...")
    rul_model.train()
    for epoch in range(config['training']['rul_model']['epochs']):
        for batch_X, batch_y in train_loader:
            optimizer.zero_grad()
            pred = rul_model(batch_X).squeeze()
            loss = criterion(pred, batch_y)
            loss.backward()
            optimizer.step()
            
    # Save RUL Artifacts
    output_dir = Path(config['output']['models_dir'])
    output_dir.mkdir(parents=True, exist_ok=True)
    
    torch.save(rul_model.state_dict(), output_dir / "rul_lstm_v2.0.0.pt")
    joblib.dump(rul_scaler, output_dir / "rul_scaler_v2.0.0.joblib")
    
    # 3. Optimize & Train Final Classifier with Calibration
    best_cls_params = train_classifier(X, y_cls, groups, config)
    
    # Prepare Classifier Data (Flattened Last Step)
    X_train_cls = X_train[:, -1, :]
    X_test_cls = X_test[:, -1, :]
    
    cls_scaler = MinMaxScaler()
    X_train_cls_scaled = cls_scaler.fit_transform(X_train_cls)
    X_test_cls_scaled = cls_scaler.transform(X_test_cls)
    
    # Base Classifier
    base_clf = RandomForestClassifier(
        **best_cls_params,
        random_state=config['training']['seed'],
        n_jobs=-1
    )
    
    # Calibrated Classifier
    logger.info(f"Training & Calibrating Classifier ({config['training']['classifier_model']['calibration_method']})...")
    calibrated_clf = CalibratedClassifierCV(
        estimator=base_clf,
        method=config['training']['classifier_model']['calibration_method'],
        cv=3 # Internal CV for calibration
    )
    
    calibrated_clf.fit(X_train_cls_scaled, y_cls_train)
    
    # Evaluate Calibration
    probs = calibrated_clf.predict_proba(X_test_cls_scaled)[:, 1]
    brier = brier_score_loss(y_cls_test, probs)
    logger.info(f"Classifier Brier Score: {brier:.4f}")
    
    # Save Classifier Artifacts
    joblib.dump(calibrated_clf, output_dir / "clf_calibrated_v2.0.0.joblib")
    joblib.dump(cls_scaler, output_dir / "clf_scaler_v2.0.0.joblib")
    
    # Save Metadata
    metadata = {
        "version": "v2.0.0",
        "train_date": datetime.now().isoformat(),
        "seed": config['training']['seed'],
        "features": feature_cols,
        "rul_metrics": {"mae": float(criterion(rul_model(torch.FloatTensor(X_test_scaled)).squeeze(), torch.FloatTensor(y_rul_test)).item())},
        "cls_metrics": {"brier_score": brier},
        "rul_params": best_rul_params,
        "cls_params": best_cls_params
    }
    joblib.dump(metadata, output_dir / "model_metadata_v2.0.0.joblib")
    
    logger.info("✅ All artifacts saved successfully.")

if __name__ == "__main__":
    main()
