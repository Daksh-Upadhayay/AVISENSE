import numpy as np
import torch
import pandas as pd
import logging
from app.ml.model_loader import (
    get_classifier_model, get_classifier_scaler,
    get_rul_model, get_rul_scaler,
    get_risk_config, get_model_info,
    get_anomaly_scorer, is_autoencoder_loaded
)
from app.config import settings

logger = logging.getLogger(__name__)

def set_deterministic_seeds(seed=42):
    """Set seeds for reproducibility."""
    import random
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.use_deterministic_algorithms(True, warn_only=True)

async def run_deterministic_inference(input_data: dict, source: str = "api"):
    """
    Run deterministic inference pipeline.
    
    Steps:
    1. Set seeds.
    2. Preprocess input (using saved scalers).
    3. Run Classifier (Calibrated).
    4. Run RUL Model.
    5. Run Anomaly Detection.
    6. Calculate Risk %.
    7. Map to Label.
    8. Sanity Checks.
    """
    # 1. Set Seeds
    # Use seed from config or default
    risk_config = get_risk_config()
    seed = 42 # Default
    if risk_config:
        # We might want to store seed in risk config or training config
        pass
    set_deterministic_seeds(seed)
    
    results = {
        "input_data": input_data,
        "source": source,
        "created_at": pd.Timestamp.now().isoformat(),
        "model_version": "v2.0.0" # Should come from metadata
    }
    
    try:
        # Load Artifacts
        clf_model = get_classifier_model()
        clf_scaler = get_classifier_scaler()
        rul_model = get_rul_model()
        rul_scaler = get_rul_scaler()
        model_info = get_model_info()
        
        results["model_version"] = model_info.get("version", "unknown")
        
        # 2. Preprocess Input
        # Convert dict to array in correct order
        features = model_info.get("features", [])
        if not features:
            # Fallback if features not in metadata
            logger.warning("Features list not found in metadata, using default order")
            # ... (define default order) ...
            pass
            
        # Extract features for Classifier
        # Assuming Classifier uses same features as RUL (or subset)
        # In training script, we used 'feature_cols' for both.
        input_vector = np.array([input_data.get(f, 0) for f in features]).reshape(1, -1)
        
        # Scale for Classifier
        input_scaled_cls = clf_scaler.transform(input_vector)
        
        # 3. Run Classifier
        # Returns [prob_safe, prob_failure]
        probs = clf_model.predict_proba(input_scaled_cls)[0]
        failure_prob = probs[1]
        results["failure_probability"] = float(failure_prob)
        results["safe_probability"] = float(probs[0])
        
        # 4. Run RUL Model
        # Scale for RUL
        # RUL model expects sequence (1, 30, 17)
        # We repeat the current input 30 times
        input_scaled_rul = rul_scaler.transform(input_vector)
        sequence = np.repeat(input_scaled_rul, 30, axis=0).reshape(1, 30, -1)
        
        with torch.no_grad():
            tensor_in = torch.FloatTensor(sequence)
            rul_pred = rul_model(tensor_in).item()
            
        # Cap RUL
        rul_cap = risk_config['normalization']['rul_cap'] if risk_config else 125.0
        rul_value = max(0, min(rul_pred, rul_cap))
        results["rul_prediction"] = float(rul_value)
        
        # 5. Run Anomaly Detection (VAE/AE)
        # TODO: Re-enable with proper integration in Step F (Explainability)
        # Current issue: Dimension mismatch between input and VAE model
        anomaly_score = 0.0
        norm_anomaly = 0.0
        results["anomalies"] = []
        
        # DISABLED TEMPORARILY
        # if is_autoencoder_loaded():
        #     scorer = get_anomaly_scorer()
        #     ae_result = scorer.score(input_data, return_details=True)
        #     anomaly_score = ae_result['anomaly_score']
        #     if anomaly_score < 10.0:
        #         norm_anomaly = min(0.05, anomaly_score / 200.0)
        #     else:
        #         norm_anomaly = min(1.0, 0.5 + (anomaly_score - 10.0) / 200.0)
        #     results["anomaly_score"] = float(anomaly_score)
        #     results["anomaly_score_normalized"] = float(norm_anomaly)
        #     results["anomalies"] = ae_result.get("anomalies", [])
            
        # 6. Calculate Risk %
        # Formula: w_clf * prob + w_anom * score + w_rul * (1 - norm_rul)
        w_clf = risk_config['weights']['classifier']
        w_anom = risk_config['weights']['anomaly']
        w_rul = risk_config['weights']['rul']
        
        norm_rul = min(rul_value, rul_cap) / rul_cap
        
        risk_score = (
            w_clf * failure_prob +
            w_anom * norm_anomaly +
            w_rul * (1.0 - norm_rul)
        ) * 100.0
        
        results["risk_percent"] = round(risk_score, 2)
        
        # 7. Map to Label
        # Deterministic Mapping
        # SAFE if prob < p_safe_thresh AND risk < risk_safe_thresh
        p_safe_thresh = risk_config['thresholds']['safe_probability']
        risk_safe_thresh = risk_config['thresholds']['risk_safe']
        risk_prone_thresh = risk_config['thresholds']['risk_prone']
        
        if failure_prob < p_safe_thresh and risk_score < risk_safe_thresh:
            prediction = "SAFE"
        elif risk_score >= risk_prone_thresh:
            prediction = "PRONE TO FAILURE"
        else:
            # In between (e.g. prob safe but risk moderate)
            # Default to conservative
            prediction = "PRONE TO FAILURE" if failure_prob >= 0.5 else "SAFE"
            
        results["prediction"] = prediction
        results["probability"] = results["risk_percent"] / 100.0 # Align probability with risk
        
        # 8. Sanity Checks (Guards)
        assert 0.0 <= results["failure_probability"] <= 1.0, "Failure probability out of bounds"
        assert 0.0 <= results["risk_percent"] <= 100.0, "Risk percent out of bounds"
        assert results["rul_prediction"] >= 0, "Negative RUL"
        
        # 9. Explainability (Simple Contribution)
        # For now, return feature importances * input values
        # TODO: Integrate SHAP
        results["shap_values"] = {} 
        
        return results
        
    except Exception as e:
        logger.error(f"Inference failed: {e}", exc_info=True)
        raise
