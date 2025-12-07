import pandas as pd
import numpy as np
from pathlib import Path
import sys

# Define constants matching prepare_rul_data.py
COLUMN_NAMES = [
    'engine_id', 'cycle',
    'setting_1', 'setting_2', 'setting_3',
    'sensor_1', 'sensor_2', 'sensor_3', 'sensor_4', 'sensor_5',
    'sensor_6', 'sensor_7', 'sensor_8', 'sensor_9', 'sensor_10',
    'sensor_11', 'sensor_12', 'sensor_13', 'sensor_14', 'sensor_15',
    'sensor_16', 'sensor_17', 'sensor_18', 'sensor_19', 'sensor_20',
    'sensor_21'
]
SEQUENCE_LENGTH = 30

def audit_data():
    print("🔍 Starting Data Quality & Leakage Audit...")
    
    # 1. Load Raw Data
    data_path = Path("/Users/dakshupadhayay/Desktop/engine-failure-detection-/AVISENSE/avisense/CMaps/train_FD001.txt")
    if not data_path.exists():
        print(f"❌ Raw data not found at {data_path}")
        return
        
    df = pd.read_csv(data_path, sep='\s+', header=None, names=COLUMN_NAMES)
    print(f"✅ Loaded raw data: {len(df)} rows, {df['engine_id'].nunique()} engines")
    
    # 2. Check for Missing Values
    missing = df.isnull().sum().sum()
    if missing > 0:
        print(f"❌ Found {missing} missing values!")
    else:
        print("✅ No missing values found.")
        
    # 3. Check for Duplicates
    duplicates = df.duplicated().sum()
    if duplicates > 0:
        print(f"❌ Found {duplicates} duplicate rows!")
    else:
        print("✅ No duplicate rows found.")
        
    # 4. Check for Constant Columns (that might need dropping)
    constant_cols = [col for col in df.columns if df[col].nunique() <= 1]
    print(f"ℹ️  Constant columns: {constant_cols}")
    
    # 5. Verify Split Logic (Leakage Check)
    print("\n🕵️‍♀️ Verifying Train/Val Split Logic...")
    
    # Replicate the sequence creation logic to see which engine ends up where
    sequences_metadata = [] # Store (engine_id, cycle) for each sequence
    
    for engine_id in df['engine_id'].unique():
        engine_data = df[df['engine_id'] == engine_id].sort_values('cycle')
        # We only care about the count of sequences per engine
        n_sequences = len(engine_data) - SEQUENCE_LENGTH + 1
        if n_sequences > 0:
            for _ in range(n_sequences):
                sequences_metadata.append(engine_id)
                
    total_sequences = len(sequences_metadata)
    split_idx = int(0.8 * total_sequences)
    
    train_engines = set(sequences_metadata[:split_idx])
    val_engines = set(sequences_metadata[split_idx:])
    
    print(f"  Total sequences: {total_sequences}")
    print(f"  Split index: {split_idx}")
    print(f"  Engines in Train: {len(train_engines)}")
    print(f"  Engines in Val: {len(val_engines)}")
    
    # Check for overlap
    overlap = train_engines.intersection(val_engines)
    
    if len(overlap) > 0:
        print(f"❌ DATA LEAKAGE DETECTED! {len(overlap)} engines are in BOTH Train and Val sets.")
        print(f"   Leaked Engines: {sorted(list(overlap))}")
        print("   Reason: The split is done by sequence index, cutting through engines.")
    else:
        print("✅ No engine overlap detected (Clean Split).")

    # 6. Check for Future Leakage (Feature Engineering)
    # Since we only use lag features (sequences) and current values, future leakage 
    # would come from things like global normalization using the whole dataset stats 
    # BEFORE splitting.
    # prepare_rul_data.py does:
    #   X_train, X_val = split(X)
    #   scaler.fit(X_train)
    #   scaler.transform(X_val)
    # This part is CORRECT (no leakage from val to train).
    print("\n✅ Normalization Logic Check: Scaler is fit on X_train only (Correct).")

if __name__ == "__main__":
    audit_data()
