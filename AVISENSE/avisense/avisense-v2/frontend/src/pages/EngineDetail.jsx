import { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { supabase } from '../lib/supabase';
import { Layout } from '../components/layout/Layout';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { MakePredictionModal } from '../components/predictions/MakePredictionModal';
import { TemporalAnomalyChart } from '../components/predictions/TemporalAnomalyChart';
import { RULGauge } from '../components/predictions/RULGauge';
import { RULTimeline } from '../components/predictions/RULTimeline';
import { api } from '../lib/api';
import { ArrowLeft, Activity, AlertTriangle, CheckCircle, Clock, Timer } from 'lucide-react';

export default function EngineDetail() {
    const { id } = useParams();
    const [engine, setEngine] = useState(null);
    const [predictions, setPredictions] = useState([]);
    const [rulHistory, setRulHistory] = useState([]);
    const [latestRul, setLatestRul] = useState(null);
    const [loading, setLoading] = useState(true);
    const [isPredictionModalOpen, setIsPredictionModalOpen] = useState(false);
    const [rulLoading, setRulLoading] = useState(false);

    const fetchData = useCallback(async () => {
        try {
            // Fetch engine details
            const { data: engineData, error: engineError } = await supabase
                .from('engines')
                .select('*')
                .eq('id', id)
                .single();

            if (engineError) throw engineError;
            setEngine(engineData);

            // Fetch prediction history
            const { data: predData, error: predError } = await supabase
                .from('predictions')
                .select('*')
                .eq('engine_id', id)
                .order('created_at', { ascending: false });

            if (predError) throw predError;
            setPredictions(predData || []);

            // Filter for RUL data
            const rulData = (predData || []).filter(p => p.rul_prediction !== null && p.rul_prediction !== undefined);
            setRulHistory(rulData);
            if (rulData.length > 0) {
                setLatestRul(rulData[0]);
            }
        } catch (error) {
            console.error('Error fetching data:', error);
        } finally {
            setLoading(false);
        }
    }, [id]);

    useEffect(() => {
        fetchData();
    }, [fetchData]);

    const handlePredictionComplete = () => {
        fetchData(); // Refresh history
    };

    const handleRunRUL = async () => {
        try {
            setRulLoading(true);
            await api.post('/predict/rul', {
                engine_id: id,
                use_latest: true
            });
            await fetchData(); // Refresh data
        } catch (error) {
            console.error('RUL Prediction failed:', error);
            alert('Failed to run RUL prediction');
        } finally {
            setRulLoading(false);
        }
    };

    if (loading) {
        return (
            <Layout>
                <div className="flex items-center justify-center h-screen">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-500"></div>
                </div>
            </Layout>
        );
    }

    if (!engine) {
        return (
            <Layout>
                <div className="text-center py-20">
                    <h2 className="text-2xl font-bold text-white">Engine not found</h2>
                    <Link to="/dashboard" className="text-primary-400 hover:underline mt-4 block">
                        Return to Dashboard
                    </Link>
                </div>
            </Layout>
        );
    }

    return (
        <Layout>
            <MakePredictionModal
                isOpen={isPredictionModalOpen}
                onClose={() => setIsPredictionModalOpen(false)}
                engineId={id}
                onPredictionComplete={handlePredictionComplete}
            />

            <div className="mb-8">
                <Link to="/dashboard" className="inline-flex items-center text-dark-muted hover:text-white mb-4 transition-colors">
                    <ArrowLeft className="w-4 h-4 mr-2" />
                    Back to Dashboard
                </Link>

                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div>
                        <h1 className="text-3xl font-bold text-white mb-2">{engine.engine_id}</h1>
                        <p className="text-dark-muted">{engine.model} • {engine.serial_number}</p>
                    </div>
                    <div className="flex gap-2">

                        <Button variant="primary" onClick={() => setIsPredictionModalOpen(true)} className="shadow-glow-sm">
                            <Activity className="w-5 h-5 mr-2" />
                            Make Prediction
                        </Button>
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Main Info / Latest Status */}
                <div className="lg:col-span-2 space-y-6">
                    {/* Temporal Anomaly Chart */}
                    {predictions.length > 0 && (
                        <TemporalAnomalyChart predictions={predictions} threshold={0.5} />
                    )}



                    <Card>
                        <h3 className="text-lg font-semibold text-white mb-4">Prediction History</h3>

                        {predictions.length === 0 ? (
                            <div className="text-center py-10 border border-dashed border-white/10 rounded-lg">
                                <p className="text-dark-muted">No predictions run yet.</p>
                                <Button variant="ghost" className="mt-2 text-primary-400" onClick={() => setIsPredictionModalOpen(true)}>
                                    Run your first prediction
                                </Button>
                            </div>
                        ) : (
                            <div className="space-y-4">
                                {predictions.map((pred) => (
                                    <div key={pred.id} className="p-4 rounded-lg bg-white/5 border border-white/10 hover:border-primary-500/30 transition-colors">
                                        <div className="flex items-start justify-between mb-2">
                                            <div className="flex items-center gap-3">
                                                {pred.prediction === 'SAFE' ? (
                                                    <div className="p-2 rounded-full bg-green-500/20 text-green-400">
                                                        <CheckCircle className="w-5 h-5" />
                                                    </div>
                                                ) : (
                                                    <div className="p-2 rounded-full bg-red-500/20 text-red-400">
                                                        <AlertTriangle className="w-5 h-5" />
                                                    </div>
                                                )}
                                                <div>
                                                    <div className="font-semibold text-white">
                                                        {pred.prediction === 'SAFE' ? 'System Healthy' : 'Failure Risk Detected'}
                                                    </div>
                                                    <div className="text-xs text-dark-muted">
                                                        Model {pred.model_version} • {new Date(pred.created_at).toLocaleString()}
                                                    </div>
                                                </div>
                                            </div>
                                            {/* Risk percentage removed as requested */}
                                        </div>

                                        {/* Anomalies Preview */}
                                        {pred.anomalies && pred.anomalies.length > 0 && (
                                            <div className="mt-3 pt-3 border-t border-white/10">
                                                <p className="text-xs text-red-300 mb-2">Detected Anomalies:</p>
                                                <div className="flex flex-wrap gap-2">
                                                    {pred.anomalies.map((anomaly, idx) => (
                                                        <span key={idx} className="px-2 py-1 rounded text-xs bg-red-500/10 text-red-300 border border-red-500/20">
                                                            {anomaly.sensor}: {anomaly.value.toFixed(2)}
                                                        </span>
                                                    ))}
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        )}
                    </Card>
                </div>

                {/* Sidebar Info */}
                <div className="space-y-6">
                    <Card>
                        <h3 className="text-lg font-semibold text-white mb-4">Engine Details</h3>
                        <div className="space-y-3 text-sm">
                            <div className="flex justify-between">
                                <span className="text-dark-muted">Status</span>
                                <span className="text-white capitalize">{engine.status}</span>
                            </div>
                            <div className="flex justify-between">
                                <span className="text-dark-muted">Aircraft</span>
                                <span className="text-white">{engine.aircraft_registration || 'N/A'}</span>
                            </div>
                            <div className="flex justify-between">
                                <span className="text-dark-muted">Added</span>
                                <span className="text-white">{new Date(engine.created_at).toLocaleDateString()}</span>
                            </div>
                        </div>
                    </Card>
                </div>
            </div>
        </Layout>
    );
}
