#!/usr/bin/env python3
"""
Train LSTM Autoencoder for Temporal Anomaly Detection

Usage:
    python scripts/train_lstm_autoencoder.py \\
        --config configs/model_configs/lstm_autoencoder_config.yaml \\
        --data data/processed/train.npz \\
        --output models/deep/lstm_ae_v1.pt
"""

import argparse
import yaml
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from pathlib import Path
import logging
import json
from datetime import datetime

# Add backend to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.ml.models.autoencoder import LSTMAutoencoder
from app.ml.training.trainer import ModelTrainer
from app.ml.evaluation.metrics import AnomalyMetrics

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_config(config_path: str) -> dict:
    """Load YAML configuration."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def load_data(data_path: str):
    """Load processed sequence data."""
    logger.info(f"Loading data from {data_path}")
    data = np.load(data_path, allow_pickle=True)
    
    X = data['X']  # Shape: (n_samples, window_length, n_features)
    
    # Labels might be None for unsupervised learning (autoencoders don't need labels)
    y = data.get('y', None)
    if y is not None and y.dtype == object:
        # If y is None object array, treat as no labels
        y = None
    
    logger.info(f"Loaded {len(X)} sequences with shape {X.shape}")
    if y is not None:
        logger.info(f"Failure samples: {np.sum(y)} ({np.mean(y)*100:.1f}%)")
    else:
        logger.info("No labels (unsupervised learning)")
    
    return X, y


def create_dataloaders(X, y, config):
    """Create train/val/test dataloaders."""
    n_samples = len(X)
    
    # Split indices
    train_size = int(n_samples * config['data']['train_split'])
    val_size = int(n_samples * config['data']['val_split'])
    
    # Shuffle if enabled
    if config['data']['shuffle']:
        indices = np.random.permutation(n_samples)
    else:
        indices = np.arange(n_samples)
    
    train_idx = indices[:train_size]
    val_idx = indices[train_size:train_size + val_size]
    test_idx = indices[train_size + val_size:]
    
    # Create datasets (autoencoders don't need labels, use X as both input and target)
    train_dataset = TensorDataset(
        torch.FloatTensor(X[train_idx]),
        torch.FloatTensor(X[train_idx])  # Use X as target for autoencoder
    )
    val_dataset = TensorDataset(
        torch.FloatTensor(X[val_idx]),
        torch.FloatTensor(X[val_idx])
    )
    test_dataset = TensorDataset(
        torch.FloatTensor(X[test_idx]),
        torch.FloatTensor(X[test_idx])
    )
    
    # Create dataloaders
    batch_size = config['training']['batch_size']
    
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False)
    
    logger.info(f"Created dataloaders: train={len(train_loader)}, val={len(val_loader)}, test={len(test_loader)}")
    
    return train_loader, val_loader, test_loader


def train_epoch(model, dataloader, optimizer, criterion, device):
    """Train for one epoch."""
    model.train()
    total_loss = 0
    
    for batch_X, _ in dataloader:
        batch_X = batch_X.to(device)
        
        optimizer.zero_grad()
        
        # Forward pass
        reconstruction, _ = model(batch_X)
        loss = criterion(reconstruction, batch_X)
        
        # Backward pass
        loss.backward()
        optimizer.step()
        
        total_loss += loss.item()
    
    return total_loss / len(dataloader)


def validate(model, dataloader, criterion, device):
    """Validate model."""
    model.eval()
    total_loss = 0
    
    with torch.no_grad():
        for batch_X, _ in dataloader:
            batch_X = batch_X.to(device)
            reconstruction, _ = model(batch_X)
            loss = criterion(reconstruction, batch_X)
            total_loss += loss.item()
    
    return total_loss / len(dataloader)


def evaluate_anomaly_detection(model, dataloader, device):
    """Evaluate anomaly detection performance."""
    model.eval()
    all_errors = []
    all_labels = []
    
    with torch.no_grad():
        for batch_X, batch_y in dataloader:
            batch_X = batch_X.to(device)
            
            # Calculate reconstruction error per sample
            errors = model.reconstruction_error(batch_X, reduction='none')
            
            all_errors.extend(errors.cpu().numpy())
            all_labels.extend(batch_y.numpy())
    
    all_errors = np.array(all_errors)
    all_labels = np.array(all_labels)
    
    # Calculate metrics
    metrics = AnomalyMetrics()
    results = metrics.calculate(all_labels, all_errors)
    
    return results


def main():
    parser = argparse.ArgumentParser(description="Train LSTM Autoencoder")
    parser.add_argument('--config', type=str, required=True, help='Path to config YAML')
    parser.add_argument('--data', type=str, required=True, help='Path to training data (.npz)')
    parser.add_argument('--output', type=str, required=True, help='Output model path')
    parser.add_argument('--device', type=str, default='cpu', help='Device (cpu/cuda)')
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    logger.info(f"Loaded config from {args.config}")
    
    # Load data
    X, y = load_data(args.data)
    
    # Create dataloaders
    train_loader, val_loader, test_loader = create_dataloaders(X, y, config)
    
    # Initialize model
    device = torch.device(args.device)
    model = LSTMAutoencoder(
        input_dim=config['model']['input_dim'],
        hidden_dims=config['model']['hidden_dims'],
        latent_dim=config['model']['latent_dim'],
        dropout=config['model']['dropout'],
        bidirectional=config['model']['bidirectional']
    ).to(device)
    
    logger.info(f"Initialized model on {device}")
    logger.info(f"Model parameters: {sum(p.numel() for p in model.parameters()):,}")
    
    # Training setup
    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=config['training']['learning_rate'],
        weight_decay=config['training'].get('weight_decay', 0)
    )
    
    # LR scheduler
    if config['training']['lr_scheduler']['enabled']:
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            optimizer,
            mode='min',
            factor=config['training']['lr_scheduler']['factor'],
            patience=config['training']['lr_scheduler']['patience'],
            min_lr=config['training']['lr_scheduler']['min_lr']
        )
    else:
        scheduler = None
    
    # Training loop
    best_val_loss = float('inf')
    patience_counter = 0
    patience = config['training']['early_stopping']['patience']
    
    history = {
        'train_loss': [],
        'val_loss': [],
        'learning_rate': []
    }
    
    logger.info("Starting training...")
    
    for epoch in range(config['training']['epochs']):
        # Train
        train_loss = train_epoch(model, train_loader, optimizer, criterion, device)
        
        # Validate
        val_loss = validate(model, val_loader, criterion, device)
        
        # Update LR scheduler
        if scheduler:
            scheduler.step(val_loss)
        
        # Record history
        history['train_loss'].append(train_loss)
        history['val_loss'].append(val_loss)
        history['learning_rate'].append(optimizer.param_groups[0]['lr'])
        
        # Logging
        logger.info(
            f"Epoch {epoch+1}/{config['training']['epochs']} | "
            f"Train Loss: {train_loss:.6f} | "
            f"Val Loss: {val_loss:.6f} | "
            f"LR: {optimizer.param_groups[0]['lr']:.6f}"
        )
        
        # Early stopping
        if val_loss < best_val_loss - config['training']['early_stopping']['min_delta']:
            best_val_loss = val_loss
            patience_counter = 0
            
            # Save best model
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            torch.save({
                'model_state_dict': model.state_dict(),
                'config': config,
                'input_dim': X.shape[2],
                'window_length': X.shape[1],
                'epoch': epoch,
                'val_loss': val_loss,
                'history': history
            }, output_path)
            
            logger.info(f"✅ Saved best model to {output_path}")
        else:
            patience_counter += 1
            
            if patience_counter >= patience:
                logger.info(f"Early stopping triggered after {epoch+1} epochs")
                break
    
    # Final evaluation on test set
    logger.info("\n" + "="*80)
    logger.info("Final Evaluation on Test Set")
    logger.info("="*80)
    
    test_metrics = evaluate_anomaly_detection(model, test_loader, device)
    
    logger.info(f"Test AUROC: {test_metrics['auroc']:.4f}")
    logger.info(f"Test Precision@10%: {test_metrics.get('precision_at_10', 'N/A')}")
    
    # Save metrics
    metrics_path = output_path.parent / f"{output_path.stem}_metrics.json"
    with open(metrics_path, 'w') as f:
        json.dump({
            'test_metrics': test_metrics,
            'best_val_loss': float(best_val_loss),
            'final_epoch': epoch + 1,
            'timestamp': datetime.now().isoformat()
        }, f, indent=2)
    
    logger.info(f"✅ Saved metrics to {metrics_path}")
    logger.info("\n🎉 Training complete!")


if __name__ == "__main__":
    main()
