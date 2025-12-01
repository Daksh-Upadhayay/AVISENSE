from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, List
from datetime import datetime, timedelta
from app.api.deps import get_current_user, get_supabase_client
from app.ml.monitoring import DriftDetector, PredictionMonitor
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/monitoring/stats")
async def get_prediction_stats(
    days: int = 30,
    model_family: Optional[str] = None,
    user=Depends(get_current_user),
    supabase=Depends(get_supabase_client)
):
    """
    Get aggregated prediction statistics for monitoring.
    
    Args:
        days: Number of days to retrieve
        model_family: Optional filter by model family
    """
    try:
        query = supabase.table("prediction_stats")\
            .select("*")\
            .gte("date", (datetime.now() - timedelta(days=days)).date().isoformat())\
            .order("date", desc=True)
        
        if model_family:
            query = query.eq("model_family", model_family)
        
        response = query.execute()
        
        return {
            "stats": response.data,
            "period_days": days
        }
        
    except Exception as e:
        logger.error(f"Failed to get prediction stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/monitoring/alerts")
async def get_alerts(
    days: int = 7,
    user=Depends(get_current_user),
    supabase=Depends(get_supabase_client)
):
    """
    Get active monitoring alerts.
    
    Checks for:
    - Sudden spikes in failure rate
    - Elevated anomaly scores
    - High error rates
    """
    try:
        monitor = PredictionMonitor(supabase)
        alerts = await monitor.check_anomaly_alerts(days=days)
        
        return {
            "alerts": alerts,
            "count": len(alerts),
            "checked_period_days": days
        }
        
    except Exception as e:
        logger.error(f"Failed to get alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/monitoring/drift")
async def get_drift_metrics(
    days: int = 30,
    user=Depends(get_current_user),
    supabase=Depends(get_supabase_client)
):
    """
    Get feature drift metrics.
    
    Shows PSI scores and distribution shifts for all features.
    """
    try:
        query = supabase.table("drift_metrics")\
            .select("*")\
            .gte("date", (datetime.now() - timedelta(days=days)).date().isoformat())\
            .order("date", desc=True)
        
        response = query.execute()
        
        # Group by feature
        drift_by_feature = {}
        for metric in response.data:
            feature = metric['feature_name']
            if feature not in drift_by_feature:
                drift_by_feature[feature] = []
            drift_by_feature[feature].append(metric)
        
        # Find features with alerts
        alerted_features = [
            feature for feature, metrics in drift_by_feature.items()
            if any(m.get('alert_triggered') for m in metrics)
        ]
        
        return {
            "drift_metrics": response.data,
            "drift_by_feature": drift_by_feature,
            "alerted_features": alerted_features,
            "period_days": days
        }
        
    except Exception as e:
        logger.error(f"Failed to get drift metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/monitoring/health")
async def get_system_health(
    user=Depends(get_current_user),
    supabase=Depends(get_supabase_client)
):
    """
    Get overall system health status.
    
    Returns:
    - Active alerts count
    - Recent error rate
    - Model status
    - Drift status
    """
    try:
        # Get recent alerts
        monitor = PredictionMonitor(supabase)
        alerts = await monitor.check_anomaly_alerts(days=1)
        
        # Get today's stats
        today_response = supabase.table("prediction_stats")\
            .select("*")\
            .eq("date", datetime.now().date().isoformat())\
            .execute()
        
        today_stats = today_response.data[0] if today_response.data else None
        
        # Get drift alerts
        drift_response = supabase.table("drift_metrics")\
            .select("*")\
            .eq("alert_triggered", True)\
            .gte("date", (datetime.now() - timedelta(days=7)).date().isoformat())\
            .execute()
        
        drift_alerts = len(drift_response.data)
        
        # Get active models
        models_response = supabase.table("model_registry")\
            .select("model_family, version")\
            .eq("status", "production")\
            .execute()
        
        # Determine overall health
        critical_alerts = [a for a in alerts if a.get('severity') == 'critical']
        health_status = "healthy"
        
        if critical_alerts or drift_alerts > 5:
            health_status = "critical"
        elif alerts or drift_alerts > 0:
            health_status = "warning"
        
        return {
            "status": health_status,
            "alerts": {
                "total": len(alerts),
                "critical": len(critical_alerts),
                "details": alerts
            },
            "drift_alerts": drift_alerts,
            "today_stats": today_stats,
            "active_models": models_response.data,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get system health: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/monitoring/comparison")
async def get_model_comparison(
    model_a: str,
    model_b: str,
    days: int = 30,
    user=Depends(get_current_user),
    supabase=Depends(get_supabase_client)
):
    """
    Compare performance of two models.
    
    Used for A/B testing and canary deployments.
    """
    try:
        # Get stats for both models
        start_date = (datetime.now() - timedelta(days=days)).date().isoformat()
        
        model_a_response = supabase.table("prediction_stats")\
            .select("*")\
            .eq("model_family", model_a)\
            .gte("date", start_date)\
            .execute()
        
        model_b_response = supabase.table("prediction_stats")\
            .select("*")\
            .eq("model_family", model_b)\
            .gte("date", start_date)\
            .execute()
        
        # Get comparison records
        comparison_response = supabase.table("model_comparison")\
            .select("*")\
            .or_(f"model_a.eq.{model_a},model_b.eq.{model_a}")\
            .or_(f"model_a.eq.{model_b},model_b.eq.{model_b}")\
            .execute()
        
        return {
            "model_a": {
                "name": model_a,
                "stats": model_a_response.data
            },
            "model_b": {
                "name": model_b,
                "stats": model_b_response.data
            },
            "comparisons": comparison_response.data,
            "period_days": days
        }
        
    except Exception as e:
        logger.error(f"Failed to compare models: {e}")
        raise HTTPException(status_code=500, detail=str(e))
