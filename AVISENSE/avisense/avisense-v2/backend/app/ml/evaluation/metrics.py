"""
Evaluation Metrics for Anomaly Detection and Classification

Provides comprehensive metrics for evaluating deep learning models.
"""

import numpy as np
from sklearn.metrics import (
    roc_auc_score, precision_recall_curve, auc,
    precision_score, recall_score, f1_score,
    confusion_matrix, roc_curve
)
from typing import Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class BinaryMetrics:
    """Metrics for binary classification (failure detection)."""
    
    @staticmethod
    def calculate(
        y_true: np.ndarray,
        y_pred: np.ndarray,
        y_scores: Optional[np.ndarray] = None
    ) -> Dict[str, float]:
        """
        Calculate binary classification metrics.
        
        Args:
            y_true: True labels (0/1)
            y_pred: Predicted labels (0/1)
            y_scores: Prediction scores/probabilities (optional)
            
        Returns:
            Dict of metrics
        """
        metrics = {}
        
        # Basic metrics
        metrics['precision'] = precision_score(y_true, y_pred, zero_division=0)
        metrics['recall'] = recall_score(y_true, y_pred, zero_division=0)
        metrics['f1'] = f1_score(y_true, y_pred, zero_division=0)
        
        # Confusion matrix
        tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
        metrics['true_positives'] = int(tp)
        metrics['false_positives'] = int(fp)
        metrics['true_negatives'] = int(tn)
        metrics['false_negatives'] = int(fn)
        metrics['fpr'] = fp / (fp + tn) if (fp + tn) > 0 else 0
        
        # Score-based metrics (if scores provided)
        if y_scores is not None:
            metrics['roc_auc'] = roc_auc_score(y_true, y_scores)
            
            # PR-AUC
            precision_curve, recall_curve, _ = precision_recall_curve(y_true, y_scores)
            metrics['pr_auc'] = auc(recall_curve, precision_curve)
            
            # FPR at 95% recall
            fpr, tpr, thresholds = roc_curve(y_true, y_scores)
            idx_95_recall = np.argmax(tpr >= 0.95)
            metrics['fpr_at_95_recall'] = float(fpr[idx_95_recall]) if idx_95_recall < len(fpr) else 1.0
        
        return metrics
    
    @staticmethod
    def precision_at_k(
        y_true: np.ndarray,
        y_scores: np.ndarray,
        k: int
    ) -> float:
        """
        Calculate precision at top-k predictions.
        
        Args:
            y_true: True labels
            y_scores: Prediction scores
            k: Number of top predictions
            
        Returns:
            Precision at k
        """
        # Get indices of top-k scores
        top_k_idx = np.argsort(y_scores)[-k:]
        
        # Calculate precision
        return np.mean(y_true[top_k_idx])
    
    @staticmethod
    def recall_at_k(
        y_true: np.ndarray,
        y_scores: np.ndarray,
        k: int
    ) -> float:
        """
        Calculate recall at top-k predictions.
        
        Args:
            y_true: True labels
            y_scores: Prediction scores
            k: Number of top predictions
            
        Returns:
            Recall at k
        """
        # Get indices of top-k scores
        top_k_idx = np.argsort(y_scores)[-k:]
        
        # Calculate recall
        n_positives = np.sum(y_true)
        if n_positives == 0:
            return 0.0
        
        return np.sum(y_true[top_k_idx]) / n_positives


