import React, { useState, useEffect } from 'react';
import { Save, Bell, Server } from 'lucide-react';
import FormInput from '../components/FormInput';
import styles from './Settings.module.css';

const Settings = () => {
    const [config, setConfig] = useState({
        apiUrl: '/api/predict',
        enableAlerts: false,
        alertContacts: ''
    });
    const [saved, setSaved] = useState(false);

    useEffect(() => {
        const savedConfig = localStorage.getItem('avisense_config');
        if (savedConfig) {
            setConfig(JSON.parse(savedConfig));
        }
    }, []);

    const handleChange = (e) => {
        const { name, value, type, checked } = e.target;
        setConfig(prev => ({
            ...prev,
            [name]: type === 'checkbox' ? checked : value
        }));
        setSaved(false);
    };

    const handleSubmit = (e) => {
        e.preventDefault();
        localStorage.setItem('avisense_config', JSON.stringify(config));
        setSaved(true);
        setTimeout(() => setSaved(false), 3000);
    };

    return (
        <div className={styles.page}>
            <div className={styles.header}>
                <h1 className={styles.title}>System Settings</h1>
                <p className={styles.subtitle}>Configure integration and notification preferences.</p>
            </div>

            <div className={styles.container}>
                <form onSubmit={handleSubmit} className={styles.form}>
                    <div className={styles.section}>
                        <div className={styles.sectionHeader}>
                            <Server size={20} className={styles.icon} />
                            <h2 className={styles.sectionTitle}>API Integration</h2>
                        </div>
                        <FormInput
                            label="Backend API Endpoint"
                            name="apiUrl"
                            value={config.apiUrl}
                            onChange={handleChange}
                            placeholder="https://api.example.com/predict"
                            required
                        />
                    </div>

                    <div className={styles.section}>
                        <div className={styles.sectionHeader}>
                            <Bell size={20} className={styles.icon} />
                            <h2 className={styles.sectionTitle}>Notifications</h2>
                        </div>

                        <div className={styles.checkboxGroup}>
                            <label className={styles.checkboxLabel}>
                                <input
                                    type="checkbox"
                                    name="enableAlerts"
                                    checked={config.enableAlerts}
                                    onChange={handleChange}
                                    className={styles.checkbox}
                                />
                                Enable Automatic Alerts
                            </label>
                            <p className={styles.helperText}>Send alerts when "Prone to Failure" is predicted.</p>
                        </div>

                        {config.enableAlerts && (
                            <FormInput
                                label="Alert Contacts (Email/SMS)"
                                name="alertContacts"
                                value={config.alertContacts}
                                onChange={handleChange}
                                placeholder="tech@airline.com, +15550123"
                                icon={Bell}
                            />
                        )}
                    </div>

                    <div className={styles.actions}>
                        <button type="submit" className="btn btn-primary">
                            <Save size={18} style={{ marginRight: '8px' }} />
                            {saved ? 'Saved!' : 'Save Settings'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default Settings;
