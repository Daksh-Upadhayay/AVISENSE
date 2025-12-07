import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';
import { format } from 'date-fns';

export function RULTimeline({ data }) {
    if (!data || data.length === 0) {
        return (
            <div className="flex items-center justify-center h-64 bg-gray-800/50 rounded-lg border border-gray-700">
                <span className="text-gray-400">No RUL history available</span>
            </div>
        );
    }

    // Format data for chart
    const chartData = data.map(item => ({
        ...item,
        date: new Date(item.created_at),
        formattedDate: format(new Date(item.created_at), 'MMM d, HH:mm'),
        rul: Math.round(item.rul_prediction)
    })).sort((a, b) => a.date - b.date);

    return (
        <div className="h-64 w-full bg-gray-800/30 rounded-lg p-4 border border-gray-700/50">
            <h3 className="text-sm font-medium text-gray-300 mb-4">RUL History</h3>
            <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" vertical={false} />
                    <XAxis
                        dataKey="formattedDate"
                        stroke="#9CA3AF"
                        fontSize={10}
                        tickLine={false}
                        axisLine={false}
                    />
                    <YAxis
                        stroke="#9CA3AF"
                        fontSize={10}
                        tickLine={false}
                        axisLine={false}
                        label={{ value: 'Cycles', angle: -90, position: 'insideLeft', style: { fill: '#9CA3AF', fontSize: 10 } }}
                    />
                    <Tooltip
                        contentStyle={{ backgroundColor: '#1F2937', borderColor: '#374151', color: '#F3F4F6' }}
                        itemStyle={{ color: '#F3F4F6' }}
                        labelStyle={{ color: '#9CA3AF' }}
                    />
                    <ReferenceLine y={20} stroke="#EF4444" strokeDasharray="3 3" label={{ value: 'Critical', fill: '#EF4444', fontSize: 10 }} />
                    <Line
                        type="monotone"
                        dataKey="rul"
                        stroke="#3B82F6"
                        strokeWidth={2}
                        dot={{ r: 3, fill: '#3B82F6' }}
                        activeDot={{ r: 5 }}
                    />
                </LineChart>
            </ResponsiveContainer>
        </div>
    );
}
