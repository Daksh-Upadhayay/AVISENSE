import numpy as np
from typing import Dict
from app.ml.model_loader import get_model, get_scaler, get_model_info
from app.ml.anomaly import detect_anomalies
import logging

logger = logging.getLogger(__name__)


async def run_prediction(input_data: Dict[str, float]) -> Dict:
    """
    Run ML prediction on input data.
    
    Args:
        input_data: Dictionary with sensor and setting values
        
    Returns:
        Dictionary with prediction results
    """
    try:
        model = get_model()
        scaler = get_scaler()
        model_info = get_model_info()
        
        # Extract features in correct order
        feature_names = model_info['feature_names']
        features = [input_data[feat] for feat in feature_names]
        
        # Convert to numpy array and reshape
        X = np.array(features).reshape(1, -1)
        
        # Scale features
        X_scaled = scaler.transform(X)
        
        # Make prediction
        prediction_class = model.predict(X_scaled)[0]
        probabilities = model.predict_proba(X_scaled)[0]
        
        # Check for anomalies to override model if necessary
        anomalies = detect_anomalies(input_data)
        high_severity_count = len([a for a in anomalies if a['severity'] == 'high'])
        
        # Safety Override: If multiple high severity anomalies, force FAILURE prediction
        if high_severity_count >= 2 and prediction_class == 0:
            logger.warning(f"⚠️ Safety Override: {high_severity_count} high severity anomalies detected. Forcing FAILURE.")
            prediction_class = 1
            # Boost failure probability to at least 85%
            probabilities[1] = max(probabilities[1], 0.85)
            probabilities[0] = 1.0 - probabilities[1]
        
        # Determine prediction label
        prediction_label = "PRONE TO FAILURE" if prediction_class == 1 else "SAFE"
        
        # --- Explainability & Risk Scoring ---
        from app.ml.explainability import explainability_engine
        
        # Calculate SHAP values
        shap_data = explainability_engine.calculate_shap_values(input_data)
        
        # Detect correlated anomalies
        correlated_anomalies = explainability_engine.detect_correlated_anomalies(anomalies)
        
        # Calculate Unified Risk Score
        risk_percent = explainability_engine.calculate_risk_score(
            probabilities[1], 
            anomalies, 
            shap_data
        )
        
        # Get recommended actions
        actions = get_recommended_actions(prediction_class, probabilities[1])
        
        result = {
            'prediction': prediction_label,
            'probability': float(probabilities[1]),  # Failure probability
            'confidence': float(max(probabilities)),
            'safe_probability': float(probabilities[0]),
            'failure_probability': float(probabilities[1]),
            'actions': actions,
            'anomalies': anomalies,
            'shap': shap_data,
            'risk_percent': risk_percent,
            'correlated_anomalies': correlated_anomalies,
            'model_version': model_info.get('version', 'v1.0.0'),
            'model_type': model_info.get('model_type', 'RandomForestClassifier')
        }
        
        logger.info(f"Prediction: {prediction_label} (probability: {probabilities[1]:.3f})")
        
        return result
        
    except Exception as e:
        logger.error(f"Prediction failed: {e}")
        raise


def get_recommended_actions(prediction: int, failure_prob: float) -> str:
    """
    Get recommended actions based on prediction result.
    
    Args:
        prediction: 0 for SAFE, 1 for FAILURE
        failure_prob: Probability of failure (0-1)
        
    Returns:
        Recommended action string
    """
    if prediction == 1:  # Failure predicted
        if failure_prob > 0.9:
            return "CRITICAL: Ground aircraft immediately. Perform comprehensive engine inspection."
        elif failure_prob > 0.7:
            return "HIGH RISK: Schedule immediate maintenance. Reduce engine load until inspection."
        else:
            return "MODERATE RISK: Schedule inspection within 24 hours. Monitor closely."
    else:  # Safe
        if failure_prob > 0.3:
            return "CAUTION: Engine is safe but showing early degradation signs. Schedule preventive maintenance."
        else:
            return "NORMAL: Continue routine monitoring. Next scheduled maintenance as planned."
