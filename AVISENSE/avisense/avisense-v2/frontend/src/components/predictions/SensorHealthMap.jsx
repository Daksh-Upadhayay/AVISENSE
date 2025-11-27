import React from 'react';
import { AlertTriangle, CheckCircle, Activity } from 'lucide-react';

export function SensorHealthMap({ anomalies, inputData }) {
    // List of all sensors we care about
    const sensors = [
        'sensor_2', 'sensor_3', 'sensor_4', 'sensor_7',
        'sensor_9', 'sensor_11', 'sensor_12', 'sensor_14',
        'sensor_17', 'sensor_20', 'sensor_21'
    ];

    const getSensorStatus = (sensorName) => {
        const anomaly = anomalies?.find(a => a.sensor === sensorName);
        if (!anomaly) return { status: 'normal', color: 'bg-green-500/20 text-green-400 border-green-500/30' };

        if (anomaly.severity === 'high') return { status: 'critical', color: 'bg-red-500/20 text-red-400 border-red-500/30' };
        return { status: 'warning', color: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30' };
    };

    return (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
            {sensors.map(sensor => {
                const { status, color } = getSensorStatus(sensor);
                const value = inputData?.[sensor];

                return (
                    <div key={sensor} className={`p-3 rounded-lg border ${color} transition-all duration-200 hover:scale-105`}>
                        <div className="flex justify-between items-start mb-1">
                            <span className="text-xs font-medium uppercase opacity-80">{sensor.replace('_', ' ')}</span>
                            {status === 'normal' ? <CheckCircle className="w-3 h-3" /> : <AlertTriangle className="w-3 h-3" />}
                        </div>
                        <div className="text-lg font-bold">
                            {value ? value.toFixed(1) : '-'}
                        </div>
                    </div>
                );
            })}
        </div>
    );
}
