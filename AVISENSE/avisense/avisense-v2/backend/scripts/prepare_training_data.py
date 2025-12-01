#!/usr/bin/env python3
"""
Prepare Training Data for Deep Learning Models

This script processes raw telemetry CSV data and creates training-ready
sequences for deep learning models (autoencoders, LSTM, RUL regression).

Usage:
    python scripts/prepare_training_data.py \
        --input data/raw/telemetry.csv \
        --output data/processed/ \
        --window-length 64 \
        --stride 4 \
        --max-rul 125

Output:
    - train.npz: Training sequences and labels
    - val.npz: Validation sequences and labels
    - test.npz: Test sequences and labels
    - scaler.joblib: Fitted scaler artifact
    - metadata.json: Dataset metadata and statistics
"""

import argparse
import json
import logging
from pathlib import Path
import sys

import numpy as np
import pandas as pd

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.data import SequenceBuilder, TimeSeriesScaler, handle_missing_data, validate_data

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_and_preprocess(
    input_path: str,
    engine_id_col: str = 'engine_id',
    cycle_col: str = 'cycle',
    label_col: str = None
) -> pd.DataFrame:
    """Load and preprocess raw telemetry data."""
    logger.info(f"Loading data from {input_path}")
    
    # Load CSV
    data = pd.read_csv(input_path)
    logger.info(f"Loaded {len(data)} rows, {len(data.columns)} columns")
    
    # Validate data
    validation_report = validate_data(data, label_col=label_col)
    logger.info(f"Validation report: {json.dumps(validation_report['feature_stats'], indent=2)}")
    
    # Handle missing data
    data = handle_missing_data(data, strategy='ffill')
    
    return data


def main():
    parser = argparse.ArgumentParser(description='Prepare training data for deep learning models')
    
    # Input/Output
    parser.add_argument('--input', type=str, required=True, help='Path to input CSV file')
    parser.add_argument('--output', type=str, required=True, help='Output directory for processed data')
    
    # Sequence parameters
    parser.add_argument('--window-length', type=int, default=64, help='Sequence window length')
    parser.add_argument('--stride', type=int, default=4, help='Stride between windows')
    
    # RUL parameters
    parser.add_argument('--max-rul', type=int, default=125, help='Maximum RUL cap (None for no cap)')
    parser.add_argument('--generate-rul', action='store_true', help='Generate RUL labels')
    
    # Split parameters
    parser.add_argument('--train-ratio', type=float, default=0.7, help='Training set ratio')
    parser.add_argument('--val-ratio', type=float, default=0.15, help='Validation set ratio')
    parser.add_argument('--random-seed', type=int, default=42, help='Random seed')
    
    # Column names
    parser.add_argument('--engine-id-col', type=str, default='engine_id', help='Engine ID column name')
    parser.add_argument('--cycle-col', type=str, default='cycle', help='Cycle/time column name')
    parser.add_argument('--label-col', type=str, default=None, help='Binary label column (optional)')
    
    # Scaler
    parser.add_argument('--scaler-type', type=str, default='standard', choices=['standard', 'robust'],
                        help='Scaler type')
    
    args = parser.parse_args()
    
    # Create output directory
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load and preprocess data
    data = load_and_preprocess(
        args.input,
        engine_id_col=args.engine_id_col,
        cycle_col=args.cycle_col,
        label_col=args.label_col
    )
    
    # Initialize sequence builder
    builder = SequenceBuilder(
        window_length=args.window_length,
        stride=args.stride
    )
    
    # Generate RUL labels if requested
    if args.generate_rul:
        logger.info("Generating RUL labels")
        data = builder.generate_rul_labels(
            data,
            engine_id_col=args.engine_id_col,
            cycle_col=args.cycle_col,
            max_rul=args.max_rul if args.max_rul > 0 else None
        )
        
        # Build RUL sequences
        sequences, rul_targets, engine_ids = builder.build_rul_sequences(
            data,
            engine_id_col=args.engine_id_col,
            cycle_col=args.cycle_col
        )
        labels = rul_targets
        task_type = 'regression'
    else:
        # Build classification sequences
        sequences, labels, engine_ids = builder.build_sequences(
            data,
            engine_id_col=args.engine_id_col,
            cycle_col=args.cycle_col,
            label_col=args.label_col
        )
        task_type = 'classification'
    
    logger.info(f"Built sequences: shape={sequences.shape}, task={task_type}")
    
    # Split by engines
    splits = builder.split_by_engines(
        sequences,
        labels,
        engine_ids,
        train_ratio=args.train_ratio,
        val_ratio=args.val_ratio,
        random_seed=args.random_seed
    )
    
    # Fit scaler on training data
    logger.info("Fitting scaler on training data")
    scaler = TimeSeriesScaler(scaler_type=args.scaler_type)
    X_train, y_train = splits['train']
    scaler.fit(X_train, feature_names=builder.feature_columns)
    
    # Transform all splits
    logger.info("Scaling data")
    X_train_scaled = scaler.transform(X_train)
    X_val_scaled = scaler.transform(splits['val'][0])
    X_test_scaled = scaler.transform(splits['test'][0])
    
    # Save splits
    logger.info("Saving processed data")
    np.savez_compressed(
        output_dir / 'train.npz',
        X=X_train_scaled,
        y=y_train
    )
    np.savez_compressed(
        output_dir / 'val.npz',
        X=X_val_scaled,
        y=splits['val'][1]
    )
    np.savez_compressed(
        output_dir / 'test.npz',
        X=X_test_scaled,
        y=splits['test'][1]
    )
    
    # Save scaler
    scaler_path = output_dir / 'scaler.joblib'
    scaler.save(str(scaler_path))
    
    # Save metadata
    metadata = {
        'task_type': task_type,
        'window_length': args.window_length,
        'stride': args.stride,
        'n_features': len(builder.feature_columns),
        'feature_names': builder.feature_columns,
        'scaler_type': args.scaler_type,
        'max_rul': args.max_rul if args.generate_rul else None,
        'splits': {
            'train': {'n_samples': len(X_train)},
            'val': {'n_samples': len(splits['val'][0])},
            'test': {'n_samples': len(splits['test'][0])}
        }
    }
    
    # Add label distribution only if labels exist
    if y_train is not None:
        metadata['label_distribution'] = {
            'train': {
                'mean': float(y_train.mean()),
                'std': float(y_train.std()),
                'min': float(y_train.min()),
                'max': float(y_train.max())
            }
        }
    
    
    metadata_path = output_dir / 'metadata.json'
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    logger.info(f"✅ Data preparation complete!")
    logger.info(f"   Output directory: {output_dir}")
    logger.info(f"   Train: {len(X_train)} samples")
    logger.info(f"   Val: {len(splits['val'][0])} samples")
    logger.info(f"   Test: {len(splits['test'][0])} samples")
    logger.info(f"   Metadata: {metadata_path}")


if __name__ == '__main__':
    main()
