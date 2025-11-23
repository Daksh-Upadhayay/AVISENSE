import React, { useEffect, useState } from 'react';
import { Filter, RefreshCw } from 'lucide-react';
import TimeSeriesChart from '../components/TimeSeriesChart';
import FormInput from '../components/FormInput';
import { getDiagnosticsData } from '../services/api';
import styles from './Diagnostics.module.css';

const Diagnostics = () => {
    const [data, setData] = useState([]);
    const [loading, setLoading] = useState(true);
    const [engineId, setEngineId] = useState('ENG-123');
    const [dateRange, setDateRange] = useState('30');

    const fetchData = async () => {
        setLoading(true);
        const result = await getDiagnosticsData(engineId);
        setData(result);
        setLoading(false);
    };

    useEffect(() => {
        fetchData();
    }, []);

    const handleRefresh = () => {
        fetchData();
    };

    return (
        <div className={styles.page}>
            <div className={styles.header}>
                <h1 className={styles.title}>Diagnostics Dashboard</h1>
                <div className={styles.controls}>
                    <div className={styles.filterGroup}>
                        <FormInput
                            name="engineId"
                            placeholder="Engine ID"
                            value={engineId}
                            onChange={(e) => setEngineId(e.target.value)}
                            style={{ marginBottom: 0, width: '150px' }}
                        />
                        <select
                            className={styles.select}
                            value={dateRange}
                            onChange={(e) => setDateRange(e.target.value)}
                        >
                            <option value="7">Last 7 Days</option>
                            <option value="30">Last 30 Days</option>
                            <option value="90">Last 3 Months</option>
                        </select>
                    </div>
                    <button onClick={handleRefresh} className="btn btn-secondary">
                        <RefreshCw size={18} className={loading ? styles.spinning : ''} />
                        Refresh
                    </button>
                </div>
            </div>

            {loading ? (
                <div className={styles.loading}>Loading diagnostic data...</div>
            ) : (
                <div className={styles.grid}>
                    <div className={styles.chartCard}>
                        <TimeSeriesChart
                            title="Temperature Trend (°C)"
                            data={data}
                            dataKey="temperature"
                            color="#ef4444"
                            unit="°C"
                        />
                    </div>
                    <div className={styles.chartCard}>
                        <TimeSeriesChart
                            title="RPM History"
                            data={data}
                            dataKey="rpm"
                            color="#3b82f6"
                            unit=" RPM"
                        />
                    </div>
                    <div className={styles.chartCard}>
                        <TimeSeriesChart
                            title="Vibration Levels (RMS)"
                            data={data}
                            dataKey="vibration"
                            color="#f59e0b"
                        />
                    </div>
                    <div className={styles.chartCard}>
                        <TimeSeriesChart
                            title="Oil Pressure (PSI)"
                            data={data}
                            dataKey="oilPressure"
                            color="#10b981"
                            unit=" PSI"
                        />
                    </div>
                </div>
            )}
        </div>
    );
};

export default Diagnostics;
