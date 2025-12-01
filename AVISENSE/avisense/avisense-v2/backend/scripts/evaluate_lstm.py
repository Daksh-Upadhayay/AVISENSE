#!/usr/bin/env python3
"""
Evaluate Trained LSTM Autoencoder
"""

import argparse
import yaml
import numpy as np
import torch
from torch.utils.data import DataLoader, TensorDataset
from pathlib import Path
import logging
import json
import sys

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.ml.models.autoencoder import LSTMAutoencoder
from app.ml.evaluation.metrics import AnomalyMetrics

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_data(data_path):
    data = np.load(data_path, allow_pickle=True)
    X = data['X']
    # For evaluation, we need labels to calculate AUROC
    y = data.get('y')
    
    # Handle None or object array labels
    if y is not None and y.dtype == object:
        # Check if it contains actual data or just None
        try:
            y = y.astype(np.float32)
        except (ValueError, TypeError):
            y = None
            
    return X, y

def evaluate():
    # Config
    model_path = "models/deep/lstm_ae_v1.pt"
    data_path = "data/processed/test.npz"
    config_path = "configs/model_configs/lstm_autoencoder_config.yaml"
    
    # Load config
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
        
    # Load data
    logger.info(f"Loading test data from {data_path}")
    X_test, y_test = load_data(data_path)
    
    logger.info(f"X_test shape: {X_test.shape}")
    if y_test is not None:
        logger.info(f"y_test shape: {y_test.shape}, dtype: {y_test.dtype}")
    else:
        logger.warning("y_test is None")

    if y_test is None:
        logger.error("Test data has no labels, cannot evaluate anomaly detection performance")
        return

    # Create dataloader
    # Ensure y_test is a numpy array of floats
    y_test = np.array(y_test, dtype=np.float32)
    
    dataset = TensorDataset(torch.FloatTensor(X_test), torch.FloatTensor(y_test))
    dataloader = DataLoader(dataset, batch_size=config['training']['batch_size'], shuffle=False)
    
    # Load model
    device = torch.device('cpu')
    checkpoint = torch.load(model_path, map_location=device)
    
    model = LSTMAutoencoder(
        input_dim=config['model']['input_dim'],
        hidden_dims=config['model']['hidden_dims'],
        latent_dim=config['model']['latent_dim'],
        dropout=config['model']['dropout'],
        bidirectional=config['model']['bidirectional']
    ).to(device)
    
    model.load_state_dict(checkpoint['model_state_dict'])
    model.eval()
    logger.info(f"Loaded model from {model_path}")
    
    # Evaluate
    all_errors = []
    all_labels = []
    
    with torch.no_grad():
        for batch_X, batch_y in dataloader:
            batch_X = batch_X.to(device)
            errors = model.reconstruction_error(batch_X, reduction='none')
            all_errors.extend(errors.cpu().numpy())
            all_labels.extend(batch_y.numpy())
            
    all_errors = np.array(all_errors)
    all_labels = np.array(all_labels)
    
    # Calculate metrics
    metrics = AnomalyMetrics.calculate(all_labels, all_errors)
    
    print("\n" + "="*60)
    print("LSTM Autoencoder Evaluation Results")
    print("="*60)
    print(f"AUROC: {metrics['auroc']:.4f}")
    print(f"Precision @ 10%: {metrics.get('precision_at_10pct', 'N/A')}")
    print(f"Precision @ 20%: {metrics.get('precision_at_20pct', 'N/A')}")
    print("="*60 + "\n")

if __name__ == "__main__":
    evaluate()
