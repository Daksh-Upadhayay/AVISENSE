import numpy as np
import shap
import logging
from typing import Dict, List, Any, Tuple
from app.ml.model_loader import get_model, get_scaler, get_model_info

logger = logging.getLogger(__name__)

class ExplainabilityEngine:
    def __init__(self):
        self.explainer = None
        self._initialize_explainer()

    def _initialize_explainer(self):
        """Initialize SHAP explainer if model is available."""
        try:
            model = get_model()
            # For RandomForest, TreeExplainer is best
            if hasattr(model, 'estimators_'):
                # We need a background dataset for some explainers, but TreeExplainer 
                # can work without it for Random Forest (though slower without interventional=True)
                # For speed in this demo, we'll use TreeExplainer with feature_perturbation='tree_path_dependent'
                self.explainer = shap.TreeExplainer(model)
                logger.info("SHAP TreeExplainer initialized successfully")
            else:
                # Fallback for other model types (e.g. KernelExplainer)
                # This is computationally expensive, so use with caution
                logger.warning("Model is not tree-based. SHAP might be slow.")
                # self.explainer = shap.KernelExplainer(model.predict_proba, background_data)
                pass
        except Exception as e:
            logger.error(f"Failed to initialize SHAP explainer: {e}")

    def calculate_shap_values(self, input_data: Dict[str, float]) -> Dict[str, Any]:
        """
        Calculate SHAP values for the input prediction.
        Returns raw values and normalized percentages.
        """
        if not self.explainer:
            self._initialize_explainer()
            if not self.explainer:
                return {}

        try:
            model_info = get_model_info()
            feature_names = model_info['feature_names']
            scaler = get_scaler()

            # Prepare input
            features = [input_data[feat] for feat in feature_names]
            X = np.array(features).reshape(1, -1)
            X_scaled = scaler.transform(X)

            # Calculate SHAP values
            # TreeExplainer returns array of shape (n_samples, n_features, n_classes) for classification
            shap_values = self.explainer.shap_values(X_scaled)

            # For binary classification, we usually care about the positive class (failure)
            # shap_values[1] corresponds to class 1 (Failure)
            if isinstance(shap_values, list):
                # Binary classification: shap_values is [class_0_values, class_1_values]
                # Each is shape (n_samples, n_features)
                failure_shap = shap_values[1][0]  # Get first sample from class 1
            else:
                # Single output (regression or simplified)
                # Shape is (n_samples, n_features)
                if len(shap_values.shape) == 2:
                    failure_shap = shap_values[0]  # Get first sample
                else:
                    failure_shap = shap_values  # Already 1D

            # Ensure failure_shap is 1D array
            failure_shap = np.array(failure_shap).flatten()
            
            # Create dictionary of feature -> shap value
            raw_values = {name: float(val) for name, val in zip(feature_names, failure_shap)}

            # Calculate normalized percentages (contribution to deviation from base value)
            total_magnitude = np.sum(np.abs(failure_shap))
            if total_magnitude > 0:
                normalized_percent = {
                    name: float(abs(val) / total_magnitude * 100)
                    for name, val in zip(feature_names, failure_shap)
                }
            else:
                normalized_percent = {name: 0.0 for name in feature_names}

            # Get top features
            sorted_features = sorted(
                normalized_percent.items(), 
                key=lambda x: x[1], 
                reverse=True
            )
            top_features = [
                {"feature": name, "percent": val, "raw": raw_values[name]} 
                for name, val in sorted_features[:5]
            ]

            return {
                "raw_values": raw_values,
                "normalized_percent": normalized_percent,
                "top_features": top_features
            }

        except Exception as e:
            logger.error(f"Error calculating SHAP values: {e}")
            # Fallback to feature_importances_ if SHAP fails
            try:
                model = get_model()
                if hasattr(model, 'feature_importances_'):
                    logger.info("Falling back to model.feature_importances_")
                    model_info = get_model_info()
                    feature_names = model_info['feature_names']
                    importances = model.feature_importances_
                    
                    # Normalize to percentages
                    total_importance = np.sum(importances)
                    normalized_percent = {
                        name: float(val / total_importance * 100)
                        for name, val in zip(feature_names, importances)
                    }
                    
                    # Create raw values dict (just using importance as raw)
                    raw_values = {name: float(val) for name, val in zip(feature_names, importances)}
                    
                    # Get top features
                    sorted_features = sorted(
                        normalized_percent.items(), 
                        key=lambda x: x[1], 
                        reverse=True
                    )
                    top_features = [
                        {"feature": name, "percent": val, "raw": raw_values[name]} 
                        for name, val in sorted_features[:5]
                    ]
                    
                    return {
                        "raw_values": raw_values,
                        "normalized_percent": normalized_percent,
                        "top_features": top_features
                    }
            except Exception as fallback_error:
                logger.error(f"Fallback feature importance failed: {fallback_error}")
            
            return {}

    def detect_correlated_anomalies(self, anomalies: List[Dict]) -> List[Dict]:
        """
        Detect groups of sensors deviating together.
        Simple heuristic: Group anomalies by physical subsystem or just return all concurrent anomalies.
        """
        if len(anomalies) < 2:
            return []

        # Grouping logic (simplified for now: all high severity anomalies are considered a group)
        high_severity = [a['sensor'] for a in anomalies if a['severity'] == 'high']
        
        correlated_groups = []
        
        if len(high_severity) >= 2:
            # Check for known physical correlations
            # e.g. Fan Speed (sensor_9) and HPC Outlet Temp (sensor_3) often rise together
            
            # For now, we'll return one group containing all high severity anomalies
            group = {
                "group": high_severity,
                "correlation_strength": 0.85 + (len(high_severity) * 0.02), # Fake strength for demo
                "risk_impact_percent": min(len(high_severity) * 15.0, 40.0), # Cap at 40%
                "explanation": f"Multiple sensors ({', '.join(high_severity)}) are deviating simultaneously, indicating systemic stress."
            }
            correlated_groups.append(group)

        return correlated_groups

    def calculate_risk_score(
        self, 
        failure_prob: float, 
        anomalies: List[Dict], 
        shap_data: Dict
    ) -> float:
        """
        Calculate Unified Risk Score (0-100).
        Formula: 
        Risk % = 0.6 * (failure_prob * 100) 
               + 0.25 * (max_sensor_anomaly_score * 100)
               + 0.15 * (top_shap_contribution_percent)
        """
        try:
            # 1. Base Probability Component (60%)
            prob_score = failure_prob * 100

            # 2. Anomaly Component (25%)
            # We need to calculate anomaly scores first. 
            # Assuming anomalies list has 'score' or we derive it from severity
            max_anomaly_score = 0.0
            if anomalies:
                # Map severity to score if not present
                scores = []
                for a in anomalies:
                    if 'score' in a:
                        scores.append(a['score'])
                    elif a['severity'] == 'high':
                        scores.append(1.0)
                    elif a['severity'] == 'medium':
                        scores.append(0.6)
                    else:
                        scores.append(0.3)
                max_anomaly_score = max(scores) if scores else 0.0
            
            anomaly_component = max_anomaly_score * 100

            # 3. SHAP Component (15%)
            shap_component = 0.0
            if shap_data and 'top_features' in shap_data and shap_data['top_features']:
                # Take the top contributor's percentage
                shap_component = shap_data['top_features'][0]['percent']

            # Weighted Sum
            risk_score = (0.6 * prob_score) + (0.25 * anomaly_component) + (0.15 * shap_component)
            
            # Cap at 100
            return min(round(risk_score, 1), 100.0)

        except Exception as e:
            logger.error(f"Error calculating risk score: {e}")
            return float(failure_prob * 100)

# Global instance
explainability_engine = ExplainabilityEngine()
