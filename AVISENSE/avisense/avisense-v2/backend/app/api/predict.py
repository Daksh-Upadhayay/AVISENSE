from fastapi import APIRouter, Depends, HTTPException, Request
from app.models import PredictionRequest, PredictionResponse
from app.api.deps import get_current_user, get_supabase_client, verify_engine_ownership
from app.ml.predictor import run_prediction
from app.ml.anomaly import detect_anomalies
from slowapi import Limiter
from slowapi.util import get_remote_address
from datetime import datetime
import logging
import torch
import numpy as np

logger = logging.getLogger(__name__)

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.post("/predict", response_model=PredictionResponse)
@limiter.limit("10/minute")
async def predict(
    request: Request,
    prediction_request: PredictionRequest,
    user=Depends(get_current_user),
    supabase=Depends(get_supabase_client)
):
    """
    Run ML prediction on engine telemetry data.
    
    This endpoint:
    1. Validates user authentication
    2. Verifies engine ownership
    3. Runs deterministic ML inference
    4. Saves prediction to database
    5. Returns prediction result
    
    Rate limit: 10 requests per minute per user
    """
    try:
        # Verify engine ownership
        engine = await verify_engine_ownership(
            prediction_request.engine_id,
            user,
            supabase
        )
        
        logger.info(f"Running prediction for engine {engine['engine_id']} (user: {user.email})")
        
        # Run Deterministic Inference
        from app.core.inference import run_deterministic_inference
        prediction_result = await run_deterministic_inference(
            prediction_request.input_data,
            source=prediction_request.source
        )
        
        # Add Engine ID (not returned by inference)
        prediction_result['engine_id'] = prediction_request.engine_id
        
        # Save to Database
        telemetry_id = None
        if prediction_request.source in ['ui', 'manual']:
             # Define known columns in telemetry table
            known_columns = {
                'engine_id', 'timestamp', 'time_cycles', 'source', 'metadata',
                'setting_1', 'setting_2', 'setting_3',
                'sensor_2', 'sensor_3', 'sensor_4', 'sensor_7', 'sensor_9',
                'sensor_11', 'sensor_12', 'sensor_14', 'sensor_17', 'sensor_20', 'sensor_21'
            }
            
            insert_data = {
                'engine_id': prediction_request.engine_id,
                'timestamp': datetime.now().isoformat(),
                'source': prediction_request.source,
                'metadata': {}
            }
            
            for key, value in prediction_request.input_data.items():
                if key in known_columns:
                    insert_data[key] = value
                else:
                    insert_data['metadata'][key] = value
            
            try:
                telemetry_response = supabase.table('telemetry').insert(insert_data).execute()
                if telemetry_response.data:
                    telemetry_id = telemetry_response.data[0]['id']
            except Exception as e:
                logger.error(f"Failed to save telemetry: {e}")

        try:
            prediction_record = {
                "engine_id": prediction_request.engine_id,
                "telemetry_id": telemetry_id,
                "prediction": prediction_result["prediction"],
                "probability": prediction_result["probability"],
                "failure_probability": prediction_result["failure_probability"],
                "safe_probability": prediction_result["safe_probability"],
                "confidence": 0.0, # Deprecated or calculate from probability
                "actions": [], # Deprecated
                "anomalies": prediction_result.get("anomalies", []),
                "shap_values": prediction_result.get("shap_values", {}),
                "risk_percent": prediction_result.get("risk_percent"),
                "correlated_anomalies": [],
                "model_version": prediction_result["model_version"],
                "model_type": "hybrid_v2",
                "input_data": prediction_request.input_data,
                "source": prediction_request.source,
                "created_by": user.id,
                "anomaly_score": prediction_result.get("anomaly_score"),
                "reconstruction_errors": {} # TODO: Add if available
            }
            
            data, count = supabase.table("predictions").insert(prediction_record).execute()
            
            if data and len(data[1]) > 0:
                db_record = data[1][0]
                prediction_result["id"] = db_record["id"]
                prediction_result["created_at"] = db_record["created_at"]
            else:
                prediction_result["id"] = "temp-id"
                prediction_result["created_at"] = datetime.now().isoformat()

        except Exception as e:
            logger.error(f"Failed to save prediction to DB: {e}", exc_info=True)
            prediction_result["id"] = "error-saving"
            prediction_result["created_at"] = datetime.now().isoformat()
        
        # Log high-risk
        if prediction_result['failure_probability'] >= 0.8:
            logger.warning(f"🚨 HIGH RISK prediction for engine {engine['engine_id']}")
            
        return PredictionResponse(
            id=prediction_result['id'],
            prediction=prediction_result['prediction'],
            probability=prediction_result['probability'],
            confidence=0.95, # Placeholder
            safe_probability=prediction_result['safe_probability'],
            failure_probability=prediction_result['failure_probability'],
            timestamp=datetime.fromisoformat(prediction_result['created_at']) if isinstance(prediction_result['created_at'], str) else prediction_result['created_at'],
            engine_id=prediction_request.engine_id,
            actions="",
            anomalies=prediction_result.get('anomalies', []),
            model_version=prediction_result['model_version'],
            model_type="hybrid_v2",
            input_data=prediction_request.input_data,
            shap=prediction_result.get('shap_values'),
            risk_percent=prediction_result.get('risk_percent'),
            anomaly_score_normalized=prediction_result.get('anomaly_score_normalized'),
            correlated_anomalies=[],
            rul_prediction=prediction_result.get('rul_prediction'),
            created_by=user.id,
            created_at=datetime.fromisoformat(prediction_result['created_at']) if isinstance(prediction_result['created_at'], str) else prediction_result['created_at']
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Prediction failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Prediction failed: {str(e)}"
        )

