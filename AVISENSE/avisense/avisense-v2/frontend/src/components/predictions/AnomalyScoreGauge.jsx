import React from 'react';
// eslint-disable-next-line no-unused-vars
import { motion } from 'framer-motion';

export function AnomalyScoreGauge({ anomalyScore, size = 200 }) {
    const radius = size * 0.4;
    const circumference = 2 * Math.PI * radius;
    // Clamp score to 0-100
    const score = Math.min(Math.max(anomalyScore * 100, 0), 100);
    const strokeDashoffset = circumference - (score / 100) * circumference;

    // Determine color based on anomaly score
    const getColor = (s) => {
        if (s < 30) return '#10B981'; // Green (Low Anomaly)
        if (s < 60) return '#F59E0B'; // Yellow (Medium Anomaly)
        return '#EF4444'; // Red (High Anomaly)
    };

    const color = getColor(score);

    return (
        <div className="relative flex flex-col items-center justify-center" style={{ width: size, height: size }}>
            {/* Background Circle */}
            <svg width={size} height={size} className="transform -rotate-90">
                <circle
                    cx={size / 2}
                    cy={size / 2}
                    r={radius}
                    stroke="rgba(255,255,255,0.1)"
                    strokeWidth="12"
                    fill="transparent"
                />
                {/* Progress Circle */}
                <motion.circle
                    initial={{ strokeDashoffset: circumference }}
                    animate={{ strokeDashoffset }}
                    transition={{ duration: 1.5, ease: "easeOut" }}
                    cx={size / 2}
                    cy={size / 2}
                    r={radius}
                    stroke={color}
                    strokeWidth="12"
                    fill="transparent"
                    strokeDasharray={circumference}
                    strokeLinecap="round"
                />
            </svg>

            {/* Text Content */}
            <div className="absolute inset-0 flex flex-col items-center justify-center">
                <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.5 }}
                    className="text-4xl font-bold text-white"
                >
                    {score.toFixed(1)}
                </motion.div>
            </div>
        </div>
    );
}
