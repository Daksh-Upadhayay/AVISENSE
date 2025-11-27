import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { supabase } from '../lib/supabase';
import { Plus, Plane, Search, Filter, ArrowRight } from 'lucide-react';
import { Layout } from '../components/layout/Layout';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { Input } from '../components/ui/Input';
import { AddEngineModal } from '../components/engines/AddEngineModal';

export default function Dashboard() {
    const [engines, setEngines] = useState([]);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState('');
    const [isAddEngineOpen, setIsAddEngineOpen] = useState(false);

    useEffect(() => {
        fetchEngines();
    }, []);

    const fetchEngines = async () => {
        try {
            const { data, error } = await supabase
                .from('engines')
                .select('*')
                .order('created_at', { ascending: false });

            if (error) throw error;
            console.log('Fetched engines:', data);
            setEngines(data || []);
        } catch (error) {
            console.error('Error fetching engines:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleEngineAdded = () => {
        fetchEngines();
    };

    // Safe filtering logic
    const filteredEngines = Array.isArray(engines) ? engines.filter(engine => {
        if (!engine) return false;
        const term = (searchTerm || '').toLowerCase();
        const id = (engine.engine_id || '').toLowerCase();
        const model = (engine.model || '').toLowerCase();
        return id.includes(term) || model.includes(term);
    }) : [];

    return (
        <Layout>
            <AddEngineModal
                isOpen={isAddEngineOpen}
                onClose={() => setIsAddEngineOpen(false)}
                onEngineAdded={handleEngineAdded}
            />

            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
                <div>
                    <h1 className="text-3xl font-bold text-white mb-2">Dashboard</h1>
                    <p className="text-dark-muted">Monitor fleet health and performance</p>
                </div>
                <Button
                    variant="primary"
                    className="shadow-glow-sm"
                    onClick={() => setIsAddEngineOpen(true)}
                >
                    <Plus className="w-5 h-5" />
                    Add Engine
                </Button>
            </div>

            {/* Stats Overview */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                <Card className="relative overflow-hidden group">
                    <div className="absolute right-0 top-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
                        <Plane className="w-24 h-24 text-primary-400" />
                    </div>
                    <div className="text-dark-muted text-sm font-medium mb-1">Total Engines</div>
                    <div className="text-3xl font-bold text-white">{engines.length}</div>
                    <div className="mt-2 text-xs text-green-400 flex items-center gap-1">
                        <div className="w-1.5 h-1.5 rounded-full bg-green-400" />
                        All systems operational
                    </div>
                </Card>

                <Card className="relative overflow-hidden group">
                    <div className="absolute right-0 top-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
                        <Filter className="w-24 h-24 text-accent-cyan" />
                    </div>
                    <div className="text-dark-muted text-sm font-medium mb-1">Active Monitoring</div>
                    <div className="text-3xl font-bold text-white">
                        {engines.filter(e => e?.status === 'active').length}
                    </div>
                    <div className="mt-2 text-xs text-primary-400">
                        {engines.length > 0
                            ? Math.round((engines.filter(e => e?.status === 'active').length / engines.length) * 100)
                            : 0}% of fleet
                    </div>
                </Card>

                <Card className="relative overflow-hidden group">
                    <div className="absolute right-0 top-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
                        <Search className="w-24 h-24 text-accent-purple" />
                    </div>
                    <div className="text-dark-muted text-sm font-medium mb-1">Recent Alerts</div>
                    <div className="text-3xl font-bold text-white">0</div>
                    <div className="mt-2 text-xs text-dark-muted">Last 24 hours</div>
                </Card>
            </div>

            {/* Filters */}
            <div className="flex items-center gap-4 mb-6">
                <div className="flex-1 max-w-md">
                    <Input
                        icon={Search}
                        placeholder="Search engines..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="bg-dark-surface"
                    />
                </div>
                <Button variant="secondary" className="hidden md:flex">
                    <Filter className="w-4 h-4" />
                    Filter
                </Button>
            </div>

            {/* Engines Grid */}
            {loading ? (
                <div className="flex items-center justify-center py-20">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-500"></div>
                </div>
            ) : filteredEngines.length === 0 ? (
                <div className="text-center py-20 border border-dashed border-white/10 rounded-2xl bg-white/5">
                    <div className="w-16 h-16 rounded-full bg-white/5 flex items-center justify-center mx-auto mb-4">
                        <Plane className="h-8 w-8 text-dark-muted" />
                    </div>
                    <h3 className="text-xl font-semibold text-white mb-2">No engines found</h3>
                    <p className="text-dark-muted mb-6 max-w-sm mx-auto">
                        {searchTerm ? 'Try adjusting your search terms' : 'Add your first engine to start monitoring performance'}
                    </p>
                    {!searchTerm && (
                        <Button
                            variant="primary"
                            onClick={() => setIsAddEngineOpen(true)}
                        >
                            <Plus className="w-5 h-5" />
                            Add Your First Engine
                        </Button>
                    )}
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {filteredEngines.map((engine) => {
                        if (!engine) return null;
                        return (
                            <Link key={engine.id || Math.random()} to={`/engines/${engine.id}`}>
                                <Card hover className="h-full border-t-4 border-t-primary-500">
                                    <div className="flex items-start justify-between mb-4">
                                        <div>
                                            <h3 className="text-lg font-semibold text-white">{engine.engine_id || 'Unknown ID'}</h3>
                                            <p className="text-sm text-dark-muted">{engine.model || 'Unknown Model'}</p>
                                        </div>
                                        <span className={`
                                            px-2.5 py-1 rounded-full text-xs font-medium border
                                            ${engine.status === 'active'
                                                ? 'bg-green-500/10 text-green-400 border-green-500/20'
                                                : engine.status === 'maintenance'
                                                    ? 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20'
                                                    : 'bg-white/10 text-dark-muted border-white/10'}
                                        `}>
                                            {engine.status || 'Unknown'}
                                        </span>
                                    </div>

                                    <div className="space-y-2 mb-4">
                                        <div className="flex justify-between text-sm">
                                            <span className="text-dark-muted">Serial Number</span>
                                            <span className="text-white font-mono">{engine.serial_number || 'N/A'}</span>
                                        </div>
                                        <div className="flex justify-between text-sm">
                                            <span className="text-dark-muted">Aircraft</span>
                                            <span className="text-white">{engine.aircraft_registration || 'N/A'}</span>
                                        </div>
                                    </div>

                                    <div className="pt-4 border-t border-white/10 flex items-center justify-between text-xs text-dark-muted">
                                        <span>Added {engine.created_at ? new Date(engine.created_at).toLocaleDateString() : 'Unknown'}</span>
                                        <span className="flex items-center gap-1 text-primary-400 group-hover:translate-x-1 transition-transform">
                                            View Details <ArrowRight className="w-3 h-3" />
                                        </span>
                                    </div>
                                </Card>
                            </Link>
                        );
                    })}
                </div>
            )}
        </Layout>
    );
}
