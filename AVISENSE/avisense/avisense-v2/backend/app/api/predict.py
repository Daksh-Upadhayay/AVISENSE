from fastapi import APIRouter, Depends, HTTPException, Request
from app.models import PredictionRequest, PredictionResponse
from app.api.deps import get_current_user, get_supabase_client, verify_engine_ownership
from app.ml.predictor import run_prediction
from app.ml.anomaly import detect_anomalies
from slowapi import Limiter
from slowapi.util import get_remote_address
from datetime import datetime
import logging

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
    3. Runs ML model prediction
    4. Detects sensor anomalies
    5. Saves prediction to database
    6. Returns prediction result
    
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
        
        # Run ML prediction
        prediction_result = await run_prediction(prediction_request.input_data)
        
        # Detect anomalies
        anomalies = detect_anomalies(prediction_request.input_data)
        
        # Optionally create telemetry record
        telemetry_id = None
        if prediction_request.source in ['ui', 'manual']:
            telemetry_data = {
                'engine_id': prediction_request.engine_id,
                'timestamp': datetime.now().isoformat(),
                'source': prediction_request.source,
                **prediction_request.input_data
            }
            
            telemetry_response = supabase.table('telemetry').insert(telemetry_data).execute()
            if telemetry_response.data:
                telemetry_id = telemetry_response.data[0]['id']
        
        # Save prediction to Supabase
        try:
            prediction_record = {
                "engine_id": prediction_request.engine_id,
                "telemetry_id": telemetry_id,
                "prediction": prediction_result["prediction"],
                "probability": prediction_result["probability"],
                "failure_probability": prediction_result["failure_probability"],
                "safe_probability": prediction_result["safe_probability"],
                "confidence": prediction_result["confidence"],
                "actions": prediction_result["actions"],
                "anomalies": anomalies, # Use the anomalies detected earlier
                "shap_values": prediction_result.get("shap", {}),
                "risk_percent": prediction_result.get("risk_percent"),
                "correlated_anomalies": prediction_result.get("correlated_anomalies", []),
                "model_version": prediction_result["model_version"],
                "model_type": prediction_result["model_type"],
                "input_data": prediction_request.input_data,
                "source": prediction_request.source,
                "created_by": user.id
            }
            
            data, count = supabase.table("predictions").insert(prediction_record).execute()
            
            # Add ID and timestamp from DB response
            if data and len(data[1]) > 0:
                db_record = data[1][0]
                prediction_result["id"] = db_record["id"]
                prediction_result["created_at"] = db_record["created_at"]
                prediction_result["input_data"] = prediction_request.input_data # Ensure input data is returned
            else:
                # Fallback if DB insert doesn't return data (shouldn't happen)
                prediction_result["id"] = "temp-id"
                prediction_result["created_at"] = datetime.now().isoformat()
                prediction_result["input_data"] = prediction_request.input_data

        except Exception as e:
            logger.error(f"Failed to save prediction to DB: {e}", exc_info=True)
            # Continue even if DB save fails, but log it
            prediction_result["id"] = "error-saving"
            prediction_result["created_at"] = datetime.now().isoformat()
            prediction_result["input_data"] = prediction_request.input_data
        
        # Use prediction_result for the response, which now includes DB fields if successful
        prediction_data = prediction_result
        
        # Log high-risk predictions
        if prediction_result['failure_probability'] >= 0.8:
            logger.warning(
                f"🚨 HIGH RISK prediction for engine {engine['engine_id']}: "
                f"{prediction_result['failure_probability']:.1%} failure probability"
            )
        
        # Return response
        return PredictionResponse(
            id=prediction_data['id'],
            prediction=prediction_data['prediction'],
            probability=prediction_data['probability'],
            confidence=prediction_data['confidence'],
            safe_probability=prediction_data['safe_probability'],
            failure_probability=prediction_data['failure_probability'],
            timestamp=datetime.fromisoformat(prediction_data['created_at']),
            engine_id=prediction_request.engine_id, # Use prediction_request.engine_id as it's always available
            actions=prediction_data['actions'],
            anomalies=prediction_data['anomalies'],
            model_version=prediction_data['model_version'],
            model_type=prediction_data['model_type'],
            input_data=prediction_data['input_data'],
            shap=prediction_data.get('shap'),
            risk_percent=prediction_data.get('risk_percent'),
            correlated_anomalies=prediction_data.get('correlated_anomalies'),
            created_by=prediction_data.get('created_by'),
            created_at=datetime.fromisoformat(prediction_data['created_at']) if isinstance(prediction_data['created_at'], str) else prediction_data['created_at']
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Prediction failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Prediction failed: {str(e)}"
        )

