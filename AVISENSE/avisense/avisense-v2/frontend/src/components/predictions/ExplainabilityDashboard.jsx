import React from 'react';
import { RiskGauge } from './RiskGauge';
import { ShapChart } from './ShapChart';
import { SensorHealthMap } from './SensorHealthMap';
import { AnomalyScoreGauge } from './AnomalyScoreGauge';
import { ReconstructionErrorChart } from './ReconstructionErrorChart';
import { TemporalAnomalyChart } from './TemporalAnomalyChart';
import { Card } from '../ui/Card';
import { AlertTriangle, Info, Brain } from 'lucide-react';

export function ExplainabilityDashboard({ predictionResult }) {
    if (!predictionResult) return null;

    const {
        risk_percent,
        shap,
        anomalies,
        correlated_anomalies,
        input_data,
        prediction,
        anomaly_score_normalized,
        reconstruction_errors,
        model_type
    } = predictionResult;

    // Fallback if risk_percent is missing (e.g. old prediction)
    const riskScore = risk_percent ?? (predictionResult.failure_probability * 100);

    // Check if deep learning was used
    const hasDeepLearning = anomaly_score_normalized !== undefined && anomaly_score_normalized !== null;

    return (

        <div className="animate-fade-in h-full">
            <div className="grid grid-cols-12 gap-3 h-full">
                {/* Left Column: Key Metrics (25%) */}
                <div className="col-span-12 lg:col-span-3 space-y-2 flex flex-col">
                    {/* Risk Gauge */}
                    <Card className="flex flex-col items-center justify-center p-2 bg-dark-surface/50 backdrop-blur-sm border-white/10 flex-1 min-h-[100px]">
                        <RiskGauge riskScore={riskScore} size={110} />
                        <h3 className="text-[10px] font-semibold text-white mt-1 text-center leading-tight">
                            {hasDeepLearning ? 'Hybrid Risk Score' : 'Failure Risk Score'}
                        </h3>
                        <div className={`mt-0.5 px-1.5 py-0.5 rounded-full text-[8px] font-medium ${prediction === 'SAFE' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
                            }`}>
                            {prediction === 'SAFE' ? 'System Healthy' : 'Prone to Failure'}
                        </div>
                    </Card>

                    {/* Anomaly Score (if deep learning) */}
                    {hasDeepLearning && (
                        <Card className="flex flex-col items-center justify-center p-2 bg-gradient-to-br from-purple-500/10 to-blue-500/10 backdrop-blur-sm border-purple-500/20 flex-1 min-h-[100px]">
                            <AnomalyScoreGauge anomalyScore={anomaly_score_normalized} size={110} />
                            <div className="flex items-center gap-1 mt-1">
                                <Brain className="w-2.5 h-2.5 text-purple-400" />
                                <h3 className="text-[10px] font-semibold text-white">Anomaly Score</h3>
                            </div>
                            <div className="mt-0.5 text-[8px] text-purple-300 font-medium">
                                {model_type === 'vae' ? 'Variational AE' : (model_type === 'lstm_ae' ? 'LSTM Model' : 'Dense AE')}
                            </div>
                        </Card>
                    )}
                </div>

                {/* Middle Column: Charts (45%) */}
                <div className="col-span-12 lg:col-span-5">
                    {/* SHAP Feature Importance */}
                    <Card className="p-3 bg-dark-surface/50 backdrop-blur-sm border-white/10 h-full">
                        <div className="flex items-center justify-between mb-1">
                            <h3 className="text-xs font-semibold text-white">Risk Contributors</h3>
                        </div>
                        <div className="h-[220px]">
                            <ShapChart data={shap} />
                        </div>
                    </Card>
                </div>

                {/* Right Column: Sensor Health (30%) */}
                <div className="col-span-12 lg:col-span-4 flex flex-col">
                    <Card className="p-3 bg-dark-surface/50 backdrop-blur-sm border-white/10 h-full flex flex-col">
                        <h3 className="text-xs font-semibold text-white mb-2">Sensor Health Map</h3>
                        <div className="flex-1 overflow-y-auto pr-1 custom-scrollbar">
                            <SensorHealthMap anomalies={anomalies} inputData={input_data} />
                        </div>
                    </Card>
                </div>
            </div>

            {/* Correlated Anomalies Alert (Bottom) */}
            {correlated_anomalies && correlated_anomalies.length > 0 && (
                <div className="mt-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 flex items-center gap-3">
                    <AlertTriangle className="w-5 h-5 text-red-400" />
                    <div>
                        <h4 className="font-semibold text-red-400 text-sm">Correlated System Failure Detected</h4>
                        <p className="text-xs text-red-300/80">
                            {correlated_anomalies[0].explanation}
                        </p>
                    </div>
                </div>
            )}
        </div>
    );

}
