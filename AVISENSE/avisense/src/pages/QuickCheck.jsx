import React, { useState } from 'react';
import { Thermometer, Activity, Droplet, Gauge, Wind, AlertCircle, RotateCw, Hash, Clock, Cpu } from 'lucide-react';
import FormInput from '../components/FormInput';
import ResultCard from '../components/ResultCard';
import ModelInfo from '../components/ModelInfo';
import { predictSafety } from '../services/api';
import styles from './QuickCheck.module.css';

const QuickCheck = () => {
    const [formData, setFormData] = useState({
        engine_id: '',
        timestamp: new Date().toISOString().slice(0, 16),
        setting_1: '',
        setting_2: '',
        setting_3: '',
        sensor_2: '',
        sensor_3: '',
        sensor_4: '',
        sensor_7: '',
        sensor_9: '',
        sensor_11: '',
        sensor_12: '',
        sensor_14: '',
        sensor_17: '',
        sensor_20: '',
        sensor_21: ''
    });

    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState(null);
    const [error, setError] = useState(null);

    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({ ...prev, [name]: value }));
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError(null);
        setResult(null);

        try {
            // Convert numeric fields
            const payload = { ...formData };
            const numericFields = [
                'setting_1', 'setting_2', 'setting_3',
                'sensor_2', 'sensor_3', 'sensor_4', 'sensor_7', 'sensor_9',
                'sensor_11', 'sensor_12', 'sensor_14', 'sensor_17', 'sensor_20', 'sensor_21'
            ];

            numericFields.forEach(field => {
                if (payload[field]) payload[field] = parseFloat(payload[field]);
            });

            const response = await predictSafety(payload);
            setResult(response);
        } catch (err) {
            setError('Failed to get prediction. Please try again.');
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className={styles.page}>
            <div className={styles.header}>
                <div>
                    <h1 className={styles.title}>Engine <span>Safety</span> Check</h1>
                    <p className={styles.subtitle}>Enter telemetry data for instant safety analysis.</p>
                </div>
            </div>

            <div className={styles.content}>
                <div className={styles.formSection}>
                    <form onSubmit={handleSubmit} className={styles.form}>
                        <div className={styles.sectionHeader}>
                            <Hash size={18} className={styles.icon} />
                            <h2 className={styles.sectionTitle}>Telemetry Input</h2>
                        </div>

                        <div className={styles.grid}>
                            <FormInput
                                label="Engine ID"
                                name="engine_id"
                                value={formData.engine_id}
                                onChange={handleChange}
                                icon={Hash}
                                required
                                placeholder="e.g. ENG-123"
                            />
                            <FormInput
                                label="Timestamp"
                                name="timestamp"
                                type="datetime-local"
                                value={formData.timestamp}
                                onChange={handleChange}
                                icon={Clock}
                                required
                            />
                        </div>

                        <div className={styles.divider}></div>

                        <div className={styles.sectionHeader}>
                            <Wind size={18} className={styles.icon} />
                            <h3 className={styles.sectionSubtitle}>Operational Settings</h3>
                        </div>

                        <div className={styles.grid}>
                            <FormInput
                                label="Setting 1 (Altitude) - Normalized"
                                name="setting_1"
                                type="number"
                                value={formData.setting_1}
                                onChange={handleChange}
                                icon={Gauge}
                                required
                                step="0.0001"
                            />
                            <FormInput
                                label="Setting 2 (Mach Number) - Normalized"
                                name="setting_2"
                                type="number"
                                value={formData.setting_2}
                                onChange={handleChange}
                                icon={Wind}
                                required
                                step="0.0001"
                            />
                            <FormInput
                                label="Setting 3 (Throttle Resolver Angle) - °"
                                name="setting_3"
                                type="number"
                                value={formData.setting_3}
                                onChange={handleChange}
                                icon={Activity}
                                required
                                step="0.1"
                            />
                        </div>

                        <div className={styles.divider}></div>

                        <div className={styles.sectionHeader}>
                            <Thermometer size={18} className={styles.icon} />
                            <h3 className={styles.sectionSubtitle}>Temperature Sensors</h3>
                        </div>

                        <div className={styles.grid}>
                            <FormInput
                                label="LPC Outlet Temperature (°R)"
                                name="sensor_2"
                                type="number"
                                value={formData.sensor_2}
                                onChange={handleChange}
                                icon={Thermometer}
                                required
                                step="0.1"
                            />
                            <FormInput
                                label="HPC Outlet Temperature (°R)"
                                name="sensor_3"
                                type="number"
                                value={formData.sensor_3}
                                onChange={handleChange}
                                icon={Thermometer}
                                required
                                step="0.1"
                            />
                            <FormInput
                                label="LPT Outlet Temperature (°R)"
                                name="sensor_4"
                                type="number"
                                value={formData.sensor_4}
                                onChange={handleChange}
                                icon={Thermometer}
                                required
                                step="0.1"
                            />
                            <FormInput
                                label="Fan Inlet Temperature (°R)"
                                name="sensor_7"
                                type="number"
                                value={formData.sensor_7}
                                onChange={handleChange}
                                icon={Thermometer}
                                required
                                step="0.1"
                            />
                        </div>

                        <div className={styles.divider}></div>

                        <div className={styles.sectionHeader}>
                            <Gauge size={18} className={styles.icon} />
                            <h3 className={styles.sectionSubtitle}>Pressure & Speed Sensors</h3>
                        </div>

                        <div className={styles.grid}>
                            <FormInput
                                label="Physical Core Speed - RPM"
                                name="sensor_9"
                                type="number"
                                value={formData.sensor_9}
                                onChange={handleChange}
                                icon={RotateCw}
                                required
                                step="0.1"
                            />
                            <FormInput
                                label="HPC Static Pressure - psia"
                                name="sensor_11"
                                type="number"
                                value={formData.sensor_11}
                                onChange={handleChange}
                                icon={Gauge}
                                required
                                step="0.01"
                            />
                            <FormInput
                                label="Fuel Flow to Ps30 Ratio - pps/psi"
                                name="sensor_12"
                                type="number"
                                value={formData.sensor_12}
                                onChange={handleChange}
                                icon={Droplet}
                                required
                                step="0.001"
                            />
                            <FormInput
                                label="Corrected Fan Speed - RPM"
                                name="sensor_14"
                                type="number"
                                value={formData.sensor_14}
                                onChange={handleChange}
                                icon={RotateCw}
                                required
                                step="0.1"
                            />
                            <FormInput
                                label="Total Pressure at HPC Outlet - psia"
                                name="sensor_17"
                                type="number"
                                value={formData.sensor_17}
                                onChange={handleChange}
                                icon={Gauge}
                                required
                                step="0.01"
                            />
                            <FormInput
                                label="Fuel Flow Ratio - pps/psi"
                                name="sensor_20"
                                type="number"
                                value={formData.sensor_20}
                                onChange={handleChange}
                                icon={Droplet}
                                required
                                step="0.001"
                            />
                            <FormInput
                                label="HPT Coolant Bleed - %"
                                name="sensor_21"
                                type="number"
                                value={formData.sensor_21}
                                onChange={handleChange}
                                icon={Wind}
                                required
                                step="0.01"
                            />
                        </div>

                        <div className={styles.actions}>
                            <button
                                type="submit"
                                className={`btn btn-primary ${styles.submitBtn}`}
                                disabled={loading}
                            >
                                {loading ? 'Analyzing...' : 'INITIATE ANALYSIS'}
                            </button>
                        </div>
                    </form>
                </div>

                <div className={styles.resultSection}>
                    <ModelInfo />

                    {error && (
                        <div className={styles.errorBanner}>
                            <AlertCircle size={20} />
                            <span>{error}</span>
                        </div>
                    )}
                    {result ? (
                        <ResultCard result={result} />
                    ) : (
                        <div className={styles.placeholder}>
                            <Activity size={48} className={styles.placeholderIcon} />
                            <p>AWAITING TELEMETRY DATA</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default QuickCheck;
