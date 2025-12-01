"""
Monitoring and Drift Detection Module

Tracks model performance, feature drift, and prediction patterns.
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from scipy import stats
import logging

logger = logging.getLogger(__name__)


class DriftDetector:
    """
    Detects distribution drift in features and predictions.
    """
    
    def __init__(self, baseline_data: Optional[Dict[str, np.ndarray]] = None):
        """
        Initialize drift detector.
        
        Args:
            baseline_data: Dictionary of feature_name -> array of baseline values
        """
        self.baseline_data = baseline_data or {}
        self.baseline_stats = {}
        
        if baseline_data:
            self._compute_baseline_stats()
    
    def _compute_baseline_stats(self):
        """Compute statistics for baseline data."""
        for feature, values in self.baseline_data.items():
            self.baseline_stats[feature] = {
                'mean': np.mean(values),
                'std': np.std(values),
                'min': np.min(values),
                'max': np.max(values),
                'percentiles': np.percentile(values, [25, 50, 75, 95])
            }
    
    def compute_psi(
        self,
        baseline: np.ndarray,
        current: np.ndarray,
        bins: int = 10
    ) -> float:
        """
        Compute Population Stability Index (PSI).
        
        PSI measures the shift in distribution between two datasets.
        PSI < 0.1: No significant change
        0.1 <= PSI < 0.25: Moderate change
        PSI >= 0.25: Significant change (action required)
        
        Args:
            baseline: Baseline distribution
            current: Current distribution
            bins: Number of bins for discretization
            
        Returns:
            PSI score
        """
        try:
            # Create bins based on baseline
            breakpoints = np.percentile(baseline, np.linspace(0, 100, bins + 1))
            breakpoints = np.unique(breakpoints)  # Remove duplicates
            
            # Count observations in each bin
            baseline_counts = np.histogram(baseline, bins=breakpoints)[0]
            current_counts = np.histogram(current, bins=breakpoints)[0]
            
            # Convert to percentages
            baseline_pct = baseline_counts / len(baseline)
            current_pct = current_counts / len(current)
            
            # Avoid division by zero
            baseline_pct = np.where(baseline_pct == 0, 0.0001, baseline_pct)
            current_pct = np.where(current_pct == 0, 0.0001, current_pct)
            
            # Calculate PSI
            psi = np.sum((current_pct - baseline_pct) * np.log(current_pct / baseline_pct))
            
            return float(psi)
            
        except Exception as e:
            logger.error(f"PSI calculation failed: {e}")
            return 0.0
    
    def kolmogorov_smirnov_test(
        self,
        baseline: np.ndarray,
        current: np.ndarray
    ) -> Tuple[float, float]:
        """
        Perform Kolmogorov-Smirnov test for distribution shift.
        
        Args:
            baseline: Baseline distribution
            current: Current distribution
            
        Returns:
            (statistic, p_value)
        """
        try:
            statistic, p_value = stats.ks_2samp(baseline, current)
            return float(statistic), float(p_value)
        except Exception as e:
            logger.error(f"KS test failed: {e}")
            return 0.0, 1.0
    
    def detect_drift(
        self,
        feature_name: str,
        current_data: np.ndarray,
        psi_threshold: float = 0.25,
        ks_pvalue_threshold: float = 0.05
    ) -> Dict:
        """
        Detect drift for a specific feature.
        
        Args:
            feature_name: Name of the feature
            current_data: Current feature values
            psi_threshold: PSI threshold for drift alert
            ks_pvalue_threshold: KS test p-value threshold
            
        Returns:
            Dictionary with drift metrics and alert status
        """
        if feature_name not in self.baseline_data:
            logger.warning(f"No baseline data for feature: {feature_name}")
            return {"alert": False, "reason": "no_baseline"}
        
        baseline = self.baseline_data[feature_name]
        
        # Compute PSI
        psi = self.compute_psi(baseline, current_data)
        
        # Perform KS test
        ks_stat, ks_pvalue = self.kolmogorov_smirnov_test(baseline, current_data)
        
        # Compute mean and std shifts
        baseline_mean = self.baseline_stats[feature_name]['mean']
        baseline_std = self.baseline_stats[feature_name]['std']
        current_mean = np.mean(current_data)
        current_std = np.std(current_data)
        
        mean_shift = abs(current_mean - baseline_mean) / (baseline_std + 1e-8)
        std_shift = abs(current_std - baseline_std) / (baseline_std + 1e-8)
        
        # Determine if drift alert should be triggered
        alert = (psi >= psi_threshold) or (ks_pvalue < ks_pvalue_threshold)
        
        result = {
            "feature_name": feature_name,
            "psi_score": psi,
            "ks_statistic": ks_stat,
            "ks_pvalue": ks_pvalue,
            "mean_shift": mean_shift,
            "std_shift": std_shift,
            "alert_triggered": alert,
            "baseline_mean": baseline_mean,
            "current_mean": current_mean,
            "baseline_std": baseline_std,
            "current_std": current_std
        }
        
        if alert:
            logger.warning(
                f"🚨 Drift detected for {feature_name}: "
                f"PSI={psi:.3f}, KS p-value={ks_pvalue:.3f}"
            )
        
        return result
    
    def detect_all_features(
        self,
        current_features: Dict[str, np.ndarray],
        psi_threshold: float = 0.25
    ) -> List[Dict]:
        """
        Detect drift across all features.
        
        Args:
            current_features: Dictionary of feature_name -> current values
            psi_threshold: PSI threshold
            
        Returns:
            List of drift results for each feature
        """
        results = []
        
        for feature_name, current_data in current_features.items():
            result = self.detect_drift(feature_name, current_data, psi_threshold)
            results.append(result)
        
        return results


class PredictionMonitor:
    """
    Monitors prediction statistics and performance.
    """
    
    def __init__(self, supabase_client):
        self.supabase = supabase_client
    
    async def log_prediction_stats(
        self,
        date: datetime,
        model_family: str,
        model_version: str,
        predictions: List[Dict]
    ):
        """
        Aggregate and log daily prediction statistics.
        
        Args:
            date: Date for the stats
            model_family: Model family name
            model_version: Model version
            predictions: List of prediction results
        """
        try:
            if not predictions:
                return
            
            # Extract metrics
            anomaly_scores = [p.get('anomaly_score_normalized', 0) for p in predictions if p.get('anomaly_score_normalized')]
            risk_percents = [p.get('risk_percent', 0) for p in predictions if p.get('risk_percent')]
            latencies = [p.get('inference_latency_ms', 0) for p in predictions if p.get('inference_latency_ms')]
            
            failure_count = sum(1 for p in predictions if p.get('prediction') == 'PRONE TO FAILURE')
            safe_count = sum(1 for p in predictions if p.get('prediction') == 'SAFE')
            error_count = sum(1 for p in predictions if p.get('error'))
            
            stats = {
                "date": date.date().isoformat(),
                "model_family": model_family,
                "model_version": model_version,
                "total_predictions": len(predictions),
                "failure_predictions": failure_count,
                "safe_predictions": safe_count,
                "error_count": error_count,
                "timeout_count": 0  # Would need to track this separately
            }
            
            if anomaly_scores:
                stats["avg_anomaly_score"] = float(np.mean(anomaly_scores))
                stats["p50_anomaly_score"] = float(np.percentile(anomaly_scores, 50))
                stats["p95_anomaly_score"] = float(np.percentile(anomaly_scores, 95))
            
            if risk_percents:
                stats["avg_risk_percent"] = float(np.mean(risk_percents))
                stats["p50_risk_percent"] = float(np.percentile(risk_percents, 50))
                stats["p95_risk_percent"] = float(np.percentile(risk_percents, 95))
            
            if latencies:
                stats["avg_latency_ms"] = float(np.mean(latencies))
                stats["p95_latency_ms"] = float(np.percentile(latencies, 95))
            
            # Upsert to database
            self.supabase.table("prediction_stats").upsert(stats).execute()
            
            logger.info(f"✅ Logged stats for {date.date()}: {len(predictions)} predictions")
            
        except Exception as e:
            logger.error(f"Failed to log prediction stats: {e}")
    
    async def check_anomaly_alerts(self, days: int = 7) -> List[Dict]:
        """
        Check for anomalous prediction patterns.
        
        Returns alerts if:
        - Sudden spike in failure rate
        - Unusual increase in anomaly scores
        - High error rate
        
        Args:
            days: Number of days to analyze
            
        Returns:
            List of alerts
        """
        try:
            # Fetch recent stats
            response = self.supabase.table("prediction_stats")\
                .select("*")\
                .gte("date", (datetime.now() - timedelta(days=days)).date().isoformat())\
                .order("date", desc=True)\
                .execute()
            
            if not response.data or len(response.data) < 2:
                return []
            
            stats = response.data
            alerts = []
            
            # Calculate baseline (average of last 7 days excluding today)
            baseline_stats = stats[1:]  # Exclude most recent
            if not baseline_stats:
                return []
            
            avg_failure_rate = np.mean([
                s['failure_predictions'] / max(s['total_predictions'], 1)
                for s in baseline_stats
            ])
            
            avg_anomaly_score = np.mean([
                s.get('avg_anomaly_score', 0)
                for s in baseline_stats
                if s.get('avg_anomaly_score')
            ])
            
            # Check today's stats
            today = stats[0]
            today_failure_rate = today['failure_predictions'] / max(today['total_predictions'], 1)
            today_anomaly_score = today.get('avg_anomaly_score', 0)
            
            # Alert if failure rate > 2x baseline
            if today_failure_rate > avg_failure_rate * 2 and today_failure_rate > 0.3:
                alerts.append({
                    "type": "high_failure_rate",
                    "severity": "high",
                    "message": f"Failure rate spike: {today_failure_rate:.1%} (baseline: {avg_failure_rate:.1%})",
                    "date": today['date']
                })
            
            # Alert if anomaly score > 2σ from baseline
            if avg_anomaly_score > 0 and today_anomaly_score > avg_anomaly_score * 1.5:
                alerts.append({
                    "type": "high_anomaly_score",
                    "severity": "medium",
                    "message": f"Anomaly score elevated: {today_anomaly_score:.3f} (baseline: {avg_anomaly_score:.3f})",
                    "date": today['date']
                })
            
            # Alert if error rate > 5%
            error_rate = today['error_count'] / max(today['total_predictions'], 1)
            if error_rate > 0.05:
                alerts.append({
                    "type": "high_error_rate",
                    "severity": "critical",
                    "message": f"High error rate: {error_rate:.1%}",
                    "date": today['date']
                })
            
            return alerts
            
        except Exception as e:
            logger.error(f"Failed to check anomaly alerts: {e}")
            return []
