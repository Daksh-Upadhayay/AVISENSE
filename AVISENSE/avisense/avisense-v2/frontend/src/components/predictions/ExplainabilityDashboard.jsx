import React from 'react';
import { RiskGauge } from './RiskGauge';
import { ShapChart } from './ShapChart';
import { SensorHealthMap } from './SensorHealthMap';
import { Card } from '../ui/Card';
import { AlertTriangle, Info } from 'lucide-react';

export function ExplainabilityDashboard({ predictionResult }) {
    if (!predictionResult) return null;

    const {
        risk_percent,
        shap,
        anomalies,
        correlated_anomalies,
        input_data,
        prediction
    } = predictionResult;

    // Fallback if risk_percent is missing (e.g. old prediction)
    const riskScore = risk_percent ?? (predictionResult.failure_probability * 100);

    return (
        <div className="space-y-6 animate-fade-in">
            {/* Top Row: Risk & Key Factors */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {/* Risk Gauge */}
                <Card className="flex flex-col items-center justify-center p-6 bg-dark-surface/50 backdrop-blur-sm border-white/10">
                    <h3 className="text-lg font-semibold text-white mb-4">Failure Risk Score</h3>
                    <RiskGauge riskScore={riskScore} size={160} />
                    <div className={`mt-4 px-3 py-1 rounded-full text-sm font-medium ${prediction === 'SAFE' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
                        }`}>
                        {prediction === 'SAFE' ? 'System Healthy' : 'Prone to Failure'}
                    </div>
                </Card>

                {/* SHAP Feature Importance */}
                <Card className="md:col-span-2 p-6 bg-dark-surface/50 backdrop-blur-sm border-white/10">
                    <div className="flex items-center justify-between mb-4">
                        <h3 className="text-lg font-semibold text-white">Top Risk Contributors</h3>
                        <div className="group relative">
                            <Info className="w-4 h-4 text-dark-muted cursor-help" />
                            <div className="absolute right-0 top-6 w-64 p-2 bg-dark-bg border border-white/10 rounded-lg text-xs text-dark-muted hidden group-hover:block z-50">
                                Shows which sensors contributed most to this risk score based on SHAP analysis.
                            </div>
                        </div>
                    </div>
                    <ShapChart data={shap} />
                </Card>
            </div>

            {/* Correlated Anomalies Alert */}
            {correlated_anomalies && correlated_anomalies.length > 0 && (
                <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/20 flex items-start gap-3">
                    <AlertTriangle className="w-5 h-5 text-red-400 mt-0.5" />
                    <div>
                        <h4 className="font-semibold text-red-400">Correlated System Failure Detected</h4>
                        <p className="text-sm text-red-300/80 mt-1">
                            {correlated_anomalies[0].explanation}
                        </p>
                    </div>
                </div>
            )}

            {/* Sensor Health Map */}
            <Card className="p-6 bg-dark-surface/50 backdrop-blur-sm border-white/10">
                <h3 className="text-lg font-semibold text-white mb-4">Sensor Health Status</h3>
                <SensorHealthMap anomalies={anomalies} inputData={input_data} />
            </Card>
        </div>
    );
}
