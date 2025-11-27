import json
from pathlib import Path
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

# Load sensor thresholds
THRESHOLDS_FILE = Path(__file__).parent.parent / "sensor_thresholds.json"
with open(THRESHOLDS_FILE, 'r') as f:
    SENSOR_THRESHOLDS = json.load(f)

# Sensor name mappings
SENSOR_NAMES = {
    'sensor_2': 'Total Temperature at Fan Inlet',
    'sensor_3': 'Total Temperature at LPC Outlet',
    'sensor_4': 'Total Temperature at HPC Outlet',
    'sensor_7': 'Total Pressure at HPC Outlet',
    'sensor_9': 'Physical Fan Speed',
    'sensor_11': 'Physical Core Speed',
    'sensor_12': 'Engine Pressure Ratio',
    'sensor_14': 'Corrected Fan Speed',
    'sensor_17': 'Corrected Core Speed',
    'sensor_20': 'Ratio of Fuel Flow to Ps30',
    'sensor_21': 'Corrected Fan Speed'
}


def detect_anomalies(sensor_data: Dict[str, float]) -> List[Dict]:
    """
    Detect sensor anomalies based on threshold violations.
    
    Args:
        sensor_data: Dictionary of sensor values
        
    Returns:
        List of anomaly dictionaries
    """
    anomalies = []
    
    for sensor, value in sensor_data.items():
        if sensor not in SENSOR_THRESHOLDS:
            continue
        
        thresholds = SENSOR_THRESHOLDS[sensor]
        min_threshold = thresholds['min']
        max_threshold = thresholds['max']
        std = thresholds['std']
        
        # Check if value is outside normal range
        if value < min_threshold:
            deviation = min_threshold - value
            # Score calculation: 0.5 (base anomaly) + scaled deviation
            # If deviation >= std, score -> 1.0
            score = min(0.5 + (deviation / (2 * std)), 1.0)
            
            # Determine severity based on distance from threshold
            severity = 'high' if value < (min_threshold - std) else 'medium'
            
            anomalies.append({
                'sensor': sensor,
                'sensor_name': SENSOR_NAMES.get(sensor, sensor),
                'value': round(float(value), 2),
                'threshold': f'below {min_threshold}',
                'threshold_min': min_threshold,
                'threshold_max': max_threshold,
                'severity': severity,
                'score': round(score, 2),
                'percent': round(score * 100, 1),
                'description': f"{SENSOR_NAMES.get(sensor, sensor)}: {value:.2f} (below min {min_threshold})"
            })
        elif value > max_threshold:
            deviation = value - max_threshold
            score = min(0.5 + (deviation / (2 * std)), 1.0)
            
            severity = 'high' if value > (max_threshold + std) else 'medium'
            
            anomalies.append({
                'sensor': sensor,
                'sensor_name': SENSOR_NAMES.get(sensor, sensor),
                'value': round(float(value), 2),
                'threshold': f'exceeds {max_threshold}',
                'threshold_min': min_threshold,
                'threshold_max': max_threshold,
                'severity': severity,
                'score': round(score, 2),
                'percent': round(score * 100, 1),
                'description': f"{SENSOR_NAMES.get(sensor, sensor)}: {value:.2f} (exceeds max {max_threshold})"
            })
    
    # Sort by severity (high first) and then by deviation magnitude
    anomalies.sort(
        key=lambda x: (
            0 if x['severity'] == 'high' else 1,
            -abs(x['value'] - ((x['threshold_min'] + x['threshold_max']) / 2))
        )
    )
    
    logger.info(f"Detected {len(anomalies)} anomalies")
    
    return anomalies
