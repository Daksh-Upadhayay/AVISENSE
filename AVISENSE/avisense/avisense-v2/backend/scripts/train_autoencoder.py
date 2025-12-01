#!/usr/bin/env python3
"""
Train Dense Autoencoder for Anomaly Detection

This script trains a Dense Autoencoder on telemetry data for unsupervised
anomaly detection.

Usage:
    python scripts/train_autoencoder.py \
        --data-dir data/processed \
        --output-dir models/deep \
        --config configs/model_configs/autoencoder_config.yaml
"""

import argparse
import sys
from pathlib import Path
import yaml
import json
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.ml.models import DenseAutoencoder
from app.ml.training import ModelTrainer, create_data_loaders
from app.ml.evaluation import AnomalyMetrics, print_metrics_report
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_config(config_path: str) -> dict:
    """Load configuration from YAML file."""
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config


def load_data(data_dir: str):
    """Load preprocessed training data."""
    data_dir = Path(data_dir)
    
    # Load train/val/test splits
    train_data = np.load(data_dir / 'train.npz')
    val_data = np.load(data_dir / 'val.npz')
    test_data = np.load(data_dir / 'test.npz')
    
    X_train = train_data['X']
    y_train = train_data['y']
    
    X_val = val_data['X']
    y_val = val_data['y']
    
    X_test = test_data['X']
    y_test = test_data['y']
    
    logger.info(f"Loaded data:")
    logger.info(f"  Train: {X_train.shape}, labels: {y_train.shape}")
    logger.info(f"  Val:   {X_val.shape}, labels: {y_val.shape}")
    logger.info(f"  Test:  {X_test.shape}, labels: {y_test.shape}")
    
    # Flatten if 3D (sequences) for Dense AE
    if X_train.ndim == 3:
        logger.info("Flattening sequences for Dense AE")
        n_train, window_length, n_features = X_train.shape
        X_train = X_train.reshape(n_train, window_length * n_features)
        
        n_val, _, _ = X_val.shape
        X_val = X_val.reshape(n_val, window_length * n_features)
        
        n_test, _, _ = X_test.shape
        X_test = X_test.reshape(n_test, window_length * n_features)
        
        logger.info(f"  Flattened shapes: {X_train.shape}")
    
    return (X_train, y_train), (X_val, y_val), (X_test, y_test)


def evaluate_model(model, X, y, device='cpu'):
    """Evaluate autoencoder on anomaly detection."""
    model.eval()
    
    with torch.no_grad():
        X_tensor = torch.FloatTensor(X).to(device)
        
        # Get reconstruction errors
        errors = model.reconstruction_error(X_tensor, reduction='none')
        anomaly_scores = errors.cpu().numpy()
    
    # Calculate metrics
    metrics = AnomalyMetrics.calculate(y, anomaly_scores)
    
    # Find optimal threshold
    threshold, f1 = AnomalyMetrics.find_optimal_threshold(y, anomaly_scores, metric='f1')
    metrics['optimal_threshold'] = threshold
    metrics['f1_at_optimal'] = f1
    
    return metrics, anomaly_scores


