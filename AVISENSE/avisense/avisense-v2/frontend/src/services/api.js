const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export async function predictEngine(engineId, inputData, token) {
    const response = await fetch(`${API_BASE_URL}/predict`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
            engine_id: engineId,
            input_data: inputData,
            source: 'ui',
        }),
    })

    if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Prediction failed')
    }

    return response.json()
}

export async function checkHealth() {
    const response = await fetch(`${API_BASE_URL}/health`)

    if (!response.ok) {
        throw new Error('Health check failed')
    }

    return response.json()
}
