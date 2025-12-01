import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';

/**
 * Reconstruction Error Chart
 * 
 * Displays per-feature reconstruction errors from the autoencoder
 * Shows which sensors contributed most to the anomaly score
 */
export function ReconstructionErrorChart({ reconstructionErrors }) {
    if (!reconstructionErrors || Object.keys(reconstructionErrors).length === 0) {
        return (
            <div className="flex items-center justify-center h-48 text-dark-muted">
                <p>No reconstruction error data available</p>
            </div>
        );
    }

    // Convert to array and sort by percent contribution
    const data = Object.entries(reconstructionErrors)
        .map(([feature, data]) => ({
            feature: feature.replace('_', ' ').toUpperCase(),
            percent: data.percent || 0,
            error: data.error || 0
        }))
        .sort((a, b) => b.percent - a.percent)
        .slice(0, 10); // Top 10

    // Color based on contribution
    const getColor = (percent) => {
        if (percent > 15) return '#ef4444'; // red
        if (percent > 8) return '#f59e0b';  // yellow
        return '#10b981'; // green
    };

    const CustomTooltip = ({ active, payload }) => {
        if (active && payload && payload.length) {
            const data = payload[0].payload;
            return (
                <div className="bg-dark-surface border border-white/10 rounded-lg p-3 shadow-lg">
                    <p className="text-white font-semibold">{data.feature}</p>
                    <p className="text-sm text-dark-muted mt-1">
                        Contribution: <span className="text-white">{data.percent.toFixed(2)}%</span>
                    </p>
                    <p className="text-sm text-dark-muted">
                        Error: <span className="text-white">{data.error.toFixed(4)}</span>
                    </p>
                </div>
            );
        }
        return null;
    };

    return (
        <div className="w-full h-64">
            <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data} layout="vertical" margin={{ top: 5, right: 30, left: 80, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                    <XAxis
                        type="number"
                        stroke="rgba(255,255,255,0.5)"
                        tick={{ fill: 'rgba(255,255,255,0.7)', fontSize: 12 }}
                        label={{ value: 'Contribution (%)', position: 'insideBottom', offset: -5, fill: 'rgba(255,255,255,0.7)' }}
                    />
                    <YAxis
                        type="category"
                        dataKey="feature"
                        stroke="rgba(255,255,255,0.5)"
                        tick={{ fill: 'rgba(255,255,255,0.7)', fontSize: 11 }}
                        width={75}
                    />
                    <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(255,255,255,0.05)' }} />
                    <Bar dataKey="percent" radius={[0, 4, 4, 0]}>
                        {data.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={getColor(entry.percent)} />
                        ))}
                    </Bar>
                </BarChart>
            </ResponsiveContainer>
        </div>
    );
}
