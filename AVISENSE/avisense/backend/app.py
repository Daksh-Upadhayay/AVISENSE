from flask import Flask, request, jsonify
from flask_cors import CORS
import joblib
import numpy as np
import pandas as pd
from datetime import datetime

app = Flask(__name__)
CORS(app)  # Enable CORS for React frontend

# Load model and scaler
print("Loading C-MAPSS model...")
model = joblib.load('../avisense_model_cmapss.joblib')
scaler = joblib.load('../avisense_scaler_cmapss.joblib')
model_info = joblib.load('../avisense_model_cmapss_info.joblib')

print(f"Model loaded: {model_info['model_type']}")
print(f"Features: {model_info['feature_names']}")
print(f"Safe Recall: {model_info['safe_recall']:.1%}")
print(f"Failure Recall: {model_info['failure_recall']:.1%}")

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'model': model_info['model_type'],
        'dataset': model_info['dataset'],
        'safe_recall': model_info['safe_recall'],
        'failure_recall': model_info['failure_recall']
    })

@app.route('/predict', methods=['POST'])
def predict():
    """
    Predict engine failure probability
    
    Expected input JSON:
    {
        "setting_1": float,
        "setting_2": float,
        "setting_3": float,
        "sensor_2": float,
        "sensor_3": float,
        "sensor_4": float,
        "sensor_7": float,
        "sensor_9": float,
        "sensor_11": float,
        "sensor_12": float,
        "sensor_14": float,
        "sensor_20": float,
        "sensor_21": float,
        "engine_id": string (optional)
    }
    """
    try:
        data = request.json
        
        # Extract features in correct order
        feature_names = model_info['feature_names']
        features = []
        
        for feat in feature_names:
            if feat not in data:
                return jsonify({
                    'error': f'Missing required field: {feat}',
                    'required_fields': feature_names
                }), 400
            features.append(float(data[feat]))
        
        # Convert to numpy array and reshape
        X = np.array(features).reshape(1, -1)
        
        # Scale features
        X_scaled = scaler.transform(X)
        
        # Make prediction
        prediction = model.predict(X_scaled)[0]
        probabilities = model.predict_proba(X_scaled)[0]
        
        # Prepare response
        result = {
            'prediction': 'PRONE TO FAILURE' if prediction == 1 else 'SAFE',
            'probability': float(probabilities[1]),  # Probability of failure
            'confidence': float(max(probabilities)),
            'safe_probability': float(probabilities[0]),
            'failure_probability': float(probabilities[1]),
            'timestamp': datetime.now().isoformat(),
            'engine_id': data.get('engine_id', 'unknown'),
            'actions': get_recommended_actions(prediction, probabilities[1])
        }
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({
            'error': str(e),
            'message': 'Prediction failed'
        }), 500

def get_recommended_actions(prediction, failure_prob):
    """Get recommended actions based on prediction"""
    if prediction == 1:  # Failure predicted
        if failure_prob > 0.9:
            return 'CRITICAL: Ground aircraft immediately. Perform comprehensive engine inspection.'
        elif failure_prob > 0.7:
            return 'HIGH RISK: Schedule immediate maintenance. Reduce engine load until inspection.'
        else:
            return 'MODERATE RISK: Schedule inspection within 24 hours. Monitor closely.'
    else:  # Safe
        if failure_prob > 0.3:
            return 'CAUTION: Engine is safe but showing early degradation signs. Schedule preventive maintenance.'
        else:
            return 'NORMAL: Continue routine monitoring. Next scheduled maintenance as planned.'

@app.route('/diagnostics', methods=['GET'])
def get_diagnostics():
    """
    Get time-series diagnostics data for an engine
    
    Query parameters:
        engine_id: string (optional) - Engine identifier
        days: int (optional) - Number of days of history (default: 30)
    """
    try:
        engine_id = request.args.get('engine_id', 'ENG-123')
        days = int(request.args.get('days', 30))
        num_points = min(days, 30)  # Cap at 30 data points
        
        # Generate realistic time-series data based on C-MAPSS sensor patterns
        # We'll create data with gradual trends and realistic variations
        
        # Base values (typical C-MAPSS ranges)
        base_temp = 220  # LPT temperature (sensor_4 range: ~200-250°C)
        base_rpm = 7200  # Physical fan speed (sensor_11 range: ~7000-7500)
        base_vibration = 0.015  # HPC outlet pressure normalized (0.01-0.03)
        base_oil_pressure = 42  # Typical oil pressure (40-45 PSI)
        
        # Create degradation trend (engine degrades over time)
        # Use engine_id as seed for consistency
        import hashlib
        seed = int(hashlib.md5(engine_id.encode()).hexdigest(), 16) % 10000
        np.random.seed(seed)
        
        data = []
        for i in range(num_points):
            # Calculate days ago
            days_ago = num_points - i - 1
            timestamp = datetime.now()
            timestamp = timestamp.replace(hour=12, minute=0, second=0, microsecond=0)
            from datetime import timedelta
            timestamp = timestamp - timedelta(days=days_ago)
            
            # Add gradual degradation trend (increases over time)
            degradation_factor = i / num_points  # 0 to 1
            
            # Temperature increases with degradation
            temp = base_temp + (degradation_factor * 15) + np.random.normal(0, 3)
            
            # RPM varies slightly
            rpm = base_rpm + (degradation_factor * 200) + np.random.normal(0, 50)
            
            # Vibration increases with degradation
            vibration = base_vibration + (degradation_factor * 0.01) + np.random.normal(0, 0.002)
            
            # Oil pressure decreases slightly with degradation
            oil_pressure = base_oil_pressure - (degradation_factor * 2) + np.random.normal(0, 0.5)
            
            data.append({
                'timestamp': timestamp.isoformat(),
                'temperature': round(float(temp), 2),
                'rpm': round(float(rpm), 0),
                'vibration': round(float(vibration), 4),
                'oilPressure': round(float(oil_pressure), 2)
            })
        
        return jsonify(data)
    
    except Exception as e:
        return jsonify({
            'error': str(e),
            'message': 'Failed to retrieve diagnostics data'
        }), 500

@app.route('/model-info', methods=['GET'])
def get_model_info():
    """Get model information"""
    return jsonify(model_info)

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 Avisense C-MAPSS Prediction API")
    print("="*60)
    print(f"Model: {model_info['model_type']}")
    print(f"Dataset: {model_info['dataset']}")
    print(f"Safe Recall: {model_info['safe_recall']:.1%}")
    print(f"Failure Recall: {model_info['failure_recall']:.1%}")
    print("="*60)
    print("\nStarting Flask server on http://localhost:5001")
    print("Endpoints:")
    print("  - GET  /health       - Health check")
    print("  - POST /predict      - Make prediction")
    print("  - GET  /diagnostics  - Get time-series diagnostics data")
    print("  - GET  /model-info   - Get model details")
    print("\n")
    
    app.run(debug=True, port=5001)
