import sys
import os
import yaml
import torch
import numpy as np
from torch.utils.data import DataLoader, TensorDataset
import torch.optim as optim

# Add parent directory to path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.ml.models.vae import VAE

def load_config(config_path):
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def train_vae():
    # Load config
    config = load_config('configs/model_configs/vae_config.yaml')
    
    # Set device
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")
    
    # Load data
    print("Loading data...")
    train_data = np.load(config['paths']['train_data'])
    val_path = config['paths']['train_data'].replace('train.npz', 'val.npz')
    val_data = np.load(val_path)
    
    X_train = torch.FloatTensor(train_data['X']).to(device)
    X_val = torch.FloatTensor(val_data['X']).to(device)
    
    print(f"Training data shape: {X_train.shape}")
    print(f"Validation data shape: {X_val.shape}")
    
    # Create dataloaders
    train_dataset = TensorDataset(X_train)
    val_dataset = TensorDataset(X_val)
    
    train_loader = DataLoader(train_dataset, batch_size=config['training']['batch_size'], shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=config['training']['batch_size'], shuffle=False)
    
    # Initialize model
    model = VAE(
        input_dim=config['architecture']['input_dim'],
        hidden_dim1=config['architecture']['hidden_dim1'],
        hidden_dim2=config['architecture']['hidden_dim2'],
        latent_dim=config['architecture']['latent_dim'],
        sequence_length=config['architecture']['sequence_length']
    ).to(device)
    
    optimizer = optim.Adam(model.parameters(), lr=config['training']['learning_rate'])
    
    # Training loop
    best_val_loss = float('inf')
    patience_counter = 0
    
    print("Starting training...")
    for epoch in range(config['training']['epochs']):
        model.train()
        train_loss = 0
        train_recon_loss = 0
        train_kld_loss = 0
        
        for batch in train_loader:
            x = batch[0]
            optimizer.zero_grad()
            
            x_recon, mu, logvar = model(x)
            loss, recon, kld = model.loss_function(x, x_recon, mu, logvar, beta=config['training']['beta'])
            
            loss.backward()
            optimizer.step()
            
            train_loss += loss.item()
            train_recon_loss += recon.item()
            train_kld_loss += kld.item()
            
        avg_train_loss = train_loss / len(train_loader.dataset)
        
        # Validation
        model.eval()
        val_loss = 0
        with torch.no_grad():
            for batch in val_loader:
                x = batch[0]
                x_recon, mu, logvar = model(x)
                loss, _, _ = model.loss_function(x, x_recon, mu, logvar, beta=config['training']['beta'])
                val_loss += loss.item()
                
        avg_val_loss = val_loss / len(val_loader.dataset)
        
        print(f"Epoch {epoch+1}/{config['training']['epochs']} | "
              f"Train Loss: {avg_train_loss:.4f} (Recon: {train_recon_loss/len(train_loader.dataset):.4f}, KLD: {train_kld_loss/len(train_loader.dataset):.4f}) | "
              f"Val Loss: {avg_val_loss:.4f}")
        
        # Early stopping and saving
        if avg_val_loss < best_val_loss:
            best_val_loss = avg_val_loss
            patience_counter = 0
            
            # Save model
            save_dir = config['paths']['save_dir']
            os.makedirs(save_dir, exist_ok=True)
            save_path = os.path.join(save_dir, f"{config['model']['name']}.pt")
            
            torch.save({
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'loss': best_val_loss,
                'config': config
            }, save_path)
            print(f"Model saved to {save_path}")
        else:
            patience_counter += 1
            if patience_counter >= config['training']['early_stopping_patience']:
                print("Early stopping triggered")
                break

if __name__ == "__main__":
    train_vae()
