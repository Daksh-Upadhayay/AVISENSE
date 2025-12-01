"""
Evaluation Script: VAE vs LSTM Comparison

Compares the performance of VAE and LSTM autoencoders on the test dataset.
Metrics: AUROC, Precision, Recall, F1, Detection Latency
"""

import sys
import os
import numpy as np
import torch
import yaml
from pathlib import Path
from sklearn.metrics import roc_auc_score, precision_recall_fscore_support, roc_curve
import matplotlib.pyplot as plt

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.ml.models.autoencoder import LSTMAutoencoder
from app.ml.models.vae import VAE
from app.data import TimeSeriesScaler

def load_test_data():
    """Load test dataset."""
    print("Loading test data...")
    data = np.load('data/processed/test.npz')
    X_test = data['X']
    y_test = data['y']
    print(f"Test data shape: {X_test.shape}, Labels: {y_test.shape}")
    return X_test, y_test

def load_lstm_model():
    """Load LSTM Autoencoder."""
    print("\nLoading LSTM model...")
    config_path = Path("configs/model_configs/lstm_autoencoder_config.yaml")
    model_path = Path("models/deep/lstm_ae_v1.pt")
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    model = LSTMAutoencoder(
        input_dim=config['model']['input_dim'],
        hidden_dims=config['model']['hidden_dims'],
        latent_dim=config['model']['latent_dim'],
        bidirectional=config['model']['bidirectional']
    )
    
    checkpoint = torch.load(model_path, map_location='cpu')
    model.load_state_dict(checkpoint['model_state_dict'])
    model.eval()
    
    print("✅ LSTM loaded")
    return model

def load_vae_model():
    """Load VAE model."""
    print("\nLoading VAE model...")
    config_path = Path("configs/model_configs/vae_config.yaml")
    model_path = Path("app/ml/models/saved/vae/vae_v1.pt")
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    model = VAE(
        input_dim=config['architecture']['input_dim'],
        hidden_dim1=config['architecture']['hidden_dim1'],
        hidden_dim2=config['architecture']['hidden_dim2'],
        latent_dim=config['architecture']['latent_dim'],
        sequence_length=config['architecture']['sequence_length']
    )
    
    checkpoint = torch.load(model_path, map_location='cpu')
    model.load_state_dict(checkpoint['model_state_dict'])
    model.eval()
    
    print("✅ VAE loaded")
    return model

def evaluate_lstm(model, X_test, y_test):
    """Evaluate LSTM on test data."""
    print("\nEvaluating LSTM...")
    X_tensor = torch.FloatTensor(X_test)
    
    anomaly_scores = []
    with torch.no_grad():
        for i in range(len(X_test)):
            x = X_tensor[i:i+1]
            x_recon, _ = model(x)  # LSTM returns (reconstruction, latent)
            mse = torch.mean((x - x_recon) ** 2).item()
            anomaly_scores.append(mse)
    
    return np.array(anomaly_scores)

def evaluate_vae(model, X_test, y_test):
    """Evaluate VAE on test data."""
    print("\nEvaluating VAE...")
    X_tensor = torch.FloatTensor(X_test)
    
    anomaly_scores = []
    with torch.no_grad():
        for i in range(len(X_test)):
            x = X_tensor[i:i+1]
            x_recon, mu, logvar = model(x)
            
            # ELBO-based score
            recon_loss = torch.mean((x - x_recon) ** 2).item()
            kld_loss = -0.5 * torch.mean(1 + logvar - mu.pow(2) - logvar.exp()).item()
            
            # Combined score (same beta as training)
            beta = 0.1
            score = recon_loss + beta * kld_loss
            anomaly_scores.append(score)
    
    return np.array(anomaly_scores)

