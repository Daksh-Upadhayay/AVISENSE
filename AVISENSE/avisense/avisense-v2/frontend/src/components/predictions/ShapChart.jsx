import React from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';

export function ShapChart({ data }) {
    if (!data || !data.top_features) return null;

    // Prepare data for chart
    const chartData = data.top_features.map(item => ({
        name: item.feature,
        value: item.percent,
        raw: item.raw
    }));

    return (
        <div className="h-[250px] w-full">
            <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} layout="vertical" margin={{ top: 5, right: 30, left: 40, bottom: 5 }}>
                    <XAxis type="number" hide />
                    <YAxis
                        dataKey="name"
                        type="category"
                        width={80}
                        tick={{ fill: '#9CA3AF', fontSize: 12 }}
                        axisLine={false}
                        tickLine={false}
                    />
                    <Tooltip
                        contentStyle={{ backgroundColor: '#1F2937', borderColor: '#374151', color: '#F3F4F6' }}
                        itemStyle={{ color: '#F3F4F6' }}
                        cursor={{ fill: 'rgba(255,255,255,0.05)' }}
                        formatter={(value, name, props) => [
                            `${value.toFixed(1)}% (Raw: ${props.payload.raw.toFixed(4)})`,
                            'Contribution'
                        ]}
                    />
                    <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                        {chartData.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={index === 0 ? '#EF4444' : '#3B82F6'} />
                        ))}
                    </Bar>
                </BarChart>
            </ResponsiveContainer>
        </div>
    );
}
