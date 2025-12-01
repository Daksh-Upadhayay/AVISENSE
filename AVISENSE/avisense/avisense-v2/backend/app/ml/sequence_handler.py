from collections import deque
import numpy as np
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class SequenceHandler:
    """
    Manages historical sensor readings to build sequences for LSTM models.
    """
    
    def __init__(self, window_length: int = 32, n_features: int = 24):
        """
        Initialize SequenceHandler.
        
        Args:
            window_length: Number of time steps in sequence
            n_features: Number of features per time step
        """
        self.window_length = window_length
        self.n_features = n_features
        # Dictionary to store history for each engine
        # engine_id -> deque of readings
        self.history: Dict[str, deque] = {}
        
    def add_reading(self, engine_id: str, reading: List[float]) -> None:
        """
        Add a new sensor reading for an engine.
        
        Args:
            engine_id: Engine identifier
            reading: List of sensor values (must match n_features)
        """
        if len(reading) != self.n_features:
            logger.warning(f"Reading has {len(reading)} features, expected {self.n_features}")
            
        if engine_id not in self.history:
            self.history[engine_id] = deque(maxlen=self.window_length)
            
        self.history[engine_id].append(reading)
        
    def get_sequence(self, engine_id: str) -> Optional[np.ndarray]:
        """
        Get the current sequence for an engine.
        
        Returns:
            np.ndarray of shape (window_length, n_features) or None if not enough history
        """
        if engine_id not in self.history:
            return None
            
        history = self.history[engine_id]
        
        if len(history) < self.window_length:
            # Not enough history yet
            # Strategy: Pad with the first reading or repeat
            # For now, we'll return None and let the caller decide (e.g., use Dense AE)
            # Or we can pad with the current reading to fill the window
            return self._pad_sequence(list(history))
            
        return np.array(history)
    
    def _pad_sequence(self, history: List[List[float]]) -> np.ndarray:
        """Pad sequence to window_length by repeating the first reading."""
        current_len = len(history)
        missing = self.window_length - current_len
        
        if missing <= 0:
            return np.array(history)
            
        # Pad with the oldest available reading (index 0)
        padding = [history[0]] * missing
        return np.array(padding + history)

    def clear_history(self, engine_id: str) -> None:
        """Clear history for an engine."""
        if engine_id in self.history:
            del self.history[engine_id]
