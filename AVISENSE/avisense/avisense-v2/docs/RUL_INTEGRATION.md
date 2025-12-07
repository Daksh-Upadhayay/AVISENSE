# RUL Integration Guide

## Overview
The Remaining Useful Life (RUL) prediction feature uses an LSTM-based deep learning model trained on the NASA C-MAPSS dataset. It predicts the number of cycles remaining before engine failure.

## 1. Machine Learning Pipeline

### Training
The training script `backend/scripts/train_rul.py` uses configuration from `backend/configs/model_configs/rul_config.yaml`.

**To retrain the model:**
```bash
# 1. Prepare data (if not already done)
python3 backend/scripts/prepare_rul_data.py

# 2. Train model
python3 backend/scripts/train_rul.py --config backend/configs/model_configs/rul_config.yaml
```

### Artifacts
Training produces two key artifacts in `backend/models/deep/`:
1.  `rul_lstm_v{version}.pt`: PyTorch model weights.
2.  `rul_model_info_v{version}.joblib`: Metadata (metrics, input shape, version).
3.  `rul_scaler.joblib`: StandardScaler for feature normalization (created by preparation script).

## 2. Backend Integration

### Endpoint
`POST /predict/rul`

**Request:**
```json
{
  "engine_id": "uuid",
  "use_latest": true
}
```

**Response:**
```json
{
  "rul_prediction": 45.2,
  "rul_uncertainty": 4.2,
  "explainability": { ... }
}
```

### Configuration
Ensure the following environment variables are set:
*   `SUPABASE_URL`: Your Supabase project URL.
*   `SUPABASE_SERVICE_ROLE_KEY`: Service role key for database writes.
*   `MODEL_PATH`: Path to model artifacts (default: `backend/models/deep`).

## 3. Database Schema
The `predictions` table has been extended with:
*   `rul_prediction` (float)
*   `rul_uncertainty` (float)
*   `input_sequence` (jsonb)

Run migration `supabase/migrations/0005_add_rul_features.sql` to apply changes.

## 4. Deployment

### Docker
Build the backend image:
```bash
docker build -t avisense-backend ./backend
```

Run with Docker Compose:
```bash
docker-compose up -d
```

### CI/CD
GitHub Actions workflow `.github/workflows/ci.yml` runs tests and builds the Docker image on push.
