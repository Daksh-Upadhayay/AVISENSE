import React, { useEffect, useState } from 'react';
import { Cpu, Database, Activity } from 'lucide-react';
import styles from './ModelInfo.module.css';

const API_BASE_URL = 'http://localhost:5001';

const ModelInfo = () => {
    const [info, setInfo] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchInfo = async () => {
            try {
                const response = await fetch(`${API_BASE_URL}/model-info`);
                if (response.ok) {
                    const data = await response.json();
                    setInfo(data);
                }
            } catch (error) {
                console.error('Failed to fetch model info:', error);
            } finally {
                setLoading(false);
            }
        };

        fetchInfo();
    }, []);

    if (loading) return <div className={styles.container}>Loading System Specs...</div>;
    if (!info) return null;

    return (
        <div className={styles.container}>
            <div className={styles.header}>
                <div className={styles.title}>
                    <Cpu size={16} />
                    SYSTEM_CORE // MODEL_SPECS
                </div>
                <div className={styles.status}>
                    <div className={styles.statusDot}></div>
                    ONLINE
                </div>
            </div>

            <div className={styles.grid}>
                <div className={styles.item}>
                    <span className={styles.label}>Architecture</span>
                    <span className={styles.value}>Random Forest Classifier</span>
                </div>
            </div>

            <div className={styles.metrics}>
                <div className={styles.metric}>
                    <span className={styles.metricValue}>{(info.safe_recall * 100).toFixed(1)}%</span>
                    <span className={styles.metricLabel}>SAFE RECALL</span>
                </div>
                <div className={styles.metric}>
                    <span className={styles.metricValue}>{(info.failure_recall * 100).toFixed(1)}%</span>
                    <span className={styles.metricLabel}>FAILURE RECALL</span>
                </div>
            </div>
        </div>
    );
};

export default ModelInfo;
