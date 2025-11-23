import pandas as pd
import numpy as np

def get_failure_data():
    # Column names for C-MAPSS dataset
    index_names = ['unit_id', 'time_cycles']
    setting_names = ['setting_1', 'setting_2', 'setting_3']
    sensor_names = [f'sensor_{i}' for i in range(1, 22)]
    col_names = index_names + setting_names + sensor_names
    
    # Load training data
    print("Loading dataset...")
    try:
        df = pd.read_csv('/Users/dakshupadhayay/Downloads/CMaps/train_FD001.txt', 
                        sep='\s+', header=None, names=col_names)
    except Exception as e:
        print(f"Error loading data: {e}")
        return

    # Calculate RUL
    print("Calculating RUL...")
    df['RUL'] = 0
    for unit_id in df['unit_id'].unique():
        unit_data = df[df['unit_id'] == unit_id]
        max_cycle = unit_data['time_cycles'].max()
        df.loc[df['unit_id'] == unit_id, 'RUL'] = max_cycle - df.loc[df['unit_id'] == unit_id, 'time_cycles']
    
    # Filter for failure data (RUL <= 5)
    failure_data = df[df['RUL'] <= 5]
    
    if failure_data.empty:
        print("No failure data found.")
        return

    # Pick a random failure sample
    sample = failure_data.sample(1).iloc[0]
    
    print("\nFOUND REAL FAILURE DATA SAMPLE:")
    print("-" * 30)
    print(f"Unit ID: {sample['unit_id']}")
    print(f"Cycle: {sample['time_cycles']}")
    print(f"RUL: {sample['RUL']}")
    print("-" * 30)
    
    # Print in a format easy to copy
    print("VALUES FOR FORM:")
    print(f"- Setting 1: {sample['setting_1']}")
    print(f"- Setting 2: {sample['setting_2']}")
    print(f"- Setting 3: {sample['setting_3']}")
    for i in range(1, 22):
        print(f"- Sensor {i}: {sample[f'sensor_{i}']}")

if __name__ == "__main__":
    get_failure_data()
