import React from 'react';
// eslint-disable-next-line no-unused-vars
import { motion } from 'framer-motion';

export function RULGauge({ rul, maxRul = 130, size = 200 }) {
    const radius = size * 0.4;
    const circumference = 2 * Math.PI * radius;
    // Cap RUL for display
    const displayRul = Math.min(Math.max(rul, 0), maxRul);
    const progress = displayRul / maxRul;
    const strokeDashoffset = circumference - progress * circumference;

    // Determine color based on RUL (Low RUL is bad)
    const getColor = (value) => {
        if (value > 50) return '#10B981'; // Green (Safe)
        if (value > 20) return '#F59E0B'; // Yellow (Warning)
        return '#EF4444'; // Red (Critical)
    };

    const color = getColor(displayRul);

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
                    className="flex flex-col items-center"
                >
                    <span className="text-4xl font-bold text-white">
                        {Math.round(displayRul)}
                    </span>
                    <span className="text-xs font-medium text-gray-400 uppercase tracking-wider mt-1">
                        Cycles
                    </span>
                </motion.div>
            </div>
        </div>
    );
}
