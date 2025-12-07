import numpy as np
from pathlib import Path

def analyze_safe_data():
    data_path = Path("backend/data/processed/train_rul.npz")
    if not data_path.exists():
        print("Data file not found.")
        return

    data = np.load(data_path)
    X = data['X_train'] # (samples, 30, 18) - Scaled
    y = data['y_train_rul'] # (samples,)
    
    # Find indices where RUL is high (Safe)
    safe_indices = np.where(y > 120)[0]
    print(f"Found {len(safe_indices)} safe samples (RUL > 120)")
    
    if len(safe_indices) == 0:
        print("No safe samples found.")
        return

    # Get the safe data (take the last time step of each sequence)
    safe_data = X[safe_indices, -1, :] # (n_safe, 18)
    
    print("\nSafe Data Statistics (Scaled):")
    print(f"Mean: {np.mean(safe_data, axis=0)}")
    print(f"Min: {np.min(safe_data, axis=0)}")
    print(f"Max: {np.max(safe_data, axis=0)}")
    
    # We need unscaled values to update the frontend.
    # Load the scaler
    import joblib
    scaler_path = Path("backend/data/processed/rul_scaler.joblib")
    scaler = joblib.load(scaler_path)
    
    # Inverse transform the mean safe data
    safe_mean_scaled = np.mean(safe_data, axis=0).reshape(1, -1)
    safe_mean_raw = scaler.inverse_transform(safe_mean_scaled)[0]
    
    feature_names = [
        'setting_1', 'setting_2', 'setting_3',
        'sensor_2', 'sensor_3', 'sensor_4', 'sensor_6', 'sensor_7', 'sensor_8', 'sensor_9',
        'sensor_11', 'sensor_12', 'sensor_13', 'sensor_14', 'sensor_15', 'sensor_17', 'sensor_20', 'sensor_21'
    ]
    
    print("\nSafe Data Mean Values (Raw):")
    for name, val in zip(feature_names, safe_mean_raw):
        print(f"{name}: {val:.4f}")

if __name__ == "__main__":
    analyze_safe_data()
