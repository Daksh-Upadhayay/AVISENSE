import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import styles from './TimeSeriesChart.module.css';

const TimeSeriesChart = ({ data, title, dataKey, color = "#ff6b35", unit = "" }) => {
    return (
        <div className={styles.chartContainer}>
            <h3 className={styles.chartTitle}>{title}</h3>
            <div className={styles.chartWrapper}>
                <ResponsiveContainer width="100%" height="100%">
                    <LineChart
                        data={data}
                        margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                    >
                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                        <XAxis
                            dataKey="timestamp"
                            tick={{ fontSize: 12, fill: '#64748b' }}
                            tickFormatter={(val) => new Date(val).toLocaleDateString()}
                        />
                        <YAxis
                            tick={{ fontSize: 12, fill: '#64748b' }}
                            unit={unit}
                        />
                        <Tooltip
                            contentStyle={{
                                backgroundColor: '#fff',
                                border: '1px solid #e2e8f0',
                                borderRadius: '4px',
                                boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)'
                            }}
                            labelStyle={{ color: '#64748b', marginBottom: '4px' }}
                            labelFormatter={(val) => new Date(val).toLocaleString()}
                        />
                        <Line
                            type="monotone"
                            dataKey={dataKey}
                            stroke={color}
                            strokeWidth={2}
                            dot={{ r: 3, fill: color }}
                            activeDot={{ r: 6 }}
                        />
                    </LineChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
};

export default TimeSeriesChart;
