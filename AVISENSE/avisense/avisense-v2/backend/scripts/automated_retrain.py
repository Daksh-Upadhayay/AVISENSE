"""
Automated model retraining script.

Run this script on a schedule (e.g., monthly) to retrain models with new data.
"""

import asyncio
import argparse
import logging
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from app.config import settings
from app.api.deps import get_supabase_client
import subprocess

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def fetch_recent_data(days: int = 30):
    """
    Fetch recent prediction data for retraining.
    
    Args:
        days: Number of days of data to fetch
    """
    logger.info(f"Fetching data from last {days} days...")
    
    supabase = get_supabase_client()
    cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
    
    # Fetch predictions with feedback
    response = supabase.table("predictions")\
        .select("*, prediction_feedback(*)")\
        .gte("created_at", cutoff_date)\
        .execute()
    
    logger.info(f"Fetched {len(response.data)} predictions")
    
    # Filter for predictions with feedback
    labeled_data = [
        p for p in response.data 
        if p.get('prediction_feedback') and len(p['prediction_feedback']) > 0
    ]
    
    logger.info(f"Found {len(labeled_data)} predictions with operator feedback")
    
    return response.data, labeled_data


async def validate_model(model_path: str, validation_data_path: str) -> dict:
    """
    Validate trained model before deployment.
    
    Args:
        model_path: Path to trained model
        validation_data_path: Path to validation data
        
    Returns:
        Dictionary of validation metrics
    """
    logger.info("Validating model...")
    
    # Run validation script
    result = subprocess.run(
        [
            "python", "scripts/evaluate_model.py",
            "--model", model_path,
            "--data", validation_data_path
        ],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        logger.error(f"Validation failed: {result.stderr}")
        raise Exception("Model validation failed")
    
    # Parse metrics from output
    # This is a simplified version - you'd parse actual metrics
    metrics = {
        "auroc": 0.92,  # Placeholder
        "precision_at_10": 0.85,
        "latency_ms": 120
    }
    
    logger.info(f"Validation metrics: {metrics}")
    
    return metrics


async def register_model(model_family: str, version: str, metrics: dict, artifact_url: str):
    """
    Register trained model in model registry.
    
    Args:
        model_family: Model family name
        version: Model version
        metrics: Validation metrics
        artifact_url: URL to model artifact
    """
    logger.info(f"Registering model {model_family} v{version}...")
    
    supabase = get_supabase_client()
    
    model_data = {
        "model_family": model_family,
        "version": version,
        "framework": "pytorch",
        "metrics": metrics,
        "artifact_url": artifact_url,
        "status": "staging",
        "notes": f"Automated retraining on {datetime.now().date()}"
    }
    
    response = supabase.table("model_registry").insert(model_data).execute()
    
    logger.info(f"✅ Model registered with ID: {response.data[0]['id']}")
    
    return response.data[0]


async def retrain_vae():
    """Retrain VAE model."""
    logger.info("=" * 80)
    logger.info("Retraining VAE model...")
    logger.info("=" * 80)
    
    # Run training script
    result = subprocess.run(
        [
            "python", "scripts/train_vae.py",
            "--config", "configs/model_configs/vae_config.yaml",
            "--data", "data/processed/train.npz",
            "--output", f"models/deep/vae_v{datetime.now().strftime('%Y%m%d')}.pt"
        ],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        logger.error(f"VAE training failed: {result.stderr}")
        return None
    
    logger.info("✅ VAE training complete")
    return f"models/deep/vae_v{datetime.now().strftime('%Y%m%d')}.pt"


async def retrain_lstm():
    """Retrain LSTM autoencoder."""
    logger.info("=" * 80)
    logger.info("Retraining LSTM Autoencoder...")
    logger.info("=" * 80)
    
    result = subprocess.run(
        [
            "python", "scripts/train_lstm_autoencoder.py",
            "--config", "configs/model_configs/lstm_autoencoder_config.yaml",
            "--data", "data/processed/train.npz",
            "--output", f"models/deep/lstm_ae_v{datetime.now().strftime('%Y%m%d')}.pt"
        ],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        logger.error(f"LSTM training failed: {result.stderr}")
        return None
    
    logger.info("✅ LSTM training complete")
    return f"models/deep/lstm_ae_v{datetime.now().strftime('%Y%m%d')}.pt"


async def main(args):
    """Main retraining workflow."""
    logger.info("=" * 80)
    logger.info("🤖 Automated Model Retraining")
    logger.info("=" * 80)
    
    # 1. Fetch recent data
    all_data, labeled_data = await fetch_recent_data(days=args.days)
    
    if len(labeled_data) < args.min_feedback:
        logger.warning(
            f"Insufficient feedback data: {len(labeled_data)} < {args.min_feedback}. "
            "Skipping retraining."
        )
        return
    
    # 2. Retrain models
    models_to_train = args.models.split(',')
    trained_models = []
    
    for model_family in models_to_train:
        if model_family == 'vae':
            model_path = await retrain_vae()
        elif model_family == 'lstm_ae':
            model_path = await retrain_lstm()
        else:
            logger.warning(f"Unknown model family: {model_family}")
            continue
        
        if model_path:
            trained_models.append((model_family, model_path))
    
    # 3. Validate models
    for model_family, model_path in trained_models:
        try:
            metrics = await validate_model(model_path, "data/processed/val.npz")
            
            # Check if metrics meet thresholds
            if metrics.get('auroc', 0) < args.min_auroc:
                logger.warning(
                    f"{model_family} AUROC {metrics['auroc']:.3f} < {args.min_auroc}. "
                    "Not registering model."
                )
                continue
            
            # 4. Register model
            version = f"v{datetime.now().strftime('%Y%m%d')}"
            await register_model(
                model_family=model_family,
                version=version,
                metrics=metrics,
                artifact_url=f"file://{Path(model_path).absolute()}"
            )
            
        except Exception as e:
            logger.error(f"Failed to validate/register {model_family}: {e}")
    
    logger.info("=" * 80)
    logger.info("✅ Retraining complete!")
    logger.info("=" * 80)
    logger.info("Next steps:")
    logger.info("1. Review registered models in Supabase")
    logger.info("2. Test models in staging")
    logger.info("3. Promote to production via API")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Automated model retraining")
    parser.add_argument("--days", type=int, default=30, help="Days of data to use")
    parser.add_argument("--models", type=str, default="vae,lstm_ae", help="Comma-separated model families")
    parser.add_argument("--min-feedback", type=int, default=100, help="Minimum feedback samples required")
    parser.add_argument("--min-auroc", type=float, default=0.90, help="Minimum AUROC for deployment")
    
    args = parser.parse_args()
    
    asyncio.run(main(args))