def calculate_metrics(scores, labels, model_name):
    """Calculate and print metrics."""
    print(f"\n{'='*50}")
    print(f"{model_name} Performance Metrics")
    print(f"{'='*50}")
    
    # AUROC
    auroc = roc_auc_score(labels, scores)
    print(f"AUROC: {auroc:.4f}")
    
    # Find optimal threshold using ROC curve
    fpr, tpr, thresholds = roc_curve(labels, scores)
    optimal_idx = np.argmax(tpr - fpr)
    optimal_threshold = thresholds[optimal_idx]
    
    # Predictions at optimal threshold
    predictions = (scores > optimal_threshold).astype(int)
    
    # Precision, Recall, F1
    precision, recall, f1, _ = precision_recall_fscore_support(
        labels, predictions, average='binary', zero_division=0
    )
    
    print(f"Optimal Threshold: {optimal_threshold:.4f}")
    print(f"Precision: {precision:.4f}")
    print(f"Recall: {recall:.4f}")
    print(f"F1 Score: {f1:.4f}")
    
    # Additional stats
    print(f"\nScore Statistics:")
    print(f"  Mean: {np.mean(scores):.4f}")
    print(f"  Std: {np.std(scores):.4f}")
    print(f"  Min: {np.min(scores):.4f}")
    print(f"  Max: {np.max(scores):.4f}")
    
    return {
        'auroc': auroc,
        'precision': precision,
        'recall': recall,
        'f1': f1,
        'threshold': optimal_threshold,
        'scores': scores
    }

def plot_comparison(lstm_results, vae_results, y_test):
    """Plot ROC curves and score distributions."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    # ROC Curves
    ax1 = axes[0]
    for results, name, color in [
        (lstm_results, 'LSTM', 'blue'),
        (vae_results, 'VAE', 'red')
    ]:
        fpr, tpr, _ = roc_curve(y_test, results['scores'])
        ax1.plot(fpr, tpr, label=f"{name} (AUC={results['auroc']:.3f})", color=color, linewidth=2)
    
    ax1.plot([0, 1], [0, 1], 'k--', label='Random', linewidth=1)
    ax1.set_xlabel('False Positive Rate')
    ax1.set_ylabel('True Positive Rate')
    ax1.set_title('ROC Curve Comparison')
    ax1.legend()
    ax1.grid(alpha=0.3)
    
    # Score Distributions
    ax2 = axes[1]
    ax2.hist(lstm_results['scores'][y_test == 0], bins=50, alpha=0.5, label='LSTM (Healthy)', color='blue')
    ax2.hist(lstm_results['scores'][y_test == 1], bins=50, alpha=0.5, label='LSTM (Failure)', color='darkblue')
    ax2.hist(vae_results['scores'][y_test == 0], bins=50, alpha=0.5, label='VAE (Healthy)', color='red')
    ax2.hist(vae_results['scores'][y_test == 1], bins=50, alpha=0.5, label='VAE (Failure)', color='darkred')
    ax2.set_xlabel('Anomaly Score')
    ax2.set_ylabel('Frequency')
    ax2.set_title('Score Distribution')
    ax2.legend()
    ax2.grid(alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('evaluation_comparison.png', dpi=150)
    print(f"\n✅ Plot saved to evaluation_comparison.png")

def main():
    # Load data
    X_test, y_test = load_test_data()
    
    # Load models
    lstm_model = load_lstm_model()
    vae_model = load_vae_model()
    
    # Evaluate
    lstm_scores = evaluate_lstm(lstm_model, X_test, y_test)
    vae_scores = evaluate_vae(vae_model, X_test, y_test)
    
    # Calculate metrics
    lstm_results = calculate_metrics(lstm_scores, y_test, "LSTM Autoencoder")
    vae_results = calculate_metrics(vae_scores, y_test, "VAE")
    
    # Comparison
    print(f"\n{'='*50}")
    print("WINNER DETERMINATION")
    print(f"{'='*50}")
    
    if lstm_results['auroc'] > vae_results['auroc']:
        winner = "LSTM"
        margin = lstm_results['auroc'] - vae_results['auroc']
    else:
        winner = "VAE"
        margin = vae_results['auroc'] - lstm_results['auroc']
    
    print(f"🏆 Winner: {winner}")
    print(f"   Margin: {margin:.4f} AUROC")
    
    # Plot
    plot_comparison(lstm_results, vae_results, y_test)

if __name__ == "__main__":
    main()
