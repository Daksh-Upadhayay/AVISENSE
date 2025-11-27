import { Layout } from '../components/layout/Layout';
import { Card } from '../components/ui/Card';

export default function Settings() {
    return (
        <Layout>
            <h1 className="text-3xl font-bold text-white mb-6">Settings</h1>
            <Card>
                <div className="text-center py-10">
                    <p className="text-dark-muted">User profile and application settings coming soon.</p>
                </div>
            </Card>
        </Layout>
    );
}
