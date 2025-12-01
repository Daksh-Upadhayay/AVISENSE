"""
Model Trainer with PyTorch

Unified training loop for deep learning models with early stopping,
checkpointing, and progress tracking.
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
import numpy as np
from pathlib import Path
from typing import Dict, Optional, Callable, Tuple
import logging
import json
from tqdm import tqdm

logger = logging.getLogger(__name__)


class EarlyStopping:
    """Early stopping to prevent overfitting."""
    
    def __init__(self, patience: int = 10, min_delta: float = 0.0, mode: str = 'min'):
        """
        Initialize early stopping.
        
        Args:
            patience: Number of epochs to wait before stopping
            min_delta: Minimum change to qualify as improvement
            mode: 'min' or 'max' for metric
        """
        self.patience = patience
        self.min_delta = min_delta
        self.mode = mode
        self.counter = 0
        self.best_score = None
        self.early_stop = False
        
    def __call__(self, score: float) -> bool:
        """
        Check if should stop.
        
        Args:
            score: Current metric value
            
        Returns:
            True if should stop
        """
        if self.best_score is None:
            self.best_score = score
            return False
        
        if self.mode == 'min':
            improved = score < (self.best_score - self.min_delta)
        else:
            improved = score > (self.best_score + self.min_delta)
        
        if improved:
            self.best_score = score
            self.counter = 0
        else:
            self.counter += 1
            if self.counter >= self.patience:
                self.early_stop = True
                logger.info(f"Early stopping triggered after {self.counter} epochs without improvement")
                return True
        
        return False


class ModelTrainer:
    """
    Unified trainer for PyTorch models.
    
    Supports:
    - Training loop with validation
    - Early stopping
    - Model checkpointing
    - Learning rate scheduling
    - Progress tracking
    """
    
    def __init__(
        self,
        model: nn.Module,
        optimizer: optim.Optimizer,
        criterion: nn.Module,
        device: str = 'cpu',
        scheduler: Optional[any] = None
    ):
        """
        Initialize trainer.
        
        Args:
            model: PyTorch model
            optimizer: Optimizer
            criterion: Loss function
            device: 'cpu' or 'cuda'
            scheduler: Optional LR scheduler
        """
        self.model = model.to(device)
        self.optimizer = optimizer
        self.criterion = criterion
        self.device = device
        self.scheduler = scheduler
        
        self.history = {
            'train_loss': [],
            'val_loss': [],
            'lr': []
        }
    
    def train_epoch(
        self,
        train_loader: DataLoader,
        epoch: int
    ) -> float:
        """
        Train for one epoch.
        
        Args:
            train_loader: Training data loader
            epoch: Current epoch number
            
        Returns:
            Average training loss
        """
        self.model.train()
        total_loss = 0
        n_batches = 0
        
        pbar = tqdm(train_loader, desc=f"Epoch {epoch} [Train]", leave=False)
        
        for batch_data in pbar:
            # Handle different data formats
            if isinstance(batch_data, (list, tuple)):
                X = batch_data[0].to(self.device)
            else:
                X = batch_data.to(self.device)
            
            # Forward pass
            self.optimizer.zero_grad()
            
            # Model-specific forward (autoencoder returns reconstruction + latent)
            output = self.model(X)
            if isinstance(output, tuple):
                reconstruction = output[0]
                loss = self.criterion(reconstruction, X)
            else:
                loss = self.criterion(output, X)
            
            # Backward pass
            loss.backward()
            self.optimizer.step()
            
            total_loss += loss.item()
            n_batches += 1
            
            pbar.set_postfix({'loss': f'{loss.item():.4f}'})
        
        avg_loss = total_loss / n_batches
        return avg_loss
    
    def validate(
        self,
        val_loader: DataLoader,
        epoch: int
    ) -> float:
        """
        Validate model.
        
        Args:
            val_loader: Validation data loader
            epoch: Current epoch number
            
        Returns:
            Average validation loss
        """
        self.model.eval()
        total_loss = 0
        n_batches = 0
        
        with torch.no_grad():
            pbar = tqdm(val_loader, desc=f"Epoch {epoch} [Val]", leave=False)
            
            for batch_data in pbar:
                if isinstance(batch_data, (list, tuple)):
                    X = batch_data[0].to(self.device)
                else:
                    X = batch_data.to(self.device)
                
                output = self.model(X)
                if isinstance(output, tuple):
                    reconstruction = output[0]
                    loss = self.criterion(reconstruction, X)
                else:
                    loss = self.criterion(output, X)
                
                total_loss += loss.item()
                n_batches += 1
                
                pbar.set_postfix({'loss': f'{loss.item():.4f}'})
        
        avg_loss = total_loss / n_batches
        return avg_loss
    
    def fit(
        self,
        train_loader: DataLoader,
        val_loader: DataLoader,
        epochs: int,
        early_stopping_patience: int = 10,
        checkpoint_dir: Optional[str] = None,
        save_best_only: bool = True
    ) -> Dict[str, list]:
        """
        Train model.
        
        Args:
            train_loader: Training data loader
            val_loader: Validation data loader
            epochs: Number of epochs
            early_stopping_patience: Patience for early stopping
            checkpoint_dir: Directory to save checkpoints
            save_best_only: Only save best model
            
        Returns:
            Training history
        """
        early_stopping = EarlyStopping(patience=early_stopping_patience, mode='min')
        best_val_loss = float('inf')
        
        if checkpoint_dir:
            checkpoint_path = Path(checkpoint_dir)
            checkpoint_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Starting training for {epochs} epochs")
        
        for epoch in range(1, epochs + 1):
            # Train
            train_loss = self.train_epoch(train_loader, epoch)
            
            # Validate
            val_loss = self.validate(val_loader, epoch)
            
            # Update history
            self.history['train_loss'].append(train_loss)
            self.history['val_loss'].append(val_loss)
            
            # Learning rate
            current_lr = self.optimizer.param_groups[0]['lr']
            self.history['lr'].append(current_lr)
            
            # Scheduler step
            if self.scheduler:
                if isinstance(self.scheduler, optim.lr_scheduler.ReduceLROnPlateau):
                    self.scheduler.step(val_loss)
                else:
                    self.scheduler.step()
            
            # Logging
            logger.info(
                f"Epoch {epoch}/{epochs} - "
                f"train_loss: {train_loss:.4f}, "
                f"val_loss: {val_loss:.4f}, "
                f"lr: {current_lr:.6f}"
            )
            
            # Save checkpoint
            if checkpoint_dir:
                if save_best_only:
                    if val_loss < best_val_loss:
                        best_val_loss = val_loss
                        self.save_checkpoint(
                            checkpoint_path / 'best_model.pt',
                            epoch,
                            val_loss
                        )
                        logger.info(f"✓ Saved best model (val_loss: {val_loss:.4f})")
                else:
                    self.save_checkpoint(
                        checkpoint_path / f'checkpoint_epoch_{epoch}.pt',
                        epoch,
                        val_loss
                    )
            
            # Early stopping
            if early_stopping(val_loss):
                logger.info(f"Early stopping at epoch {epoch}")
                break
        
        logger.info("Training complete!")
        return self.history
    
    def save_checkpoint(
        self,
        filepath: Path,
        epoch: int,
        val_loss: float
    ):
        """Save model checkpoint."""
        torch.save({
            'epoch': epoch,
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'val_loss': val_loss,
            'history': self.history
        }, filepath)
    
    def load_checkpoint(self, filepath: Path):
        """Load model checkpoint."""
        checkpoint = torch.load(filepath, map_location=self.device)
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        self.history = checkpoint.get('history', self.history)
        logger.info(f"Loaded checkpoint from {filepath}")
        return checkpoint['epoch'], checkpoint['val_loss']


def create_data_loaders(
    X_train: np.ndarray,
    X_val: np.ndarray,
    y_train: Optional[np.ndarray] = None,
    y_val: Optional[np.ndarray] = None,
    batch_size: int = 64,
    shuffle: bool = True
) -> Tuple[DataLoader, DataLoader]:
    """
    Create PyTorch data loaders.
    
    Args:
        X_train: Training features
        X_val: Validation features
        y_train: Training labels (optional for autoencoders)
        y_val: Validation labels (optional)
        batch_size: Batch size
        shuffle: Shuffle training data
        
    Returns:
        Tuple of (train_loader, val_loader)
    """
    # Convert to tensors
    X_train_tensor = torch.FloatTensor(X_train)
    X_val_tensor = torch.FloatTensor(X_val)
    
    if y_train is not None:
        y_train_tensor = torch.FloatTensor(y_train)
        y_val_tensor = torch.FloatTensor(y_val)
        
        train_dataset = TensorDataset(X_train_tensor, y_train_tensor)
        val_dataset = TensorDataset(X_val_tensor, y_val_tensor)
    else:
        # For autoencoders (unsupervised)
        train_dataset = TensorDataset(X_train_tensor)
        val_dataset = TensorDataset(X_val_tensor)
    
    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=shuffle,
        num_workers=0  # Set to 0 for compatibility
    )
    
    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=0
    )
    
    return train_loader, val_loader
