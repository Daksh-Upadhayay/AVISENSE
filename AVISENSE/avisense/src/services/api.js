// API service for C-MAPSS model predictions

const API_BASE_URL = 'http://localhost:5001';

export const predictSafety = async (data) => {
    try {
        const response = await fetch(`${API_BASE_URL}/predict`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.message || 'Prediction failed');
        }

        const result = await response.json();

        // Save to history
        const history = JSON.parse(localStorage.getItem('avisense_history') || '[]');
        history.unshift({ ...result, ...data });
        localStorage.setItem('avisense_history', JSON.stringify(history));

        // Transform to match frontend expectations
        return {
            prediction: result.prediction,
            probability: result.failure_probability,
            confidence: result.confidence,
            actions: result.actions,
            top_features: result.anomalies?.map(anomaly => ({
                name: anomaly.sensor_name || anomaly.sensor,
                contribution: anomaly.value,
                description: anomaly.description,
                severity: anomaly.severity
            })) || [],
            timestamp: result.timestamp,
            engine_id: result.engine_id
        };
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
};

export const getHistory = async () => {
    return new Promise((resolve) => {
        setTimeout(() => {
            const history = JSON.parse(localStorage.getItem('avisense_history') || '[]');
            resolve(history);
        }, 500);
    });
};

export const getDiagnosticsData = async (engineId, days = 30) => {
    try {
        const response = await fetch(`${API_BASE_URL}/diagnostics?engine_id=${engineId}&days=${days}`);

        if (!response.ok) {
            throw new Error('Failed to fetch diagnostics data');
        }

        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Diagnostics API Error:', error);
        // Return empty array on error instead of throwing
        return [];
    }
};

