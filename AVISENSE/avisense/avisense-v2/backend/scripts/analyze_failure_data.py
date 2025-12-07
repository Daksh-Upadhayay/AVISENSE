import numpy as np
from pathlib import Path
import joblib

def analyze_failure_data():
    data_path = Path("backend/data/processed/train_rul.npz")
    scaler_path = Path("backend/data/processed/rul_scaler.joblib")
    
    if not data_path.exists():
        print("Data file not found.")
        return

    data = np.load(data_path)
    X = data['X_train'] # (samples, 30, 18) - Scaled
    y = data['y_train_rul'] # (samples,)
    
    # Find indices where RUL is low (Failure)
    # Let's look at RUL < 5 cycles
    failure_indices = np.where(y < 5)[0]
    print(f"Found {len(failure_indices)} failure samples (RUL < 5)")
    
    if len(failure_indices) == 0:
        print("No failure samples found.")
        return

    # Get the failure data (take the last time step of each sequence)
    failure_data = X[failure_indices, -1, :] # (n_failure, 18)
    
    print("\nFailure Data Statistics (Scaled):")
    print(f"Mean: {np.mean(failure_data, axis=0)}")
    
    # Load scaler to get raw values
    scaler = joblib.load(scaler_path)
    
    # Inverse transform the mean failure data
    failure_mean_scaled = np.mean(failure_data, axis=0).reshape(1, -1)
    failure_mean_raw = scaler.inverse_transform(failure_mean_scaled)[0]
    
    feature_names = [
        'setting_1', 'setting_2', 'setting_3',
        'sensor_2', 'sensor_3', 'sensor_4', 'sensor_6', 'sensor_7', 'sensor_8', 'sensor_9',
        'sensor_11', 'sensor_12', 'sensor_13', 'sensor_14', 'sensor_15', 'sensor_17', 'sensor_20', 'sensor_21'
    ]
    
    print("\nFailure Data Mean Values (Raw):")
    for name, val in zip(feature_names, failure_mean_raw):
        print(f"{name}: {val:.4f}")

if __name__ == "__main__":
    analyze_failure_data()
