#!/usr/bin/env python3
"""
Convert NASA C-MAPSS TXT files to CSV format

The C-MAPSS data comes as space-separated TXT files without headers.
This script adds proper column names and converts to CSV.
"""

import pandas as pd
import sys

# Column names for C-MAPSS dataset
COLUMN_NAMES = [
    'engine_id', 'cycle',
    'setting_1', 'setting_2', 'setting_3',
    'sensor_1', 'sensor_2', 'sensor_3', 'sensor_4', 'sensor_5',
    'sensor_6', 'sensor_7', 'sensor_8', 'sensor_9', 'sensor_10',
    'sensor_11', 'sensor_12', 'sensor_13', 'sensor_14', 'sensor_15',
    'sensor_16', 'sensor_17', 'sensor_18', 'sensor_19', 'sensor_20',
    'sensor_21'
]

def convert_cmapss_to_csv(input_file, output_file):
    """Convert C-MAPSS TXT to CSV with headers."""
    print(f"Reading {input_file}...")
    
    # Read space-separated file
    df = pd.read_csv(input_file, sep='\s+', header=None, names=COLUMN_NAMES)
    
    print(f"Loaded {len(df)} rows, {len(df.columns)} columns")
    print(f"Engines: {df['engine_id'].nunique()}")
    print(f"Cycles per engine: {df.groupby('engine_id')['cycle'].max().describe()}")
    
    # Add failure label (last cycle for each engine = failure)
    df['label'] = 0
    for engine_id in df['engine_id'].unique():
        engine_data = df[df['engine_id'] == engine_id]
        max_cycle = engine_data['cycle'].max()
        # Mark last 10 cycles as failure (degradation period)
        df.loc[(df['engine_id'] == engine_id) & (df['cycle'] >= max_cycle - 10), 'label'] = 1
    
    print(f"Failure samples: {df['label'].sum()} ({df['label'].mean()*100:.1f}%)")
    
    # Save to CSV
    df.to_csv(output_file, index=False)
    print(f"✅ Saved to {output_file}")
    
    return df

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python convert_cmapss.py <input.txt> <output.csv>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    convert_cmapss_to_csv(input_file, output_file)
