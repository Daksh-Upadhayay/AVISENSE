"""
Autoencoder Models for Anomaly Detection

Implements Dense, LSTM, and Variational Autoencoders for unsupervised
anomaly detection in engine telemetry data.
"""

import torch
import torch.nn as nn
import numpy as np
from typing import Tuple, Optional, List
import logging

logger = logging.getLogger(__name__)


class DenseAutoencoder(nn.Module):
    """
    Dense (fully-connected) Autoencoder for tabular data.
    
    Architecture: Input -> Encoder -> Latent -> Decoder -> Reconstruction
    """
    
    def __init__(
        self,
        input_dim: int,
        encoder_dims: List[int] = [128, 64, 32],
        latent_dim: int = 16,
        activation: str = 'relu',
        dropout: float = 0.2
    ):
        """
        Initialize Dense Autoencoder.
        
        Args:
            input_dim: Number of input features
            encoder_dims: Hidden layer dimensions for encoder
            latent_dim: Latent space dimension
            activation: Activation function ('relu', 'tanh', 'elu')
            dropout: Dropout probability
        """
        super(DenseAutoencoder, self).__init__()
        
        self.input_dim = input_dim
        self.latent_dim = latent_dim
        
        # Activation function
        if activation == 'relu':
            self.activation = nn.ReLU()
        elif activation == 'tanh':
            self.activation = nn.Tanh()
        elif activation == 'elu':
            self.activation = nn.ELU()
        else:
            raise ValueError(f"Unknown activation: {activation}")
        
        # Build encoder
        encoder_layers = []
        prev_dim = input_dim
        
        for dim in encoder_dims:
            encoder_layers.extend([
                nn.Linear(prev_dim, dim),
                self.activation,
                nn.Dropout(dropout)
            ])
            prev_dim = dim
        
        # Latent layer
        encoder_layers.append(nn.Linear(prev_dim, latent_dim))
        
        self.encoder = nn.Sequential(*encoder_layers)
        
        # Build decoder (mirror of encoder)
        decoder_layers = []
        decoder_dims = encoder_dims[::-1]  # Reverse
        prev_dim = latent_dim
        
        for dim in decoder_dims:
            decoder_layers.extend([
                nn.Linear(prev_dim, dim),
                self.activation,
                nn.Dropout(dropout)
            ])
            prev_dim = dim
        
        # Output layer
        decoder_layers.append(nn.Linear(prev_dim, input_dim))
        
        self.decoder = nn.Sequential(*decoder_layers)
        
        logger.info(f"Created DenseAutoencoder: input_dim={input_dim}, latent_dim={latent_dim}")
    
    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Forward pass.
        
        Args:
            x: Input tensor (batch_size, input_dim)
            
        Returns:
            Tuple of (reconstruction, latent_representation)
        """
        latent = self.encoder(x)
        reconstruction = self.decoder(latent)
        return reconstruction, latent
    
    def encode(self, x: torch.Tensor) -> torch.Tensor:
        """Encode input to latent space."""
        return self.encoder(x)
    
    def decode(self, z: torch.Tensor) -> torch.Tensor:
        """Decode latent representation to reconstruction."""
        return self.decoder(z)
    
    def reconstruction_error(
        self,
        x: torch.Tensor,
        reduction: str = 'mean'
    ) -> torch.Tensor:
        """
        Calculate reconstruction error (MSE).
        
        Args:
            x: Input tensor
            reduction: 'mean', 'sum', or 'none'
            
        Returns:
            Reconstruction error
        """
        reconstruction, _ = self.forward(x)
        
        if reduction == 'none':
            # Per-sample error
            return torch.mean((x - reconstruction) ** 2, dim=1)
        elif reduction == 'mean':
            return torch.mean((x - reconstruction) ** 2)
        elif reduction == 'sum':
            return torch.sum((x - reconstruction) ** 2)
        else:
            raise ValueError(f"Unknown reduction: {reduction}")
    
    def per_feature_error(self, x: torch.Tensor) -> torch.Tensor:
        """
        Calculate per-feature reconstruction error.
        
        Args:
            x: Input tensor (batch_size, input_dim)
            
        Returns:
            Per-feature error (batch_size, input_dim)
        """
        reconstruction, _ = self.forward(x)
        return (x - reconstruction) ** 2


class LSTMAutoencoder(nn.Module):
    """
    LSTM-based Autoencoder for sequence data.
    
    Encodes sequences to latent representation and reconstructs them.
    """
    
    def __init__(
        self,
        input_dim: int,
        hidden_dims: List[int] = [128, 64],
        latent_dim: int = 32,
        dropout: float = 0.3,
        bidirectional: bool = False
    ):
        """
        Initialize LSTM Autoencoder.
        
        Args:
            input_dim: Number of features per time step
            hidden_dims: LSTM hidden dimensions (stacked)
            latent_dim: Latent space dimension
            dropout: Dropout probability
            bidirectional: Use bidirectional LSTM
        """
        super(LSTMAutoencoder, self).__init__()
        
        self.input_dim = input_dim
        self.hidden_dims = hidden_dims
        self.latent_dim = latent_dim
        self.bidirectional = bidirectional
        self.num_directions = 2 if bidirectional else 1
        
        # Encoder LSTM
        # Note: When using num_layers > 1, all layers use hidden_dims[0]
        self.encoder_lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dims[0],
            num_layers=len(hidden_dims),
            batch_first=True,
            dropout=dropout if len(hidden_dims) > 1 else 0,
            bidirectional=bidirectional
        )
        
        # Latent projection
        # The output of the last LSTM layer is hidden_dims[0] * num_directions
        encoder_output_dim = hidden_dims[0] * self.num_directions
        self.latent_projection = nn.Linear(encoder_output_dim, latent_dim)
        
        # Decoder LSTM
        self.decoder_lstm = nn.LSTM(
            input_size=latent_dim,
            hidden_size=hidden_dims[0],
            num_layers=len(hidden_dims),
            batch_first=True,
            dropout=dropout if len(hidden_dims) > 1 else 0
        )
        
        # Output projection
        self.output_projection = nn.Linear(hidden_dims[0], input_dim)
        
        logger.info(f"Created LSTMAutoencoder: input_dim={input_dim}, latent_dim={latent_dim}, bidirectional={bidirectional}")
    
    def forward(
        self,
        x: torch.Tensor
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Forward pass.
        
        Args:
            x: Input sequences (batch_size, seq_len, input_dim)
            
        Returns:
            Tuple of (reconstruction, latent)
        """
        batch_size, seq_len, _ = x.shape
        
        # Encode
        encoder_output, (hidden, cell) = self.encoder_lstm(x)
        
        # Get latent from last hidden state
        if self.bidirectional:
            # Concatenate forward and backward hidden states
            hidden = hidden.view(len(self.hidden_dims), 2, batch_size, -1)
            hidden = torch.cat([hidden[-1, 0], hidden[-1, 1]], dim=1)
        else:
            hidden = hidden[-1]  # Last layer
        
        latent = self.latent_projection(hidden)
        
        # Decode: repeat latent for each time step
        latent_seq = latent.unsqueeze(1).repeat(1, seq_len, 1)
        decoder_output, _ = self.decoder_lstm(latent_seq)
        
        # Project to output
        reconstruction = self.output_projection(decoder_output)
        
        return reconstruction, latent
    
    def reconstruction_error(
        self,
        x: torch.Tensor,
        reduction: str = 'mean'
    ) -> torch.Tensor:
        """Calculate sequence reconstruction error."""
        reconstruction, _ = self.forward(x)
        
        if reduction == 'none':
            # Per-sample error (average over time and features)
            return torch.mean((x - reconstruction) ** 2, dim=(1, 2))
        elif reduction == 'mean':
            return torch.mean((x - reconstruction) ** 2)
        elif reduction == 'sum':
            return torch.sum((x - reconstruction) ** 2)
        else:
            raise ValueError(f"Unknown reduction: {reduction}")
    
    def per_feature_error(self, x: torch.Tensor) -> torch.Tensor:
        """
        Calculate per-feature reconstruction error averaged over time.
        
        Args:
            x: Input sequences (batch_size, seq_len, input_dim)
            
        Returns:
            Per-feature error (batch_size, input_dim)
        """
        reconstruction, _ = self.forward(x)
        # Average over time dimension
        return torch.mean((x - reconstruction) ** 2, dim=1)


