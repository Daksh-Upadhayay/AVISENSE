import React, { useState } from 'react';
import { CheckCircle, AlertTriangle, ChevronDown, ChevronUp, Activity } from 'lucide-react';
import styles from './ResultCard.module.css';

const ResultCard = ({ result }) => {
    if (!result) return null;

    const { prediction, probability, actions, top_features } = result;
    const isSafe = prediction.toLowerCase() === 'safe';

    return (
        <div className={`${styles.card} ${isSafe ? styles.safe : styles.danger}`}>
            <div className={styles.header}>
                <div className={styles.statusBadge}>
                    {isSafe ? <CheckCircle size={32} /> : <AlertTriangle size={32} />}
                    <span className={styles.statusText}>
                        {isSafe ? 'SAFE' : 'PRONE TO FAILURE'}
                    </span>
                </div>
            </div>

            <div className={styles.actions}>
                <h4 className={styles.sectionTitle}>
                    {isSafe ? 'Suggested Actions' : 'Fault Diagnosis & Actions'}
                </h4>
                <p className={styles.actionText}>{actions || 'No specific actions required.'}</p>

                {!isSafe && top_features && top_features.length > 0 && (
                    <div className={styles.faultAnalysis}>
                        <h5 className={styles.subTitle}>Detected Anomalies:</h5>
                        <ul className={styles.faultList}>
                            {top_features.slice(0, 5).map((feature, index) => (
                                <li key={index} className={styles.faultItem}>
                                    <Activity size={14} className={styles.faultIcon} />
                                    <span>{feature.description || `High deviation in ${feature.name}`}</span>
                                </li>
                            ))}
                        </ul>
                    </div>
                )}
            </div>
        </div>
    );
};

export default ResultCard;
