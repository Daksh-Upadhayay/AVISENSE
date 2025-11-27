import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import {
    LayoutDashboard,
    Plane,
    Settings,
    LogOut,
    Menu,
    X
} from 'lucide-react';
import { Button } from '../ui/Button';

import logo from '../../assets/logo.png';

export function Layout({ children }) {
    const { user, signOut } = useAuth();
    const location = useLocation();
    const [isMobileMenuOpen, setIsMobileMenuOpen] = React.useState(false);

    const navItems = [
        { label: 'Dashboard', icon: LayoutDashboard, path: '/dashboard' },
        { label: 'Engines', icon: Plane, path: '/engines' },
        { label: 'Settings', icon: Settings, path: '/settings' },
    ];

    const isActive = (path) => location.pathname === path;

    return (
        <div className="min-h-screen flex flex-col md:flex-row">
            {/* Sidebar (Desktop) */}

            <aside className="hidden md:flex flex-col w-64 fixed h-full glass-panel border-r border-white/10 z-20">
                <div className="p-6 border-b border-white/10">
                    <Link to="/" className="flex items-center gap-3">
                        <img src={logo} alt="Avisense Logo" className="w-10 h-10 object-contain" />
                        <span className="text-xl font-bold heading-gradient">Avisense</span>
                    </Link>
                </div>

                <nav className="flex-1 p-4 space-y-2">
                    {navItems.map((item) => (
                        <Link key={item.path} to={item.path}>
                            <div className={`
                flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200
                ${isActive(item.path)
                                    ? 'bg-primary-500/20 text-primary-400 border border-primary-500/30 shadow-glow-sm'
                                    : 'text-dark-muted hover:text-white hover:bg-white/5'}
              `}>
                                <item.icon className="w-5 h-5" />
                                <span className="font-medium">{item.label}</span>
                            </div>
                        </Link>
                    ))}
                </nav>

                <div className="p-4 border-t border-white/10">
                    <div className="flex items-center gap-3 px-4 py-3 mb-2">
                        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary-400 to-primary-600 flex items-center justify-center text-white font-bold text-sm">
                            {user?.email?.[0].toUpperCase()}
                        </div>
                        <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-white truncate">
                                {user?.user_metadata?.full_name || 'User'}
                            </p>
                            <p className="text-xs text-dark-muted truncate">{user?.email}</p>
                        </div>
                    </div>
                    <Button
                        variant="ghost"
                        className="w-full justify-start text-red-400 hover:text-red-300 hover:bg-red-500/10"
                        onClick={signOut}
                    >
                        <LogOut className="w-4 h-4" />
                        Sign Out
                    </Button>
                </div>
            </aside>

            {/* Mobile Header */}
            <header className="md:hidden fixed top-0 w-full z-30 glass-panel border-b border-white/10 px-4 py-3 flex items-center justify-between">
                <Link to="/" className="flex items-center gap-2">
                    <img src={logo} alt="Avisense Logo" className="w-8 h-8 object-contain" />
                    <span className="text-lg font-bold text-white">Avisense</span>
                </Link>
                <button
                    onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
                    className="p-2 text-dark-muted hover:text-white"
                >
                    {isMobileMenuOpen ? <X /> : <Menu />}
                </button>
            </header>

            {/* Mobile Menu Overlay */}
            {isMobileMenuOpen && (
                <div className="fixed inset-0 z-20 bg-dark-bg/95 backdrop-blur-xl pt-20 px-4 md:hidden">
                    <nav className="space-y-2">
                        {navItems.map((item) => (
                            <Link
                                key={item.path}
                                to={item.path}
                                onClick={() => setIsMobileMenuOpen(false)}
                            >
                                <div className={`
                  flex items-center gap-3 px-4 py-4 rounded-lg mb-2
                  ${isActive(item.path)
                                        ? 'bg-primary-500/20 text-primary-400 border border-primary-500/30'
                                        : 'text-dark-muted hover:text-white hover:bg-white/5'}
                `}>
                                    <item.icon className="w-5 h-5" />
                                    <span className="font-medium">{item.label}</span>
                                </div>
                            </Link>
                        ))}
                        <div className="pt-4 border-t border-white/10 mt-4">
                            <Button
                                variant="ghost"
                                className="w-full justify-start text-red-400"
                                onClick={signOut}
                            >
                                <LogOut className="w-4 h-4" />
                                Sign Out
                            </Button>
                        </div>
                    </nav>
                </div>
            )}

            {/* Main Content */}
            <main className="flex-1 md:ml-64 p-4 md:p-8 pt-20 md:pt-8 min-h-screen">
                <div className="max-w-7xl mx-auto animate-fade-in">
                    {children}
                </div>
            </main>
        </div>
    );
}