class VariationalAutoencoder(nn.Module):
    """
    Variational Autoencoder (VAE) for probabilistic anomaly detection.
    
    Uses reparameterization trick for latent sampling.
    """
    
    def __init__(
        self,
        input_dim: int,
        encoder_dims: List[int] = [128, 64, 32],
        latent_dim: int = 16,
        activation: str = 'relu',
        dropout: float = 0.2
    ):
        """Initialize VAE."""
        super(VariationalAutoencoder, self).__init__()
        
        self.input_dim = input_dim
        self.latent_dim = latent_dim
        
        # Activation
        if activation == 'relu':
            self.activation = nn.ReLU()
        elif activation == 'tanh':
            self.activation = nn.Tanh()
        else:
            self.activation = nn.ELU()
        
        # Encoder
        encoder_layers = []
        prev_dim = input_dim
        
        for dim in encoder_dims:
            encoder_layers.extend([
                nn.Linear(prev_dim, dim),
                self.activation,
                nn.Dropout(dropout)
            ])
            prev_dim = dim
        
        self.encoder = nn.Sequential(*encoder_layers)
        
        # Latent distribution parameters
        self.fc_mu = nn.Linear(prev_dim, latent_dim)
        self.fc_logvar = nn.Linear(prev_dim, latent_dim)
        
        # Decoder
        decoder_layers = []
        decoder_dims = encoder_dims[::-1]
        prev_dim = latent_dim
        
        for dim in decoder_dims:
            decoder_layers.extend([
                nn.Linear(prev_dim, dim),
                self.activation,
                nn.Dropout(dropout)
            ])
            prev_dim = dim
        
        decoder_layers.append(nn.Linear(prev_dim, input_dim))
        
        self.decoder = nn.Sequential(*decoder_layers)
        
        logger.info(f"Created VAE: input_dim={input_dim}, latent_dim={latent_dim}")
    
    def encode(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """Encode to latent distribution parameters."""
        h = self.encoder(x)
        mu = self.fc_mu(h)
        logvar = self.fc_logvar(h)
        return mu, logvar
    
    def reparameterize(self, mu: torch.Tensor, logvar: torch.Tensor) -> torch.Tensor:
        """Reparameterization trick."""
        std = torch.exp(0.5 * logvar)
        eps = torch.randn_like(std)
        return mu + eps * std
    
    def decode(self, z: torch.Tensor) -> torch.Tensor:
        """Decode latent to reconstruction."""
        return self.decoder(z)
    
    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Forward pass.
        
        Returns:
            Tuple of (reconstruction, mu, logvar)
        """
        mu, logvar = self.encode(x)
        z = self.reparameterize(mu, logvar)
        reconstruction = self.decode(z)
        return reconstruction, mu, logvar
    
    def loss_function(
        self,
        x: torch.Tensor,
        reconstruction: torch.Tensor,
        mu: torch.Tensor,
        logvar: torch.Tensor,
        beta: float = 1.0
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        VAE loss = Reconstruction loss + KL divergence.
        
        Args:
            beta: Weight for KL term (beta-VAE)
            
        Returns:
            Tuple of (total_loss, recon_loss, kl_loss)
        """
        # Reconstruction loss (MSE)
        recon_loss = torch.mean((x - reconstruction) ** 2)
        
        # KL divergence
        kl_loss = -0.5 * torch.mean(1 + logvar - mu.pow(2) - logvar.exp())
        
        # Total loss
        total_loss = recon_loss + beta * kl_loss
        
        return total_loss, recon_loss, kl_loss
