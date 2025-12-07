import torch
import torch.nn as nn

class RULRegressor(nn.Module):
    """
    LSTM-based RUL (Remaining Useful Life) Regressor.
    Predicts the number of remaining cycles before failure.
    """
    
    def __init__(self, input_dim, hidden_dim=100, num_layers=2, dropout=0.2):
        super(RULRegressor, self).__init__()
        
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        
        # LSTM layers
        self.lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0
        )
        
        # Fully connected layers for regression
        # Simplified to match training script architecture
        self.fc = nn.Linear(hidden_dim, 1)
        
    def forward(self, x):
        # x shape: (batch_size, seq_len, input_dim)
        
        # LSTM forward pass
        # out shape: (batch_size, seq_len, hidden_dim)
        out, _ = self.lstm(x)
        
        # Take the output from the last time step
        # out[:, -1, :] shape: (batch_size, hidden_dim)
        last_step_out = out[:, -1, :]
        
        # Regression
        rul_pred = self.fc(last_step_out)
        
        return rul_pred
