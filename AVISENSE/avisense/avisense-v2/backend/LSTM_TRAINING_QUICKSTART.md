# LSTM Autoencoder Training - Quick Start Guide

## Overview
Train an LSTM-based autoencoder for improved temporal anomaly detection in engine sensor data.

## Prerequisites
- Processed training data in `data/processed/train.npz`
- Python dependencies installed (`requirements-deep.txt`)

## Quick Start

### 1. Generate Sample Data (if needed)
```bash
cd backend

# Generate synthetic C-MAPSS-like data
python scripts/generate_sample_data.py \
  --output data/raw/sample_cmapss.csv \
  --n_engines 100 \
  --failure_rate 0.3

# Prepare sequences for training
python scripts/prepare_training_data.py \
  --input data/raw/sample_cmapss.csv \
  --output data/processed \
  --window_length 32 \
  --stride 4 \
  --task classification
```

### 2. Train LSTM Autoencoder
```bash
python scripts/train_lstm_autoencoder.py \
  --config configs/model_configs/lstm_autoencoder_config.yaml \
  --data data/processed/train.npz \
  --output models/deep/lstm_ae_v1.pt \
  --device cpu
```

**Expected Output**:
```
Loaded 5000 sequences with shape (5000, 32, 14)
Initialized model on cpu
Model parameters: 245,678
Starting training...
Epoch 1/100 | Train Loss: 0.125000 | Val Loss: 0.118000 | LR: 0.001000
...
✅ Saved best model to models/deep/lstm_ae_v1.pt
Test AUROC: 0.9350
🎉 Training complete!
```

### 3. Verify Model
```bash
# Check model file
ls -lh models/deep/lstm_ae_v1.pt

# Check metrics
cat models/deep/lstm_ae_v1_metrics.json
```

## Configuration Options

### Key Parameters
- `window_length: 32` - Sequence length (increase for longer patterns)
- `hidden_dims: [128, 64]` - LSTM layer sizes
- `bidirectional: true` - Use bidirectional LSTM (better accuracy)
- `dropout: 0.3` - Regularization strength
- `batch_size: 64` - Training batch size
- `learning_rate: 0.001` - Initial learning rate

### For Better Performance
```yaml
# In lstm_autoencoder_config.yaml
model:
  hidden_dims: [256, 128]  # Larger model
  latent_dim: 64
  
training:
  batch_size: 32  # Smaller batches for stability
  epochs: 150  # More training
```

### For Faster Training
```yaml
model:
  hidden_dims: [64, 32]  # Smaller model
  bidirectional: false
  
training:
  batch_size: 128
  epochs: 50
```

## Expected Performance

| Metric | Dense AE | LSTM AE (Target) |
|--------|----------|------------------|
| AUROC | 0.914 | **>0.925** |
| Precision@10% | 0.82 | **>0.87** |
| Lead-Time (cycles) | 3-5 | **7-12** |
| Training Time | 5 min | 15-20 min |

## Troubleshooting

### Out of Memory
```bash
# Reduce batch size
--config configs/model_configs/lstm_autoencoder_config.yaml
# Edit: training.batch_size: 32
```

### Poor Performance
- Increase `window_length` to 64 (more temporal context)
- Enable data augmentation in config
- Train longer (increase `epochs`)
- Use GPU if available (`--device cuda`)

### Training Too Slow
- Disable bidirectional LSTM
- Reduce `hidden_dims`
- Increase `batch_size`

## Next Steps

After training:
1. **Sprint 6**: Integrate LSTM into backend API
2. **Sprint 7**: Add LSTM selector to frontend UI
3. **Evaluation**: Compare LSTM vs Dense AE in notebook

## Files Created
- `models/deep/lstm_ae_v1.pt` - Trained model checkpoint
- `models/deep/lstm_ae_v1_metrics.json` - Evaluation metrics
- `configs/model_configs/lstm_autoencoder_config.yaml` - Configuration
