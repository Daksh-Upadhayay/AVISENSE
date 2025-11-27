import pytest
from app.ml.predictor import run_prediction, get_recommended_actions


@pytest.mark.asyncio
async def test_run_prediction_safe():
    """Test prediction for a safe engine."""
    input_data = {
        'setting_1': 0.0007,
        'setting_2': 0.0004,
        'setting_3': 100.0,
        'sensor_2': 642.5,
        'sensor_3': 1589.7,
        'sensor_4': 1400.6,
        'sensor_7': 554.4,
        'sensor_9': 2388.0,
        'sensor_11': 47.5,
        'sensor_12': 521.7,
        'sensor_14': 2388.1,
        'sensor_17': 392.0,
        'sensor_20': 38.9,
        'sensor_21': 23.4
    }
    
    result = await run_prediction(input_data)
    
    assert 'prediction' in result
    assert 'probability' in result
    assert 'confidence' in result
    assert result['prediction'] in ['SAFE', 'PRONE TO FAILURE']
    assert 0 <= result['probability'] <= 1
    assert 0 <= result['confidence'] <= 1


def test_recommended_actions_critical():
    """Test recommended actions for critical failure."""
    actions = get_recommended_actions(1, 0.95)
    assert "CRITICAL" in actions
    assert "Ground aircraft" in actions


def test_recommended_actions_high_risk():
    """Test recommended actions for high risk."""
    actions = get_recommended_actions(1, 0.75)
    assert "HIGH RISK" in actions
    assert "immediate maintenance" in actions


def test_recommended_actions_safe():
    """Test recommended actions for safe engine."""
    actions = get_recommended_actions(0, 0.1)
    assert "NORMAL" in actions
    assert "routine monitoring" in actions
