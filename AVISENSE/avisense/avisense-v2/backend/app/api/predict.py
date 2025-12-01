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
        
        logger.info(f"Running prediction for engine {engine['engine_id']} (user: {user.email}, use_deep={prediction_request.use_deep})")
        
        # Run ML prediction (RandomForest)
        prediction_result = await run_prediction(prediction_request.input_data)
        
        # Detect anomalies (traditional threshold-based)
        anomalies = detect_anomalies(prediction_request.input_data)
        
        # Deep learning anomaly detection (if requested and available)
        # Deep learning anomaly detection (if requested and available)
        # Deep learning anomaly detection (if requested and available)
        if prediction_request.use_deep:
            from app.ml.model_loader import (
                get_anomaly_scorer, is_autoencoder_loaded,
                get_vae_scorer, get_sequence_handler, get_rul_model
            )
            
            # Determine which model to use
            model_family = prediction_request.model_family
            
            # VAE (Variational Autoencoder) - Primary Deep Learning Model
            if model_family == 'vae' or model_family == 'lstm_ae':  # Accept both for backward compatibility
                vae_scorer = get_vae_scorer()
                sequence_handler = get_sequence_handler()
                
                if vae_scorer and sequence_handler:
                    try:
                        # VAE scorer builds its own sequence from input_data dict
                        # No need to use sequence_handler for VAE
                        ae_result = vae_scorer.score(prediction_request.input_data, return_details=True)
                        
                        # Add results
                        prediction_result['anomaly_score'] = ae_result['anomaly_score']
                        # VAE uses ELBO-based scoring (Reconstruction + KL Divergence)
                        raw_score = ae_result['anomaly_score']
                        
                        # VAE score distribution (observed):
                        # - Safe data: ~2-5 (low reconstruction error)
                        # - Failure data: ~50-200+ (high reconstruction error)
                        # Use threshold-based normalization
                        if raw_score < 10.0:
                            # Safe range: map 0-10 to 0-0.3
                            norm_score = min(0.3, raw_score / 33.0)
                        else:
                            # Failure range: map 10+ to 0.3-1.0
                            # Adjusted divisor from 100.0 to 400.0 to prevent saturation
                            # This allows raw scores up to ~290 to be mapped to < 1.0
                            norm_score = min(1.0, 0.3 + (raw_score - 10.0) / 400.0)
                        
                        prediction_result['anomaly_score_normalized'] = norm_score
                        
                        logger.info(f"🔍 VAE Debug - Raw ELBO: {raw_score:.4f}, Norm Score: {norm_score:.4f}")
                        
                        prediction_result['reconstruction_errors'] = ae_result.get('reconstruction_errors', {})
                        prediction_result['shap_values'] = ae_result.get('shap_values', {})
                        prediction_result['model_type'] = 'vae'
                        
                        # Hybrid risk: 40% RF, 60% VAE (balanced approach)
                        rf_prob = prediction_result.get('failure_probability', 0)
                        vae_score = prediction_result['anomaly_score_normalized']
                        
                        hybrid_risk = (0.4 * rf_prob * 100) + (0.6 * vae_score * 100)
                        prediction_result['risk_percent'] = round(hybrid_risk, 1)
                        
                        logger.info(f"⚖️ Hybrid Risk - RF: {rf_prob:.4f}, VAE: {vae_score:.4f} -> Final: {prediction_result['risk_percent']:.2f}%")
                        
                    except Exception as e:
                        logger.error(f"VAE scoring failed: {e}")
                        # Fallback
                        if 'risk_percent' not in prediction_result:
                            prediction_result['risk_percent'] = round(prediction_result['failure_probability'] * 100, 1)
                else:
                    logger.warning("VAE requested but not loaded")
                    # Fallback
                    if 'risk_percent' not in prediction_result:
                        prediction_result['risk_percent'] = round(prediction_result['failure_probability'] * 100, 1)
            
            # Dense Autoencoder (Default)
            else:
                if is_autoencoder_loaded():
                    try:
                        scorer = get_anomaly_scorer()
                        ae_result = scorer.score(prediction_request.input_data, return_details=True)
                        
                        # Add autoencoder results to prediction
                        prediction_result['anomaly_score'] = ae_result['anomaly_score']
                        prediction_result['anomaly_score_normalized'] = ae_result['anomaly_score_normalized']
                        prediction_result['reconstruction_errors'] = ae_result.get('reconstruction_errors', {})
                        prediction_result['shap_values'] = ae_result.get('shap_values', {}) # Ensure SHAP values are passed
                        prediction_result['model_type'] = 'dense_ae'
                        
                        # Calculate hybrid risk score (RF + AE)
                        rf_prob = prediction_result['failure_probability']
                        ae_score = ae_result['anomaly_score_normalized']
                        
                        # Hybrid risk: 50% RF, 50% AE
                        hybrid_risk = (0.5 * rf_prob * 100) + (0.5 * ae_score * 100)
                        prediction_result['risk_percent'] = round(hybrid_risk, 1)
                        
                        logger.info(f"Deep learning enabled: AE score={ae_score:.3f}, Hybrid risk={hybrid_risk:.1f}%")
                        
                    except Exception as e:
                        logger.error(f"Autoencoder scoring failed: {e}")
                        # Fall back to RF-only risk
                        if 'risk_percent' not in prediction_result:
                            prediction_result['risk_percent'] = round(prediction_result['failure_probability'] * 100, 1)
                else:
                    logger.warning("Deep learning requested but autoencoder not loaded")
                    # Fall back to RF-only
                    if 'risk_percent' not in prediction_result:
                        prediction_result['risk_percent'] = round(prediction_result['failure_probability'] * 100, 1)

            # RUL Prediction (Separate from Ensemble)
            try:
                rul_model = get_rul_model()
                from app.ml.model_loader import get_rul_scaler
                rul_scaler = get_rul_scaler()
                
                if rul_model and rul_scaler:
                    # RUL model was trained on 18 features (standard CMAPSS subset)
                    # Excluded sensors: 1, 5, 10, 16, 18, 19
                    # Included: settings 1-3, sensors 2, 3, 4, 6, 7, 8, 9, 11, 12, 13, 14, 15, 17, 20, 21
                    
                    # Extract the 18 features in correct order
                    features_18 = []
                    # Settings (3)
                    features_18.extend([prediction_request.input_data.get(f'setting_{i}', 0) for i in range(1, 4)])
                    # Sensors (15): 2, 3, 4, 6, 7, 8, 9, 11, 12, 13, 14, 15, 17, 20, 21
                    included_sensors = [2, 3, 4, 6, 7, 8, 9, 11, 12, 13, 14, 15, 17, 20, 21]
                    features_18.extend([prediction_request.input_data.get(f'sensor_{i}', 0) for i in included_sensors])
                    
                    # Convert to array
                    feat_array_18 = np.array(features_18).reshape(1, -1)
                    
                    # Scale using the proper RUL scaler (MinMaxScaler fit on CMAPSS data)
                    scaled_feat_18 = rul_scaler.transform(feat_array_18)
                    
                    logger.info(f"RUL Input (scaled, first 5): {scaled_feat_18[0][:5]}")
                    
                    # Create sequence of length 30 by repeating the current point
                    # This is a simplification - ideally we'd use historical data
                    sequence = np.repeat(scaled_feat_18, 30, axis=0).reshape(1, 30, 18)
                    
                    # Predict
                    with torch.no_grad():
                        tensor_in = torch.FloatTensor(sequence)
                        rul_pred = rul_model(tensor_in)
                        raw_rul_value = rul_pred.item()
                        
                        logger.info(f"🔍 RUL Debug - Raw Model Output: {raw_rul_value}")
                        
                        # Cap RUL at reasonable limits (e.g. 0 to 130)
                        rul_value = max(0, min(raw_rul_value, 130))
                        
                        prediction_result['rul_prediction'] = rul_value
                        logger.info(f"⏳ RUL Prediction: {rul_value:.1f} cycles (Raw: {raw_rul_value:.4f})")
                else:
                    if not rul_model:
                        logger.warning("RUL model not loaded")
                    if not rul_scaler:
                        logger.warning("RUL scaler not loaded")
            except Exception as e:
                logger.error(f"RUL prediction failed: {e}", exc_info=True)
        
        # CRITICAL FIX: Update the main 'probability' field to reflect the final hybrid risk
        # This ensures the history table (which uses 'probability') matches the modal (which uses 'risk_percent')
        if 'risk_percent' in prediction_result:
            prediction_result['probability'] = prediction_result['risk_percent'] / 100.0
            # Also update the binary prediction label based on the new risk
            # Must be a string to match Pydantic model
            prediction_result['prediction'] = 'PRONE TO FAILURE' if prediction_result['risk_percent'] > 50 else 'SAFE'
        
        # Optionally create telemetry record
        telemetry_id = None
        if prediction_request.source in ['ui', 'manual']:
            # Define known columns in telemetry table
            known_columns = {
                'engine_id', 'timestamp', 'time_cycles', 'source', 'metadata',
                'setting_1', 'setting_2', 'setting_3',
                'sensor_2', 'sensor_3', 'sensor_4', 'sensor_7', 'sensor_9',
                'sensor_11', 'sensor_12', 'sensor_14', 'sensor_17', 'sensor_20', 'sensor_21'
            }
            
            # Prepare data for insertion
            insert_data = {
                'engine_id': prediction_request.engine_id,
                'timestamp': datetime.now().isoformat(),
                'source': prediction_request.source,
                'metadata': {}
            }
            
            # Distribute input data to columns or metadata
            for key, value in prediction_request.input_data.items():
                if key in known_columns:
                    insert_data[key] = value
                else:
                    # Store extra sensors (1, 5, 6, 8, etc.) in metadata
                    insert_data['metadata'][key] = value
            
            try:
                telemetry_response = supabase.table('telemetry').insert(insert_data).execute()
                if telemetry_response.data:
                    telemetry_id = telemetry_response.data[0]['id']
            except Exception as e:
                logger.error(f"Failed to save telemetry: {e}")
                # Continue without telemetry ID (don't block prediction)
        
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
                "created_by": user.id,
                # Deep learning fields
                "anomaly_score": prediction_result.get("anomaly_score"),
                "reconstruction_errors": prediction_result.get("reconstruction_errors")
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
            anomaly_score_normalized=prediction_data.get('anomaly_score_normalized'),
            correlated_anomalies=prediction_data.get('correlated_anomalies'),
            rul_prediction=prediction_data.get('rul_prediction'),
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

