import React, { useState } from 'react';
import { Modal } from '../ui/Modal';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { api } from '../../lib/api';
import { Activity, Zap, BarChart2, AlertTriangle, Brain } from 'lucide-react';
import { ExplainabilityDashboard } from './ExplainabilityDashboard';

const REQUIRED_FEATURES = [
    'setting_1', 'setting_2', 'setting_3',
    'sensor_1', 'sensor_2', 'sensor_3', 'sensor_4', 'sensor_5', 'sensor_6',
    'sensor_7', 'sensor_8', 'sensor_9', 'sensor_10', 'sensor_11', 'sensor_12',
    'sensor_13', 'sensor_14', 'sensor_15', 'sensor_16', 'sensor_17', 'sensor_18',
    'sensor_19', 'sensor_20', 'sensor_21'
];

export function MakePredictionModal({ isOpen, onClose, engineId, onPredictionComplete }) {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [formData, setFormData] = useState({});
    const [result, setResult] = useState(null); // Store result locally for display
    const [useDeep, setUseDeep] = useState(false); // Toggle for deep learning
    const [modelFamily, setModelFamily] = useState('dense_ae'); // Model selection

    // ... existing functions ...

    const handleChange = (name, value) => {
        setFormData(prev => ({ ...prev, [name]: parseFloat(value) || 0 }));
    };

    const fillSafeData = () => {
        // Real healthy sample extracted from data/processed/train.npz
        // This is an actual data point from a healthy engine in the C-MAPSS dataset
        // Increased noise for more variety each time
        const noise = () => (Math.random() - 0.5) * 0.2; // Increased from 0.05 to 0.2

        const safeData = {
            setting_1: 0.0005 + (Math.random() * 0.0002), // Doubled range
            setting_2: -0.0003 + (Math.random() * 0.0002), // Doubled range
            setting_3: 100.0, // Constant
            sensor_1: 518.67, // Constant
            sensor_2: 642.33 + noise() * 2, // More variation
            sensor_3: 1591.38 + noise() * 5, // More variation
            sensor_4: 1400.36 + noise() * 5, // More variation
            sensor_5: 14.62, // Constant
            sensor_6: 21.61, // Low variance
            sensor_7: 554.96 + noise() * 2, // More variation
            sensor_8: 2388.04 + noise() * 10, // More variation
            sensor_9: 9050.97 + noise() * 10, // More variation
            sensor_10: 1.30, // Constant
            sensor_11: 47.25 + noise() * 0.5, // More variation
            sensor_12: 521.92 + noise() * 2, // More variation
            sensor_13: 2388.07 + noise() * 10, // More variation
            sensor_14: 8129.70 + noise() * 10, // More variation
            sensor_15: 8.4148 + noise() * 0.2, // More variation
            sensor_16: 0.03, // Constant
            sensor_17: 392.0 + Math.floor(Math.random() * 4), // More variation (0-3)
            sensor_18: 2388.0, // Constant
            sensor_19: 100.0, // Constant
            sensor_20: 39.02 + noise() * 0.3, // More variation
            sensor_21: 23.50 + noise() * 0.3, // More variation
        };
        setFormData(safeData);
    };

    const fillFailureData = () => {
        // Generate data that exceeds thresholds to trigger failure prediction
        // Increased random noise so each click generates noticeably different values
        const noise = () => (Math.random() - 0.5) * 10; // Increased from 5 to 10

        console.log("Generating failure data with noise...");

        const failureData = {
            setting_1: 0.0035 + (Math.random() * 0.002),  // More variation
            setting_2: 0.001 + (Math.random() * 0.0006),  // More variation
            setting_3: 100.0,
            sensor_1: 518.67,  // Constant
            sensor_2: 648.0 + noise() * 2,    // Much higher than max 643.68
            sensor_3: 1625.0 + noise() * 10,  // Much higher than max 1602.79
            sensor_4: 1455.0 + noise() * 10,  // Much higher than max 1426.93
            sensor_5: 14.62,  // Constant
            sensor_6: 21.61,  // Low variance
            sensor_7: 562.0 + noise() * 2,    // Much higher than max 555.14
            sensor_8: 2388.04 + noise() * 0.5,
            sensor_9: 9250.0 + noise() * 30,  // Much higher than max 9109.41
            sensor_10: 1.30,  // Constant
            sensor_11: 50.5 + noise() * 0.8,  // Much higher than max 48.08
            sensor_12: 528.0 + noise() * 2,   // Much higher than max 522.89
            sensor_13: 2388.07 + noise() * 0.5,
            sensor_14: 8280.0 + noise() * 30, // Much higher than max 8181.91
            sensor_15: 8.4148 + noise() * 0.1,
            sensor_16: 0.03,  // Constant
            sensor_17: 405.0 + Math.floor(noise() * 3),  // Much higher than max 396.31
            sensor_18: 2388.0,  // Constant
            sensor_19: 100.0,  // Constant
            sensor_20: 41.5 + noise() * 0.3,  // Much higher than max 39.18
            sensor_21: 25.0 + noise() * 0.2,  // Much higher than max 23.51
        };
        console.log("Generated data:", failureData);
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
                source: 'ui',
                use_deep: true,      // Enforced
                model_family: 'vae' // VAE is primary deep learning model
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
        <Modal isOpen={isOpen} onClose={handleClose} title="Make Prediction" maxWidth="max-w-[75vw]">
            <div className="space-y-6 max-h-[90vh] overflow-y-auto pr-2">
                {/* Result Display */}
                {result && (
                    <div className="p-4 rounded-lg bg-dark-surface border border-white/10 animate-fade-in">
                        <ExplainabilityDashboard predictionResult={result} />
                        <div className="flex justify-end pt-4 sticky bottom-0 bg-dark-bg/95 backdrop-blur py-4 border-t border-white/10">
                            <Button onClick={handleClose} variant="primary">
                                Close Analysis
                            </Button>
                        </div>
                    </div>
                )}

                <form onSubmit={handleSubmit} className="space-y-6">
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
                        <Button type="button" variant="secondary" size="sm" onClick={fillSafeData}>
                            <Zap className="w-4 h-4 mr-2" />
                            Fill Safe Data
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
            </div>
        </Modal>
    );
}
