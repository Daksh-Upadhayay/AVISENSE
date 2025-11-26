import pandas as pd
import numpy as np
import json

# Load C-MAPSS dataset
print("Loading C-MAPSS dataset...")
df = pd.read_csv('/Users/dakshupadhayay/Downloads/CMaps/train_FD001.txt', 
                 sep=r'\s+', header=None)

# Define column names
index_names = ['unit_id', 'time_cycles']
setting_names = ['setting_1', 'setting_2', 'setting_3']
sensor_names = [f'sensor_{i}' for i in range(1, 22)]
df.columns = index_names + setting_names + sensor_names

# Sensors used in the model
model_sensors = ['sensor_2', 'sensor_3', 'sensor_4', 'sensor_7', 'sensor_9', 
                 'sensor_11', 'sensor_12', 'sensor_14', 'sensor_17', 'sensor_20', 'sensor_21']

# Calculate thresholds (mean ± 2*std for 95% confidence)
thresholds = {}
print("\nSensor Thresholds (Mean ± 2*Std):")
print("="*70)

for sensor in model_sensors:
    mean = df[sensor].mean()
    std = df[sensor].std()
    min_threshold = mean - 2 * std
    max_threshold = mean + 2 * std
    
    thresholds[sensor] = {
        'mean': round(float(mean), 2),
        'std': round(float(std), 2),
        'min': round(float(min_threshold), 2),
        'max': round(float(max_threshold), 2)
    }
    
    print(f"{sensor:12s}: mean={mean:8.2f}, std={std:6.2f}, "
          f"range=[{min_threshold:8.2f}, {max_threshold:8.2f}]")

# Save thresholds to JSON
output_file = 'sensor_thresholds.json'
with open(output_file, 'w') as f:
    json.dump(thresholds, f, indent=2)

print(f"\n✓ Thresholds saved to {output_file}")
