import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
import numpy as np
import yaml
import argparse
from pathlib import Path
import logging
import joblib
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.ml.models.rul_regressor import RULRegressor

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_data(data_path):
    """Load processed sequence data."""
    logger.info(f"Loading data from {data_path}")
    data = np.load(data_path)
    
    # X: (n_samples, window_length, n_features)
    # y: (n_samples,) - RUL values
    
    # Check available keys
    logger.info(f"Available keys in data: {list(data.keys())}")
    
    if 'X_train' in data:
        X_train = data['X_train']
    elif 'X' in data:
        X_train = data['X']
    else:
        raise ValueError("X data not found in file")
        
    # Check for target
    if 'y_train' in data:
        y_train = data['y_train']
    elif 'y_train_rul' in data:
        y_train = data['y_train_rul']
    elif 'rul_train' in data:
        y_train = data['rul_train']
    elif 'y' in data:
        y_train = data['y']
    else:
        raise ValueError("RUL targets (y) not found in data file")
        
    return X_train, y_train

def train(config_path, data_path, output_dir):
    # Load config
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
        
    # Set device
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    logger.info(f"Using device: {device}")
    
    # Load data
    X_train, y_train = load_data(data_path)
    
    # Convert to tensors
    X_tensor = torch.FloatTensor(X_train)
    y_tensor = torch.FloatTensor(y_train).unsqueeze(1) # (N, 1)
    
    # Create dataloader
    dataset = TensorDataset(X_tensor, y_tensor)
    dataloader = DataLoader(
        dataset, 
        batch_size=config['training']['batch_size'], 
        shuffle=True
    )
    
    # Initialize model
    model = RULRegressor(
        input_dim=X_train.shape[2],
        hidden_dim=config['model']['hidden_dim'],
        num_layers=config['model']['num_layers'],
        dropout=config['model']['dropout']
    ).to(device)
    
    # Loss and optimizer
    criterion = nn.MSELoss()
    optimizer = optim.Adam(
        model.parameters(), 
        lr=config['training']['learning_rate']
    )
    
    # Training loop
    epochs = config['training']['epochs']
    logger.info(f"Starting training for {epochs} epochs")
    
    for epoch in range(epochs):
        model.train()
        total_loss = 0
        
        for batch_X, batch_y in dataloader:
            batch_X, batch_y = batch_X.to(device), batch_y.to(device)
            
            # Forward pass
            outputs = model(batch_X)
            loss = criterion(outputs, batch_y)
            
            # Backward pass
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item()
            
        avg_loss = total_loss / len(dataloader)
        rmse = np.sqrt(avg_loss)
        
        if (epoch + 1) % 5 == 0:
            logger.info(f"Epoch [{epoch+1}/{epochs}], Loss: {avg_loss:.4f}, RMSE: {rmse:.4f}")
            
    # Save model
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    model_save_path = output_path / "rul_lstm_v1.pt"
    torch.save(model.state_dict(), model_save_path)
    logger.info(f"Model saved to {model_save_path}")
    
    # Save scaler if needed (assuming it's already saved during preprocessing)
    # But we might want to save a separate scaler for RUL if we scaled it
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, default="configs/model_configs/rul_regressor_config.yaml")
    parser.add_argument("--data", type=str, default="data/processed/train.npz")
    parser.add_argument("--output", type=str, default="models/deep")
    args = parser.parse_args()
    
    train(args.config, args.data, args.output)
