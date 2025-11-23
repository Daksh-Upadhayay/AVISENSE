import React, { useEffect, useState } from 'react';
import { Download, ChevronDown, ChevronUp, Search, AlertTriangle, CheckCircle } from 'lucide-react';
import { getHistory } from '../services/api';
import styles from './History.module.css';

const History = () => {
    const [history, setHistory] = useState([]);
    const [loading, setLoading] = useState(true);
    const [expandedRow, setExpandedRow] = useState(null);
    const [searchTerm, setSearchTerm] = useState('');

    useEffect(() => {
        const fetchHistory = async () => {
            const data = await getHistory();
            setHistory(data);
            setLoading(false);
        };
        fetchHistory();
    }, []);

    const toggleRow = (index) => {
        setExpandedRow(expandedRow === index ? null : index);
    };

    const exportCSV = () => {
        if (history.length === 0) return;

        const headers = Object.keys(history[0]).join(',');
        const rows = history.map(row =>
            Object.values(row).map(val =>
                typeof val === 'object' ? JSON.stringify(val).replace(/,/g, ';') : val
            ).join(',')
        );

        const csvContent = "data:text/csv;charset=utf-8," + [headers, ...rows].join('\n');
        const encodedUri = encodeURI(csvContent);
        const link = document.createElement("a");
        link.setAttribute("href", encodedUri);
        link.setAttribute("download", "avisense_history.csv");
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };

    const filteredHistory = history.filter(item =>
        item.engine_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
        item.prediction.toLowerCase().includes(searchTerm.toLowerCase())
    );

    return (
        <div className={styles.page}>
            <div className={styles.header}>
                <h1 className={styles.title}>Prediction History</h1>
                <div className={styles.actions}>
                    <div className={styles.searchWrapper}>
                        <Search size={18} className={styles.searchIcon} />
                        <input
                            type="text"
                            placeholder="Search Engine ID or Status..."
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                            className={styles.searchInput}
                        />
                    </div>
                    <button onClick={exportCSV} className="btn btn-secondary">
                        <Download size={18} style={{ marginRight: '8px' }} />
                        Export CSV
                    </button>
                </div>
            </div>

            <div className={styles.tableContainer}>
                {loading ? (
                    <div className={styles.loading}>Loading history...</div>
                ) : filteredHistory.length === 0 ? (
                    <div className={styles.empty}>No records found.</div>
                ) : (
                    <table className={styles.table}>
                        <thead>
                            <tr>
                                <th>Timestamp</th>
                                <th>Engine ID</th>
                                <th>Status</th>
                                <th>Confidence</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {filteredHistory.map((item, index) => {
                                const isSafe = item.prediction === 'SAFE';
                                const isExpanded = expandedRow === index;

                                return (
                                    <React.Fragment key={index}>
                                        <tr
                                            className={`${styles.row} ${isExpanded ? styles.expanded : ''}`}
                                            onClick={() => toggleRow(index)}
                                        >
                                            <td>{new Date(item.timestamp).toLocaleString()}</td>
                                            <td className={styles.engineId}>{item.engine_id}</td>
                                            <td>
                                                <span className={`${styles.badge} ${isSafe ? styles.badgeSafe : styles.badgeDanger}`}>
                                                    {isSafe ? <CheckCircle size={14} /> : <AlertTriangle size={14} />}
                                                    {item.prediction}
                                                </span>
                                            </td>
                                            <td>{(item.probability * 100).toFixed(1)}%</td>
                                            <td>
                                                <button className={styles.expandBtn}>
                                                    {isExpanded ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                                                </button>
                                            </td>
                                        </tr>
                                        {isExpanded && (
                                            <tr className={styles.detailsRow}>
                                                <td colSpan="5">
                                                    <div className={styles.details}>
                                                        <div className={styles.detailSection}>
                                                            <h4>Input Telemetry</h4>
                                                            <div className={styles.detailGrid}>
                                                                {Object.entries(item).map(([key, value]) => {
                                                                    if (['prediction', 'probability', 'actions', 'top_features', 'timestamp', 'engine_id'].includes(key)) return null;
                                                                    return (
                                                                        <div key={key} className={styles.detailItem}>
                                                                            <span className={styles.detailLabel}>{key}:</span>
                                                                            <span className={styles.detailValue}>{value}</span>
                                                                        </div>
                                                                    );
                                                                })}
                                                            </div>
                                                        </div>
                                                        <div className={styles.detailSection}>
                                                            <h4>Model Explanation</h4>
                                                            <div className={styles.features}>
                                                                {item.top_features?.map((f, i) => (
                                                                    <div key={i} className={styles.featureTag}>
                                                                        {f.name}: {f.contribution > 0 ? '+' : ''}{f.contribution.toFixed(3)}
                                                                    </div>
                                                                ))}
                                                            </div>
                                                            <div className={styles.suggestedActions}>
                                                                <strong>Suggested Actions:</strong> {item.actions}
                                                            </div>
                                                        </div>
                                                    </div>
                                                </td>
                                            </tr>
                                        )}
                                    </React.Fragment>
                                );
                            })}
                        </tbody>
                    </table>
                )}
            </div>
        </div>
    );
};

export default History;
