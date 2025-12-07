from fastapi import APIRouter, Depends, HTTPException, Request
from app.models import RULPredictionRequest, RULPredictionResponse
from app.api.deps import get_current_user, get_supabase_client, verify_engine_ownership
from app.ml.model_loader import get_rul_model, get_rul_scaler
from slowapi import Limiter
from slowapi.util import get_remote_address
from datetime import datetime
import logging
import torch
import numpy as np
import joblib
from pathlib import Path

logger = logging.getLogger(__name__)

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

@router.post("/predict/rul", response_model=RULPredictionResponse)
@limiter.limit("10/minute")
async def predict_rul(
    request: Request,
    prediction_request: RULPredictionRequest,
    user=Depends(get_current_user),
    supabase=Depends(get_supabase_client)
):
    """
    Predict Remaining Useful Life (RUL) for an engine.
    """
    try:
        # 1. Verify ownership
        engine = await verify_engine_ownership(
            prediction_request.engine_id,
            user,
            supabase
        )
        
        # 2. Get Model and Scaler
        model = get_rul_model()
        scaler = get_rul_scaler()
        
        if not model or not scaler:
            raise HTTPException(status_code=503, detail="RUL model not loaded")
            
        # 3. Prepare Input Data
        sequence_length = 30 # Default for now, should match training
        n_features = 18 # 14 sensors + 3 settings + 1 cycle? No, scaler expects 18.
        
        input_sequence = []
        
        if prediction_request.use_latest:
            # Fetch latest N records from telemetry
            response = supabase.table("telemetry")\
                .select("*")\
                .eq("engine_id", prediction_request.engine_id)\
                .order("timestamp", desc=True)\
                .limit(sequence_length)\
                .execute()
                
            if not response.data or len(response.data) < 1:
                raise HTTPException(status_code=400, detail="Not enough telemetry data")
                
            # Sort by time ascending
            records = sorted(response.data, key=lambda x: x['timestamp'])
            
            # If we have fewer than sequence_length, pad with the first record
            while len(records) < sequence_length:
                records.insert(0, records[0])
                
            # Extract features
            # Order must match training: setting 1-3, sensors 2,3,4,6,7,8,9,11,12,13,14,15,17,20,21
            for record in records:
                row = []
                # Settings
                row.extend([record.get(f'setting_{i}', 0) for i in range(1, 4)])
                # Sensors
                included_sensors = [2, 3, 4, 6, 7, 8, 9, 11, 12, 13, 14, 15, 17, 20, 21]
                row.extend([record.get(f'sensor_{i}', 0) for i in included_sensors])
                input_sequence.append(row)
                
        else:
            # Use provided input
            if not prediction_request.input_sequence:
                raise HTTPException(status_code=400, detail="Input sequence required if use_latest=False")
                
            # Convert dicts to list of lists
            for item in prediction_request.input_sequence:
                row = []
                row.extend([item.get(f'setting_{i}', 0) for i in range(1, 4)])
                included_sensors = [2, 3, 4, 6, 7, 8, 9, 11, 12, 13, 14, 15, 17, 20, 21]
                row.extend([item.get(f'sensor_{i}', 0) for i in included_sensors])
                input_sequence.append(row)

        # 4. Preprocess
        X = np.array(input_sequence)
        
        # Scale
        # Scaler expects (n_samples, n_features)
        # We have (sequence_length, n_features)
        X_scaled = scaler.transform(X)
        
        # Reshape for LSTM: (1, sequence_length, n_features)
        X_tensor = torch.FloatTensor(X_scaled).unsqueeze(0)
        
        # 5. Predict
        with torch.no_grad():
            rul_pred = model(X_tensor)
            rul_value = rul_pred.item()
            
        # Cap RUL
        rul_value = max(0, min(rul_value, 130))
        
        # Uncertainty (Mock for now, or use dropout)
        # For now, we'll use a heuristic based on RUL value (higher RUL = higher uncertainty)
        uncertainty = 2.0 + (rul_value * 0.05)
        
        # Explainability (Mock for now, or use SHAP/IG)
        # We'll return top contributing features based on simple variance or just static for now
        # Ideally we'd use Captum or SHAP here
        explainability = {
            "top_features": [
                {"feature": "sensor_11", "percent": 25.0},
                {"feature": "sensor_9", "percent": 20.0},
                {"feature": "sensor_4", "percent": 15.0}
            ]
        }
        
        # 6. Save to DB
        prediction_record = {
            "engine_id": prediction_request.engine_id,
            "prediction": "SAFE" if rul_value > 50 else "PRONE TO FAILURE", # Dummy for schema compliance
            "probability": 0.0, # Dummy
            "confidence": 1.0,
            "safe_probability": 0.0,
            "failure_probability": 0.0,
            "model_version": "v1.0.0", # Should get from model info
            "model_type": "rul_lstm",
            "model_family": "rul_lstm",
            "rul_prediction": float(rul_value),
            "rul_uncertainty": float(uncertainty),
            "explainability": explainability,
            "input_data": {}, # We used a sequence, store in separate field if possible or empty
            "created_by": user.id
        }
        
        db_response = supabase.table("predictions").insert(prediction_record).execute()
        saved_id = db_response.data[0]['id'] if db_response.data else None
        
        # 7. Return Response
        return RULPredictionResponse(
            engine_id=prediction_request.engine_id,
            timestamp=datetime.now(),
            model_family="rul_lstm",
            model_version="v1.0.0",
            rul_prediction=float(rul_value),
            rul_uncertainty=float(uncertainty),
            explainability=explainability,
            provenance={
                "scaler": "rul_scaler.joblib",
                "artifact": "rul_lstm_v1.0.0.pt"
            },
            saved_prediction_id=saved_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"RUL prediction failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
