import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { Plane, Mail, Lock, ArrowRight } from 'lucide-react';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Card } from '../components/ui/Card';
import logo from '../assets/logo.png';

export default function Login() {
    const navigate = useNavigate();
    const { signIn } = useAuth();
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [formData, setFormData] = useState({
        email: '',
        password: '',
    });

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError(null);
        setLoading(true);

        try {
            await signIn(formData.email, formData.password);
            navigate('/dashboard');
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const handleChange = (e) => {
        setFormData({ ...formData, [e.target.name]: e.target.value });
    };

    return (
        <div className="min-h-screen flex items-center justify-center p-4 relative overflow-hidden">
            {/* Background Elements */}
            <div className="absolute top-0 left-0 w-full h-full overflow-hidden -z-10">
                <div className="absolute top-[-10%] left-[-5%] w-[500px] h-[500px] bg-primary-600/20 rounded-full blur-[120px]" />
                <div className="absolute bottom-[-10%] right-[-5%] w-[500px] h-[500px] bg-accent-purple/10 rounded-full blur-[120px]" />
            </div>

            <div className="w-full max-w-md animate-fade-in">
                <div className="text-center mb-8">
                    <Link to="/" className="inline-flex items-center gap-3 mb-6 group">
                        <img src={logo} alt="Avisense Logo" className="w-12 h-12 object-contain group-hover:scale-105 transition-transform duration-300" />
                        <span className="text-2xl font-bold text-white">Avisense</span>
                    </Link>
                    <h2 className="text-3xl font-bold text-white mb-2">Welcome Back</h2>
                    <p className="text-dark-muted">Log in to access your fleet dashboard</p>
                </div>

                <Card className="backdrop-blur-xl border-white/10">
                    <form onSubmit={handleSubmit} className="space-y-5">
                        {error && (
                            <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm flex items-center gap-2">
                                <div className="w-1.5 h-1.5 rounded-full bg-red-500" />
                                {error}
                            </div>
                        )}

                        <Input
                            label="Email"
                            icon={Mail}
                            type="email"
                            name="email"
                            value={formData.email}
                            onChange={handleChange}
                            required
                            placeholder="you@company.com"
                        />

                        <div className="space-y-1">
                            <Input
                                label="Password"
                                icon={Lock}
                                type="password"
                                name="password"
                                value={formData.password}
                                onChange={handleChange}
                                required
                                placeholder="Enter your password"
                            />
                            <div className="text-right">
                                <a href="#" className="text-xs text-primary-400 hover:text-primary-300 transition-colors">
                                    Forgot password?
                                </a>
                            </div>
                        </div>

                        <Button
                            type="submit"
                            variant="primary"
                            className="w-full mt-2"
                            isLoading={loading}
                        >
                            Log In <ArrowRight className="w-4 h-4" />
                        </Button>
                    </form>

                    <div className="mt-6 text-center text-sm text-dark-muted">
                        Don't have an account?{' '}
                        <Link to="/signup" className="text-primary-400 hover:text-primary-300 font-medium transition-colors">
                            Sign up
                        </Link>
                    </div>
                </Card>
            </div>
        </div>
    );
}
