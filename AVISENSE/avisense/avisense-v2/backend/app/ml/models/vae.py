import torch
import torch.nn as nn
import torch.nn.functional as F

class VAE(nn.Module):
    def __init__(self, input_dim, hidden_dim1=64, hidden_dim2=32, latent_dim=8, sequence_length=30):
        super(VAE, self).__init__()
        
        self.input_dim = input_dim
        self.sequence_length = sequence_length
        self.latent_dim = latent_dim

        # Encoder
        # Input: (batch, seq_len, input_dim) -> Flatten -> (batch, seq_len * input_dim)
        self.input_flattened_dim = sequence_length * input_dim
        
        self.encoder = nn.Sequential(
            nn.Linear(self.input_flattened_dim, hidden_dim1),
            nn.ReLU(),
            nn.Linear(hidden_dim1, hidden_dim2),
            nn.ReLU()
        )
        
        # Latent space (Mean and Log Variance)
        self.fc_mu = nn.Linear(hidden_dim2, latent_dim)
        self.fc_logvar = nn.Linear(hidden_dim2, latent_dim)
        
        # Decoder
        self.decoder_input = nn.Linear(latent_dim, hidden_dim2)
        
        self.decoder = nn.Sequential(
            nn.Linear(hidden_dim2, hidden_dim1),
            nn.ReLU(),
            nn.Linear(hidden_dim1, self.input_flattened_dim),
            nn.Sigmoid() # Assuming scaled data in [0, 1] or similar range
        )

    def encode(self, x):
        # Flatten input: (batch, seq_len, input_dim) -> (batch, seq_len * input_dim)
        x_flat = x.view(x.size(0), -1)
        h = self.encoder(x_flat)
        mu = self.fc_mu(h)
        logvar = self.fc_logvar(h)
        return mu, logvar

    def reparameterize(self, mu, logvar):
        std = torch.exp(0.5 * logvar)
        eps = torch.randn_like(std)
        return mu + eps * std

    def decode(self, z):
        h = self.decoder_input(z)
        h = F.relu(h)
        x_recon_flat = self.decoder(h)
        # Reshape back to sequence: (batch, seq_len * input_dim) -> (batch, seq_len, input_dim)
        x_recon = x_recon_flat.view(x_recon_flat.size(0), self.sequence_length, self.input_dim)
        return x_recon

    def forward(self, x):
        mu, logvar = self.encode(x)
        z = self.reparameterize(mu, logvar)
        x_recon = self.decode(z)
        return x_recon, mu, logvar

    def loss_function(self, x, x_recon, mu, logvar, beta=1.0):
        # Reconstruction Loss (MSE)
        recon_loss = F.mse_loss(x_recon, x, reduction='sum')
        
        # KL Divergence
        # KLD = -0.5 * sum(1 + log(sigma^2) - mu^2 - sigma^2)
        kld_loss = -0.5 * torch.sum(1 + logvar - mu.pow(2) - logvar.exp())
        
        return recon_loss + beta * kld_loss, recon_loss, kld_loss