class AnomalyMetrics:
    """Metrics for anomaly detection."""
    
    @staticmethod
    def calculate(
        y_true: np.ndarray,
        anomaly_scores: np.ndarray,
        threshold: Optional[float] = None
    ) -> Dict[str, float]:
        """
        Calculate anomaly detection metrics.
        
        Args:
            y_true: True labels (0=normal, 1=anomaly)
            anomaly_scores: Anomaly scores (higher = more anomalous)
            threshold: Optional threshold for binary classification
            
        Returns:
            Dict of metrics
        """
        metrics = {}
        
        # AUROC
        if len(np.unique(y_true)) > 1:
            metrics['auroc'] = roc_auc_score(y_true, anomaly_scores)
        else:
            metrics['auroc'] = 0.0
        
        # Precision at N (top 5%, 10%, 20%)
        for pct in [5, 10, 20]:
            n = max(1, int(len(y_true) * pct / 100))
            metrics[f'precision_at_{pct}pct'] = BinaryMetrics.precision_at_k(
                y_true, anomaly_scores, n
            )
        
        # If threshold provided, calculate binary metrics
        if threshold is not None:
            y_pred = (anomaly_scores >= threshold).astype(int)
            binary_metrics = BinaryMetrics.calculate(y_true, y_pred, anomaly_scores)
            metrics.update(binary_metrics)
        
        return metrics
    
    @staticmethod
    def find_optimal_threshold(
        y_true: np.ndarray,
        anomaly_scores: np.ndarray,
        metric: str = 'f1'
    ) -> Tuple[float, float]:
        """
        Find optimal threshold for anomaly detection.
        
        Args:
            y_true: True labels
            anomaly_scores: Anomaly scores
            metric: Metric to optimize ('f1', 'precision', 'recall')
            
        Returns:
            Tuple of (optimal_threshold, metric_value)
        """
        # Try different thresholds
        thresholds = np.percentile(anomaly_scores, np.arange(50, 100, 1))
        
        best_threshold = None
        best_score = 0
        
        for threshold in thresholds:
            y_pred = (anomaly_scores >= threshold).astype(int)
            
            if metric == 'f1':
                score = f1_score(y_true, y_pred, zero_division=0)
            elif metric == 'precision':
                score = precision_score(y_true, y_pred, zero_division=0)
            elif metric == 'recall':
                score = recall_score(y_true, y_pred, zero_division=0)
            else:
                raise ValueError(f"Unknown metric: {metric}")
            
            if score > best_score:
                best_score = score
                best_threshold = threshold
        
        return best_threshold, best_score


class RULMetrics:
    """Metrics for Remaining Useful Life regression."""
    
    @staticmethod
    def calculate(
        y_true: np.ndarray,
        y_pred: np.ndarray
    ) -> Dict[str, float]:
        """
        Calculate RUL regression metrics.
        
        Args:
            y_true: True RUL values
            y_pred: Predicted RUL values
            
        Returns:
            Dict of metrics
        """
        metrics = {}
        
        # Basic regression metrics
        errors = y_true - y_pred
        metrics['mae'] = float(np.mean(np.abs(errors)))
        metrics['rmse'] = float(np.sqrt(np.mean(errors ** 2)))
        
        # R-squared
        ss_res = np.sum(errors ** 2)
        ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
        metrics['r2'] = float(1 - (ss_res / ss_tot)) if ss_tot > 0 else 0.0
        
        # NASA scoring function (asymmetric)
        metrics['nasa_score'] = RULMetrics.nasa_score(y_true, y_pred)
        
        # Coverage within ±X cycles
        for threshold in [5, 10, 15, 20]:
            within_threshold = np.abs(errors) <= threshold
            metrics[f'coverage_within_{threshold}'] = float(np.mean(within_threshold))
        
        return metrics
    
    @staticmethod
    def nasa_score(y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """
        NASA turbofan RUL scoring function.
        
        Penalizes late predictions more than early predictions.
        """
        errors = y_pred - y_true
        
        # Asymmetric scoring
        scores = np.where(
            errors < 0,
            np.exp(-errors / 13) - 1,  # Late prediction (underestimate)
            np.exp(errors / 10) - 1     # Early prediction (overestimate)
        )
        
        return float(np.sum(scores))


def print_metrics_report(metrics: Dict[str, float], title: str = "Metrics Report"):
    """Pretty print metrics report."""
    print(f"\n{'='*60}")
    print(f"{title:^60}")
    print(f"{'='*60}")
    
    for key, value in metrics.items():
        if isinstance(value, float):
            print(f"{key:.<40} {value:.4f}")
        else:
            print(f"{key:.<40} {value}")
    
    print(f"{'='*60}\n")
