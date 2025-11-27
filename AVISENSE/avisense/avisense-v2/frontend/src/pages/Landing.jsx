import React from 'react';
import { Link } from 'react-router-dom';
import { Plane, Shield, TrendingUp, ArrowRight, Activity, Zap } from 'lucide-react';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import logo from '../assets/logo.png';

export default function Landing() {
    return (
        <div className="min-h-screen flex flex-col">
            {/* Navbar */}
            <nav className="fixed w-full z-50 glass-panel border-b border-white/10">
                <div className="container mx-auto px-6 py-4 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <img src={logo} alt="Avisense Logo" className="w-10 h-10 object-contain" />
                        <span className="text-xl font-bold heading-gradient">Avisense</span>
                    </div>
                    <div className="flex items-center gap-4">
                        <Link to="/login">
                            <Button variant="ghost" className="text-sm">Log In</Button>
                        </Link>
                        <Link to="/signup">
                            <Button variant="primary" className="text-sm shadow-glow-sm">
                                Get Started
                            </Button>
                        </Link>
                    </div>
                </div>
            </nav>

            {/* Hero Section */}
            <main className="flex-1 pt-32 pb-20 px-6">
                <div className="container mx-auto max-w-6xl">
                    <div className="text-center mb-20 relative">
                        {/* Background Glow */}
                        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-primary-500/20 rounded-full blur-[100px] -z-10 animate-pulse-slow" />

                        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary-500/10 border border-primary-500/20 text-primary-300 text-sm font-medium mb-8 animate-fade-in">
                            <span className="relative flex h-2 w-2">
                                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary-400 opacity-75"></span>
                                <span className="relative inline-flex rounded-full h-2 w-2 bg-primary-500"></span>
                            </span>
                            Powered by NASA C-MAPSS Data
                        </div>

                        <h1 className="text-5xl md:text-7xl font-bold text-white mb-6 leading-tight animate-slide-up">
                            Predict Engine Failures <br />
                            <span className="heading-gradient">Before They Happen</span>
                        </h1>

                        <p className="text-xl text-dark-muted mb-10 max-w-2xl mx-auto animate-slide-up animation-delay-200">
                            Advanced ML-powered engine health monitoring. Detect anomalies,
                            predict failures, and optimize maintenance schedules with 97.6% accuracy.
                        </p>

                        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 animate-slide-up animation-delay-400">
                            <Link to="/signup">
                                <Button variant="primary" className="text-lg px-8 py-4 h-auto">
                                    Start Monitoring Free
                                    <ArrowRight className="w-5 h-5" />
                                </Button>
                            </Link>
                            <a href="#features">
                                <Button variant="secondary" className="text-lg px-8 py-4 h-auto">
                                    View Demo
                                </Button>
                            </a>
                        </div>
                    </div>

                    {/* Stats Grid */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-32 animate-slide-up animation-delay-400">
                        <Card className="text-center group">
                            <div className="mb-4 inline-flex p-4 rounded-2xl bg-primary-500/10 text-primary-400 group-hover:scale-110 transition-transform duration-300">
                                <Shield className="w-8 h-8" />
                            </div>
                            <div className="text-4xl font-bold text-white mb-2">97.6%</div>
                            <div className="text-dark-muted">Safe Engine Recall</div>
                        </Card>
                        <Card className="text-center group">
                            <div className="mb-4 inline-flex p-4 rounded-2xl bg-accent-cyan/10 text-accent-cyan group-hover:scale-110 transition-transform duration-300">
                                <Activity className="w-8 h-8" />
                            </div>
                            <div className="text-4xl font-bold text-white mb-2">86.9%</div>
                            <div className="text-dark-muted">Failure Detection Rate</div>
                        </Card>
                        <Card className="text-center group">
                            <div className="mb-4 inline-flex p-4 rounded-2xl bg-accent-purple/10 text-accent-purple group-hover:scale-110 transition-transform duration-300">
                                <Zap className="w-8 h-8" />
                            </div>
                            <div className="text-4xl font-bold text-white mb-2">&lt;200ms</div>
                            <div className="text-dark-muted">Prediction Latency</div>
                        </Card>
                    </div>

                    {/* Features Section */}
                    <div id="features" className="grid grid-cols-1 md:grid-cols-2 gap-12 items-center">
                        <div className="space-y-8">
                            <h2 className="text-3xl md:text-4xl font-bold text-white">
                                Enterprise-Grade <br />
                                <span className="text-primary-400">Engine Monitoring</span>
                            </h2>
                            <p className="text-dark-muted text-lg">
                                Built for reliability and scale. Monitor your entire fleet in real-time
                                with predictive insights powered by state-of-the-art machine learning.
                            </p>

                            <div className="space-y-4">
                                {[
                                    'Real-time anomaly detection',
                                    'Predictive maintenance alerts',
                                    'Fleet-wide health dashboard',
                                    'Secure data encryption'
                                ].map((feature, i) => (
                                    <div key={i} className="flex items-center gap-3 text-white">
                                        <div className="p-1 rounded-full bg-primary-500/20 text-primary-400">
                                            <ArrowRight className="w-4 h-4" />
                                        </div>
                                        {feature}
                                    </div>
                                ))}
                            </div>
                        </div>

                        <div className="relative">
                            <div className="absolute inset-0 bg-primary-500/20 blur-[80px] rounded-full -z-10" />
                            <Card className="border-primary-500/30 bg-dark-surface/80 backdrop-blur-xl">
                                <div className="flex items-center justify-between mb-6 border-b border-white/10 pb-4">
                                    <div className="flex items-center gap-3">
                                        <div className="w-3 h-3 rounded-full bg-red-500" />
                                        <div className="w-3 h-3 rounded-full bg-yellow-500" />
                                        <div className="w-3 h-3 rounded-full bg-green-500" />
                                    </div>
                                    <div className="text-xs text-dark-muted font-mono">LIVE MONITORING</div>
                                </div>
                                <div className="space-y-4">
                                    {[1, 2, 3].map((i) => (
                                        <div key={i} className="flex items-center justify-between p-3 rounded-lg bg-white/5 border border-white/5">
                                            <div className="flex items-center gap-3">
                                                <Activity className="w-4 h-4 text-primary-400" />
                                                <span className="text-sm text-white">Engine #{100 + i}</span>
                                            </div>
                                            <span className="text-xs px-2 py-1 rounded-full bg-green-500/20 text-green-400 border border-green-500/30">
                                                Normal
                                            </span>
                                        </div>
                                    ))}
                                </div>
                            </Card>
                        </div>
                    </div>
                </div>
            </main>

            {/* Footer */}
            <footer className="border-t border-white/10 bg-dark-surface/30 backdrop-blur-md py-8">
                <div className="container mx-auto px-6 text-center text-dark-muted text-sm">
                    <p>&copy; 2025 Avisense. Powered by NASA C-MAPSS data.</p>
                </div>
            </footer>
        </div>
    );
}