def main():
    parser = argparse.ArgumentParser(description='Train Dense Autoencoder')
    
    # Paths
    parser.add_argument('--data-dir', type=str, default='data/processed',
                        help='Directory with processed data')
    parser.add_argument('--output-dir', type=str, default='models/deep',
                        help='Output directory for model')
    parser.add_argument('--config', type=str,
                        default='configs/model_configs/autoencoder_config.yaml',
                        help='Config file path')
    
    # Training overrides
    parser.add_argument('--epochs', type=int, default=None,
                        help='Number of epochs (overrides config)')
    parser.add_argument('--batch-size', type=int, default=None,
                        help='Batch size (overrides config)')
    parser.add_argument('--device', type=str, default='cpu',
                        choices=['cpu', 'cuda'], help='Device to use')
    
    args = parser.parse_args()
    
    # Load config
    config = load_config(args.config)
    logger.info(f"Loaded config from {args.config}")
    
    # Override config with CLI args
    if args.epochs:
        config['training']['epochs'] = args.epochs
    if args.batch_size:
        config['training']['batch_size'] = args.batch_size
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load data
    (X_train, y_train), (X_val, y_val), (X_test, y_test) = load_data(args.data_dir)
    
    input_dim = X_train.shape[1]
    logger.info(f"Input dimension: {input_dim}")
    
    # Create model
    model = DenseAutoencoder(
        input_dim=input_dim,
        encoder_dims=config['model']['encoder_dims'],
        latent_dim=config['model']['latent_dim'],
        activation=config['model']['activation'],
        dropout=config['model']['dropout']
    )
    
    logger.info(f"Created model with {sum(p.numel() for p in model.parameters())} parameters")
    
    # Create optimizer
    optimizer = optim.Adam(
        model.parameters(),
        lr=config['training']['learning_rate'],
        weight_decay=config['training']['weight_decay']
    )
    
    # Create scheduler
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(
        optimizer,
        mode='min',
        factor=config['training']['lr_scheduler']['factor'],
        patience=config['training']['lr_scheduler']['patience'],
        min_lr=config['training']['lr_scheduler']['min_lr']
    )
    
    # Loss function
    criterion = nn.MSELoss()
    
    # Create data loaders
    train_loader, val_loader = create_data_loaders(
        X_train, X_val,
        batch_size=config['training']['batch_size'],
        shuffle=True
    )
    
    # Create trainer
    trainer = ModelTrainer(
        model=model,
        optimizer=optimizer,
        criterion=criterion,
        device=args.device,
        scheduler=scheduler
    )
    
    # Train
    logger.info("Starting training...")
    history = trainer.fit(
        train_loader=train_loader,
        val_loader=val_loader,
        epochs=config['training']['epochs'],
        early_stopping_patience=config['training']['early_stopping_patience'],
        checkpoint_dir=str(output_dir),
        save_best_only=True
    )
    
    # Load best model
    best_model_path = output_dir / 'best_model.pt'
    if best_model_path.exists():
        checkpoint = torch.load(best_model_path, map_location=args.device)
        model.load_state_dict(checkpoint['model_state_dict'])
        logger.info(f"Loaded best model from epoch {checkpoint['epoch']}")
    
    # Evaluate on test set
    logger.info("\nEvaluating on test set...")
    test_metrics, test_scores = evaluate_model(model, X_test, y_test, args.device)
    
    print_metrics_report(test_metrics, "Test Set Metrics")
    
    # Save final model
    model_save_path = output_dir / 'dense_ae_v1.pt'
    torch.save({
        'model_state_dict': model.state_dict(),
        'config': config,
        'input_dim': input_dim,
        'test_metrics': test_metrics,
        'history': history
    }, model_save_path)
    
    logger.info(f"✅ Saved final model to {model_save_path}")
    
    # Save metrics report
    metrics_path = output_dir / 'metrics.json'
    with open(metrics_path, 'w') as f:
        json.dump({
            'test_metrics': {k: float(v) if isinstance(v, (int, float, np.number)) else v 
                           for k, v in test_metrics.items()},
            'final_train_loss': float(history['train_loss'][-1]),
            'final_val_loss': float(history['val_loss'][-1]),
            'epochs_trained': len(history['train_loss'])
        }, f, indent=2)
    
    logger.info(f"✅ Saved metrics to {metrics_path}")
    
    # Save training history
    history_path = output_dir / 'training_history.npz'
    np.savez(
        history_path,
        train_loss=np.array(history['train_loss']),
        val_loss=np.array(history['val_loss']),
        lr=np.array(history['lr'])
    )
    
    logger.info(f"✅ Saved training history to {history_path}")
    
    print("\n" + "="*60)
    print("Training Complete!")
    print(f"Model saved to: {model_save_path}")
    print(f"Test AUROC: {test_metrics['auroc']:.4f}")
    print(f"Test Precision@5%: {test_metrics['precision_at_5pct']:.4f}")
    print("="*60)


if __name__ == '__main__':
    main()
