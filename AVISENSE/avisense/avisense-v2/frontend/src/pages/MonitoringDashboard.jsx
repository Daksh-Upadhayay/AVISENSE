import React, { useState, useEffect } from 'react';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Activity, AlertTriangle, TrendingUp, Database, CheckCircle, XCircle } from 'lucide-react';
import { api } from '../lib/api';

export function MonitoringDashboard() {
    const [healthData, setHealthData] = useState(null);
    const [stats, setStats] = useState([]);
    const [alerts, setAlerts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        fetchMonitoringData();
        // Refresh every 30 seconds
        const interval = setInterval(fetchMonitoringData, 30000);
        return () => clearInterval(interval);
    }, []);

    const fetchMonitoringData = async () => {
        try {
            setLoading(true);
            const [health, statsData, alertsData] = await Promise.all([
                api.get('/api/monitoring/health'),
                api.get('/api/monitoring/stats?days=7'),
                api.get('/api/monitoring/alerts?days=7')
            ]);

            setHealthData(health);
            setStats(statsData.stats || []);
            setAlerts(alertsData.alerts || []);
            setError(null);
        } catch (err) {
            console.error('Failed to fetch monitoring data:', err);
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const getStatusColor = (status) => {
        switch (status) {
            case 'healthy': return 'text-green-400 bg-green-500/20';
            case 'warning': return 'text-yellow-400 bg-yellow-500/20';
            case 'critical': return 'text-red-400 bg-red-500/20';
            default: return 'text-gray-400 bg-gray-500/20';
        }
    };

    const getSeverityColor = (severity) => {
        switch (severity) {
            case 'critical': return 'border-red-500/50 bg-red-500/10';
            case 'high': return 'border-orange-500/50 bg-orange-500/10';
            case 'medium': return 'border-yellow-500/50 bg-yellow-500/10';
            default: return 'border-blue-500/50 bg-blue-500/10';
        }
    };

    if (loading && !healthData) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-500"></div>
            </div>
        );
    }

    return (
        <div className="space-y-6 p-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-white">System Monitoring</h1>
                    <p className="text-dark-muted mt-1">Real-time health and performance metrics</p>
                </div>
                <Button onClick={fetchMonitoringData} variant="secondary">
                    <Activity className="w-4 h-4 mr-2" />
                    Refresh
                </Button>
            </div>

            {error && (
                <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400">
                    {error}
                </div>
            )}

            {/* System Health Status */}
            {healthData && (
                <Card className="p-6 bg-dark-surface/50 backdrop-blur-sm border-white/10">
                    <div className="flex items-center justify-between mb-4">
                        <h2 className="text-xl font-semibold text-white">System Health</h2>
                        <div className={`px-4 py-2 rounded-full font-medium ${getStatusColor(healthData.status)}`}>
                            {healthData.status === 'healthy' && <CheckCircle className="w-4 h-4 inline mr-2" />}
                            {healthData.status !== 'healthy' && <AlertTriangle className="w-4 h-4 inline mr-2" />}
                            {healthData.status.toUpperCase()}
                        </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                        <div className="p-4 rounded-lg bg-dark-bg/50">
                            <div className="text-sm text-dark-muted mb-1">Total Alerts</div>
                            <div className="text-2xl font-bold text-white">{healthData.alerts?.total || 0}</div>
                        </div>
                        <div className="p-4 rounded-lg bg-dark-bg/50">
                            <div className="text-sm text-dark-muted mb-1">Critical Alerts</div>
                            <div className="text-2xl font-bold text-red-400">{healthData.alerts?.critical || 0}</div>
                        </div>
                        <div className="p-4 rounded-lg bg-dark-bg/50">
                            <div className="text-sm text-dark-muted mb-1">Drift Alerts</div>
                            <div className="text-2xl font-bold text-yellow-400">{healthData.drift_alerts || 0}</div>
                        </div>
                        <div className="p-4 rounded-lg bg-dark-bg/50">
                            <div className="text-sm text-dark-muted mb-1">Active Models</div>
                            <div className="text-2xl font-bold text-primary-400">{healthData.active_models?.length || 0}</div>
                        </div>
                    </div>

                    {/* Active Models */}
                    {healthData.active_models && healthData.active_models.length > 0 && (
                        <div className="mt-4">
                            <h3 className="text-sm font-medium text-dark-muted mb-2">Production Models</h3>
                            <div className="flex flex-wrap gap-2">
                                {healthData.active_models.map((model, idx) => (
                                    <div key={idx} className="px-3 py-1 rounded-full bg-primary-500/20 text-primary-400 text-sm">
                                        {model.model_family} {model.version}
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </Card>
            )}

            {/* Active Alerts */}
            {alerts.length > 0 && (
                <Card className="p-6 bg-dark-surface/50 backdrop-blur-sm border-white/10">
                    <h2 className="text-xl font-semibold text-white mb-4 flex items-center">
                        <AlertTriangle className="w-5 h-5 mr-2 text-yellow-400" />
                        Active Alerts ({alerts.length})
                    </h2>
                    <div className="space-y-3">
                        {alerts.map((alert, idx) => (
                            <div key={idx} className={`p-4 rounded-lg border ${getSeverityColor(alert.severity)}`}>
                                <div className="flex items-start justify-between">
                                    <div>
                                        <div className="font-medium text-white mb-1">{alert.type.replace(/_/g, ' ').toUpperCase()}</div>
                                        <div className="text-sm text-dark-muted">{alert.message}</div>
                                    </div>
                                    <div className="text-xs text-dark-muted">{alert.date}</div>
                                </div>
                            </div>
                        ))}
                    </div>
                </Card>
            )}

            {/* Prediction Statistics */}
            {stats.length > 0 && (
                <Card className="p-6 bg-dark-surface/50 backdrop-blur-sm border-white/10">
                    <h2 className="text-xl font-semibold text-white mb-4 flex items-center">
                        <TrendingUp className="w-5 h-5 mr-2 text-primary-400" />
                        Prediction Statistics (Last 7 Days)
                    </h2>
                    <div className="overflow-x-auto">
                        <table className="w-full">
                            <thead>
                                <tr className="border-b border-white/10">
                                    <th className="text-left py-3 px-4 text-sm font-medium text-dark-muted">Date</th>
                                    <th className="text-left py-3 px-4 text-sm font-medium text-dark-muted">Model</th>
                                    <th className="text-right py-3 px-4 text-sm font-medium text-dark-muted">Total</th>
                                    <th className="text-right py-3 px-4 text-sm font-medium text-dark-muted">Failures</th>
                                    <th className="text-right py-3 px-4 text-sm font-medium text-dark-muted">Avg Risk %</th>
                                    <th className="text-right py-3 px-4 text-sm font-medium text-dark-muted">Latency (ms)</th>
                                </tr>
                            </thead>
                            <tbody>
                                {stats.map((stat, idx) => (
                                    <tr key={idx} className="border-b border-white/5 hover:bg-white/5">
                                        <td className="py-3 px-4 text-sm text-white">{stat.date}</td>
                                        <td className="py-3 px-4 text-sm text-primary-400">{stat.model_family}</td>
                                        <td className="py-3 px-4 text-sm text-white text-right">{stat.total_predictions}</td>
                                        <td className="py-3 px-4 text-sm text-red-400 text-right">{stat.failure_predictions}</td>
                                        <td className="py-3 px-4 text-sm text-white text-right">
                                            {stat.avg_risk_percent ? stat.avg_risk_percent.toFixed(1) : 'N/A'}
                                        </td>
                                        <td className="py-3 px-4 text-sm text-white text-right">
                                            {stat.avg_latency_ms ? stat.avg_latency_ms.toFixed(0) : 'N/A'}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </Card>
            )}

            {/* Today's Stats */}
            {healthData?.today_stats && (
                <Card className="p-6 bg-dark-surface/50 backdrop-blur-sm border-white/10">
                    <h2 className="text-xl font-semibold text-white mb-4 flex items-center">
                        <Database className="w-5 h-5 mr-2 text-primary-400" />
                        Today's Performance
                    </h2>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <div>
                            <div className="text-sm text-dark-muted mb-1">Predictions</div>
                            <div className="text-2xl font-bold text-white">{healthData.today_stats.total_predictions}</div>
                        </div>
                        <div>
                            <div className="text-sm text-dark-muted mb-1">Failure Rate</div>
                            <div className="text-2xl font-bold text-red-400">
                                {((healthData.today_stats.failure_predictions / healthData.today_stats.total_predictions) * 100).toFixed(1)}%
                            </div>
                        </div>
                        <div>
                            <div className="text-sm text-dark-muted mb-1">Avg Anomaly Score</div>
                            <div className="text-2xl font-bold text-yellow-400">
                                {healthData.today_stats.avg_anomaly_score?.toFixed(3) || 'N/A'}
                            </div>
                        </div>
                        <div>
                            <div className="text-sm text-dark-muted mb-1">Errors</div>
                            <div className="text-2xl font-bold text-red-400">{healthData.today_stats.error_count}</div>
                        </div>
                    </div>
                </Card>
            )}
        </div>
    );
}
