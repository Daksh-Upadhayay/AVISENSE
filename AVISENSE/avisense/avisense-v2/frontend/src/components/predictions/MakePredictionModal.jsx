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

    // ... existing functions ...

    const handleChange = (name, value) => {
        setFormData(prev => ({ ...prev, [name]: parseFloat(value) || 0 }));
    };

    const fillSafeData = () => {
        // Real healthy sample extracted from data/processed/train.npz
        // This is an actual data point from a healthy engine in the C-MAPSS dataset
        // Increased noise for more variety each time
        const noise = () => (Math.random() - 0.5) * 2.0; // Increased noise significantly (was 0.2)

        const safeData = {
            setting_1: -0.0000 + noise() * 0.002,
            setting_2: 0.0000 + noise() * 0.0005,
            setting_3: 100.0,
            sensor_1: 518.67,
            sensor_2: 642.41 + noise() * 0.5,
            sensor_3: 1587.40 + noise(),
            sensor_4: 1403.45 + noise(),
            sensor_5: 14.62,
            sensor_6: 21.61,
            sensor_7: 553.90 + noise() * 0.5,
            sensor_8: 2388.06 + noise() * 0.05,
            sensor_9: 9058.21 + noise() * 2,
            sensor_10: 1.30,
            sensor_11: 47.37 + noise() * 0.2,
            sensor_12: 521.86 + noise() * 0.5,
            sensor_13: 2388.06 + noise() * 0.05,
            sensor_14: 8139.16 + noise() * 2,
            sensor_15: 8.4206 + noise() * 0.02,
            sensor_16: 0.03,
            sensor_17: 392 + Math.floor(Math.random() * 3) - 1, // 391, 392, 393
            sensor_18: 2388.0,
            sensor_19: 100.0,
            sensor_20: 38.92 + noise() * 0.1,
            sensor_21: 23.35 + noise() * 0.1,
        };
        setFormData(safeData);
    };

    const fillFailureData = () => {
        // Generate data that matches actual failure conditions (RUL < 5)
        // Based on analysis of training data
        // significantly increased noise to ensure variety
        const noise = () => (Math.random() - 0.5) * 5.0;

        console.log("Generating failure data with noise...");

        const failureData = {
            setting_1: -0.0001 + noise() * 0.002,
            setting_2: -0.0000 + noise() * 0.0005,
            setting_3: 100.0,
            sensor_1: 518.67,
            sensor_2: 643.68 + noise() * 0.8,
            sensor_3: 1602.39 + noise() * 3,
            sensor_4: 1428.86 + noise() * 3,
            sensor_5: 14.62,
            sensor_6: 21.61,
            sensor_7: 551.51 + noise() * 0.8,
            sensor_8: 2388.23 + noise() * 0.1,
            sensor_9: 9099.40 + noise() * 10,
            sensor_10: 1.30,
            sensor_11: 48.14 + noise() * 0.3,
            sensor_12: 519.82 + noise() * 0.8,
            sensor_13: 2388.23 + noise() * 0.1,
            sensor_14: 8168.19 + noise() * 10,
            sensor_15: 8.5203 + noise() * 0.03,
            sensor_16: 0.03,
            sensor_17: 396 + Math.floor(Math.random() * 5) - 2, // Wider range
            sensor_18: 2388.0,
            sensor_19: 100.0,
            sensor_20: 38.45 + noise() * 0.2,
            sensor_21: 23.07 + noise() * 0.2,
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
        <Modal isOpen={isOpen} onClose={handleClose} title="Make Prediction" maxWidth="max-w-[70vw]">
            <div className="space-y-4 max-h-[85vh] overflow-y-auto pr-2">
                {/* Result Display */}
                {result && (
                    <div className="p-3 rounded-lg bg-dark-surface border border-white/10 animate-fade-in">
                        <ExplainabilityDashboard predictionResult={result} />
                        <div className="flex justify-end pt-3 sticky bottom-0 bg-dark-bg/95 backdrop-blur py-3 border-t border-white/10">
                            <Button onClick={handleClose} variant="primary">
                                Close Analysis
                            </Button>
                        </div>
                    </div>
                )}

                <form onSubmit={handleSubmit} className="space-y-4">
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

                    <div className="space-y-2">
                        <h3 className="text-xs font-medium text-primary-400 uppercase tracking-wider">Operational Settings</h3>
                        <div className="grid grid-cols-3 gap-2">
                            {['setting_1', 'setting_2', 'setting_3'].map(field => (
                                <div key={field}>
                                    <label className="block text-xs text-dark-muted mb-0.5">{field}</label>
                                    <input
                                        type="number"
                                        step="any"
                                        className="w-full bg-dark-surface border border-white/10 rounded px-2 py-1.5 text-white text-xs focus:border-primary-500 focus:outline-none"
                                        value={formData[field] || ''}
                                        onChange={(e) => handleChange(field, e.target.value)}
                                        required
                                    />
                                </div>
                            ))}
                        </div>
                    </div>

                    <div className="space-y-2">
                        <h3 className="text-xs font-medium text-primary-400 uppercase tracking-wider">Sensor Readings</h3>
                        <div className="grid grid-cols-4 gap-2">
                            {REQUIRED_FEATURES.filter(f => f.startsWith('sensor')).map(field => (
                                <div key={field}>
                                    <label className="block text-xs text-dark-muted mb-0.5">{field}</label>
                                    <input
                                        type="number"
                                        step="any"
                                        className="w-full bg-dark-surface border border-white/10 rounded px-2 py-1.5 text-white text-xs focus:border-primary-500 focus:outline-none"
                                        value={formData[field] || ''}
                                        onChange={(e) => handleChange(field, e.target.value)}
                                        required
                                    />
                                </div>
                            ))}
                        </div>
                    </div>

                    <div className="pt-3 flex justify-end gap-2">
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
