import pytest
from app.ml.anomaly import detect_anomalies


def test_detect_anomalies_none():
    """Test anomaly detection with normal values."""
    sensor_data = {
        'sensor_2': 642.5,
        'sensor_3': 1589.7,
        'sensor_4': 1400.6,
        'sensor_7': 554.4,
        'sensor_9': 9046.19,
        'sensor_11': 47.5,
        'sensor_12': 521.7,
        'sensor_14': 8138.62,
        'sensor_17': 392.0,
        'sensor_20': 38.9,
        'sensor_21': 23.4
    }
    
    anomalies = detect_anomalies(sensor_data)
    assert isinstance(anomalies, list)
    # Should have few or no anomalies for normal values
    assert len(anomalies) <= 2


def test_detect_anomalies_high_temp():
    """Test anomaly detection with high temperature."""
    sensor_data = {
        'sensor_2': 650.0,  # Above max threshold
        'sensor_3': 1589.7,
        'sensor_4': 1400.6,
        'sensor_7': 554.4,
        'sensor_9': 9046.19,
        'sensor_11': 47.5,
        'sensor_12': 521.7,
        'sensor_14': 8138.62,
        'sensor_17': 392.0,
        'sensor_20': 38.9,
        'sensor_21': 23.4
    }
    
    anomalies = detect_anomalies(sensor_data)
    assert len(anomalies) > 0
    
    # Check that sensor_2 anomaly is detected
    sensor_2_anomaly = next((a for a in anomalies if a['sensor'] == 'sensor_2'), None)
    assert sensor_2_anomaly is not None
    assert sensor_2_anomaly['severity'] in ['medium', 'high']


def test_anomaly_structure():
    """Test that anomaly objects have correct structure."""
    sensor_data = {
        'sensor_2': 650.0,
        'sensor_3': 1589.7
    }
    
    anomalies = detect_anomalies(sensor_data)
    
    if anomalies:
        anomaly = anomalies[0]
        assert 'sensor' in anomaly
        assert 'sensor_name' in anomaly
        assert 'value' in anomaly
        assert 'threshold' in anomaly
        assert 'threshold_min' in anomaly
        assert 'threshold_max' in anomaly
        assert 'severity' in anomaly
        assert 'description' in anomaly
