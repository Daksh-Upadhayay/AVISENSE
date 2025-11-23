import requests
import json

url = "http://localhost:5001/predict"

# Base "Safe" values
base_data = {
    "engine_id": "TEST-FAIL-FINDER",
    "timestamp": "2025-11-23T12:00:00",
    "setting_1": 0.0007,
    "setting_2": 0.0004,
    "setting_3": 100.0,
    "sensor_2": 642.5,
    "sensor_3": 1589.7,
    "sensor_4": 1400.6,
    "sensor_7": 554.4,
    "sensor_9": 2388.0,
    "sensor_11": 47.5,
    "sensor_12": 521.7,
    "sensor_14": 2388.1,
    "sensor_17": 392.0,
    "sensor_20": 38.9,
    "sensor_21": 23.4
}

# Try to degrade the engine by increasing temps and decreasing pressures
# We will iterate to find a failure point

print("Searching for failure vector...")

for i in range(0, 50):
    # Degrade factor
    factor = i * 0.5
    
    test_data = base_data.copy()
    
    # Increase temperatures (Sensors 2, 3, 4)
    test_data["sensor_2"] += factor * 0.5
    test_data["sensor_3"] += factor * 1.0
    test_data["sensor_4"] += factor * 1.0
    
    # Decrease pressures (Sensors 7, 11, 12, 20, 21)
    test_data["sensor_7"] -= factor * 0.5
    test_data["sensor_11"] -= factor * 0.1
    test_data["sensor_12"] -= factor * 0.5
    test_data["sensor_20"] -= factor * 0.1
    test_data["sensor_21"] -= factor * 0.1
    
    try:
        response = requests.post(url, json=test_data)
        result = response.json()
        
        print(f"Iteration {i}: Prediction = {result['prediction']}, Probability = {result['probability']:.4f}")
        
        if result['prediction'].lower() != 'safe':
            print("\nFOUND FAILURE VECTOR!")
            print(json.dumps(test_data, indent=2))
            break
    except Exception as e:
        print(f"Error: {e}")

