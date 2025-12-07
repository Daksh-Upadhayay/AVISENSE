import React from 'react';
import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    ReferenceLine,
    Area,
    AreaChart
} from 'recharts';
import { format } from 'date-fns';

// Custom tooltip
const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
        const data = payload[0].payload;
        return (
            <div className="bg-dark-surface/95 backdrop-blur-md p-3 rounded-lg shadow-xl border border-white/10">
                <p className="text-xs text-gray-400 mb-1">{data.displayTime}</p>
                <p className="text-sm font-semibold text-primary-400">
                    Anomaly: {data.isRaw
                        ? data.anomalyScore.toFixed(2)
                        : `${(data.anomalyScore * 100).toFixed(1)}%`}
                </p>
                <p className="text-xs text-gray-300">
                    Risk: {data.riskPercent}%
                </p>
                <p className={`text-xs font-medium mt-1 ${data.prediction === 'SAFE' ? 'text-green-400' : 'text-red-400'}`}>
                    {data.prediction === 'SAFE' ? '✓ Healthy' : '⚠ Failure Risk'}
                </p>
            </div>
        );
    }
    return null;
};

export function TemporalAnomalyChart({ predictions, threshold = 0.5 }) {
    if (!predictions || predictions.length === 0) {
        return (
            <div className="flex items-center justify-center h-64 bg-gray-50 rounded-lg border border-gray-200">
                <p className="text-gray-400">No prediction history available</p>
            </div>
        );
    }

    // Transform predictions into chart data
    const chartData = predictions
        .map(pred => {
            // Prefer normalized score if available, otherwise use raw score
            // If raw score is used and it's > 1, treat it as raw value (not percentage)
            const rawScore = pred.anomaly_score || 0;
            const normalizedScore = pred.anomaly_score_normalized;

            // Determine what to show
            // If we have normalized score, use it (0-1 range)
            // If not, and raw score is small (<1), assume it's normalized-ish
            // If raw score is large (>1), it's a raw ELBO score
            const isRaw = normalizedScore === undefined && rawScore > 1.0;
            const displayScore = normalizedScore !== undefined ? normalizedScore : rawScore;

            return {
                timestamp: new Date(pred.created_at).getTime(),
                displayTime: format(new Date(pred.created_at), 'MMM dd, HH:mm'),
                anomalyScore: displayScore,
                isRaw: isRaw,
                prediction: pred.prediction,
                // Use the explicit risk_percent if available, otherwise fallback to failure_probability
                riskPercent: pred.risk_percent !== undefined
                    ? pred.risk_percent
                    : (pred.failure_probability * 100).toFixed(1)
            };
        })
        .sort((a, b) => a.timestamp - b.timestamp);



    return (
        <div className="w-full glass-card p-6 mb-6">
            <div className="flex items-center justify-between mb-6">
                <div>
                    <h3 className="text-lg font-semibold text-white">Anomaly Trend Analysis</h3>
                    <p className="text-sm text-dark-muted">Real-time monitoring of engine health degradation</p>
                </div>
                <div className="flex items-center gap-2 text-xs text-dark-muted">
                    <span className="flex items-center gap-1">
                        <span className="w-2 h-2 rounded-full bg-primary-500"></span>
                        Score
                    </span>
                    <span className="flex items-center gap-1">
                        <span className="w-2 h-2 rounded-full bg-red-500"></span>
                        Threshold
                    </span>
                </div>
            </div>

            <div className="h-[300px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                    <AreaChart
                        data={chartData}
                        margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
                    >
                        <defs>
                            <linearGradient id="anomalyGradient" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                            </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.05)" />
                        <XAxis
                            dataKey="displayTime"
                            tick={{ fontSize: 11, fill: '#64748b' }}
                            stroke="rgba(255,255,255,0.1)"
                            tickLine={false}
                            axisLine={false}
                            dy={10}
                        />
                        <YAxis
                            domain={[0, 1]}
                            tick={{ fontSize: 11, fill: '#64748b' }}
                            stroke="rgba(255,255,255,0.1)"
                            tickLine={false}
                            axisLine={false}
                            tickFormatter={(value) => value > 1 ? value.toFixed(0) : `${(value * 100).toFixed(0)}%`}
                        />
                        <Tooltip content={<CustomTooltip />} cursor={{ stroke: 'rgba(255,255,255,0.1)', strokeWidth: 1 }} />
                        <ReferenceLine
                            y={threshold}
                            stroke="#ef4444"
                            strokeDasharray="3 3"
                            strokeOpacity={0.5}
                        />
                        <Area
                            type="monotone"
                            dataKey="anomalyScore"
                            stroke="#3b82f6"
                            strokeWidth={2}
                            fill="url(#anomalyGradient)"
                            dot={false}
                            activeDot={{ r: 6, fill: '#3b82f6', stroke: '#fff', strokeWidth: 2 }}
                            animationDuration={1000}
                        />
                    </AreaChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
}
