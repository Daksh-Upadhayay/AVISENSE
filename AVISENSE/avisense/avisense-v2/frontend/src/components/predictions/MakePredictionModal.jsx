import React, { useState } from 'react';
import { Modal } from '../ui/Modal';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { api } from '../../lib/api';
import { Activity, Zap, BarChart2, AlertTriangle } from 'lucide-react';
import { ExplainabilityDashboard } from './ExplainabilityDashboard';

const REQUIRED_FEATURES = [
    'setting_1', 'setting_2', 'setting_3',
    'sensor_2', 'sensor_3', 'sensor_4', 'sensor_7', 'sensor_9',
    'sensor_11', 'sensor_12', 'sensor_14', 'sensor_17', 'sensor_20', 'sensor_21'
];

export function MakePredictionModal({ isOpen, onClose, engineId, onPredictionComplete }) {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [formData, setFormData] = useState({});
    const [result, setResult] = useState(null); // Store result locally for display

    // ... existing functions ...

    const handleChange = (name, value) => {
        setFormData(prev => ({ ...prev, [name]: parseFloat(value) || 0 }));
    };

    const fillRandomData = () => {
        // Generate somewhat realistic random data based on C-MAPSS typical values
        const randomData = {
            setting_1: -0.0007 + (Math.random() * 0.005),
            setting_2: -0.0004 + (Math.random() * 0.001),
            setting_3: 100.0,
            sensor_2: 641.0 + (Math.random() * 2),
            sensor_3: 1580.0 + (Math.random() * 20),
            sensor_4: 1390.0 + (Math.random() * 20),
            sensor_7: 553.0 + (Math.random() * 2),
            sensor_9: 9040.0 + (Math.random() * 20),
            sensor_11: 47.0 + (Math.random() * 1),
            sensor_12: 521.0 + (Math.random() * 2),
            sensor_14: 8130.0 + (Math.random() * 20),
            sensor_17: 390 + Math.floor(Math.random() * 5),
            sensor_20: 38.0 + (Math.random() * 1),
            sensor_21: 23.0 + (Math.random() * 1),
        };
        setFormData(randomData);
    };

    const fillFailureData = () => {
        // Generate data that exceeds thresholds to trigger failure prediction
        const failureData = {
            setting_1: 0.002,
            setting_2: 0.0005,
            setting_3: 100.0,
            sensor_2: 645.0,    // Exceeds max 643.68
            sensor_3: 1610.0,   // Exceeds max 1602.79
            sensor_4: 1440.0,   // Exceeds max 1426.93
            sensor_7: 558.0,    // Exceeds max 555.14
            sensor_9: 9150.0,   // Exceeds max 9109.41
            sensor_11: 49.0,    // Exceeds max 48.08
            sensor_12: 525.0,   // Exceeds max 522.89
            sensor_14: 8200.0,  // Exceeds max 8181.91
            sensor_17: 400.0,   // Exceeds max 396.31
            sensor_20: 40.0,    // Exceeds max 39.18
            sensor_21: 24.0,    // Exceeds max 23.51
        };
        setFormData(failureData);
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError(null);
        setLoading(true);

        try {
            const response = await api.post('/predict', {
                engine_id: engineId,
                input_data: formData,
                source: 'ui'
            });

            setResult(response);
            onPredictionComplete(response);
            // Don't close immediately, show result
        } catch (err) {
            console.error('Prediction failed:', err);
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const handleClose = () => {
        setResult(null);
        setFormData({});
        onClose();
    };

    return (
        <Modal isOpen={isOpen} onClose={handleClose} title={result ? "Prediction Analysis" : "Run Failure Prediction"}>
            {result ? (
                <div className="space-y-6 max-h-[70vh] overflow-y-auto pr-2">
                    <ExplainabilityDashboard predictionResult={result} />
                    <div className="flex justify-end pt-4 sticky bottom-0 bg-dark-bg/95 backdrop-blur py-4 border-t border-white/10">
                        <Button onClick={handleClose} variant="primary">
                            Close Analysis
                        </Button>
                    </div>
                </div>
            ) : (
                <form onSubmit={handleSubmit} className="space-y-6">
                    {/* ... existing form content ... */}
                    {error && (
                        <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
                            {error}
                        </div>
                    )}

                    <div className="flex justify-end gap-2">
                        <Button type="button" variant="ghost" size="sm" onClick={fillFailureData} className="text-red-400 hover:bg-red-500/10">
                            <AlertTriangle className="w-4 h-4 mr-2" />
                            Fill Failure Data
                        </Button>
                        <Button type="button" variant="secondary" size="sm" onClick={fillRandomData}>
                            <Zap className="w-4 h-4 mr-2" />
                            Auto-Fill Test Data
                        </Button>
                    </div>

                    <div className="space-y-4">
                        <h3 className="text-sm font-medium text-primary-400 uppercase tracking-wider">Operational Settings</h3>
                        <div className="grid grid-cols-3 gap-3">
                            {['setting_1', 'setting_2', 'setting_3'].map(field => (
                                <div key={field}>
                                    <label className="block text-xs text-dark-muted mb-1">{field}</label>
                                    <input
                                        type="number"
                                        step="any"
                                        className="w-full bg-dark-surface border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:border-primary-500 focus:outline-none"
                                        value={formData[field] || ''}
                                        onChange={(e) => handleChange(field, e.target.value)}
                                        required
                                    />
                                </div>
                            ))}
                        </div>
                    </div>

                    <div className="space-y-4">
                        <h3 className="text-sm font-medium text-primary-400 uppercase tracking-wider">Sensor Readings</h3>
                        <div className="grid grid-cols-3 gap-3">
                            {REQUIRED_FEATURES.filter(f => f.startsWith('sensor')).map(field => (
                                <div key={field}>
                                    <label className="block text-xs text-dark-muted mb-1">{field}</label>
                                    <input
                                        type="number"
                                        step="any"
                                        className="w-full bg-dark-surface border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:border-primary-500 focus:outline-none"
                                        value={formData[field] || ''}
                                        onChange={(e) => handleChange(field, e.target.value)}
                                        required
                                    />
                                </div>
                            ))}
                        </div>
                    </div>

                    <div className="pt-4 flex justify-end gap-3">
                        <Button type="button" variant="ghost" onClick={handleClose}>
                            Cancel
                        </Button>
                        <Button type="submit" variant="primary" isLoading={loading}>
                            <Activity className="w-4 h-4" />
                            Run Prediction
                        </Button>
                    </div>
                </form>
            )}
        </Modal>
    );
}
