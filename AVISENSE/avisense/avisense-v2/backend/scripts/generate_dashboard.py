import joblib
from pathlib import Path
import json
from datetime import datetime
import pandas as pd

def generate_dashboard():
    print("📊 Generating Model Health Dashboard...")
    
    models_dir = Path("backend/app/ml/models")
    metadata_path = models_dir / "model_metadata_v2.0.0.joblib"
    
    if not metadata_path.exists():
        print(f"❌ Metadata not found at {metadata_path}. Run training first.")
        return
        
    metadata = joblib.load(metadata_path)
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Avisense Model Health Dashboard</title>
        <style>
            body {{ font-family: 'Inter', sans-serif; margin: 0; padding: 20px; background: #f4f4f9; color: #333; }}
            .container {{ max-width: 1000px; margin: 0 auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
            h1 {{ color: #2c3e50; border-bottom: 2px solid #eee; padding-bottom: 10px; }}
            h2 {{ color: #34495e; margin-top: 30px; }}
            .metric-card {{ background: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 4px solid #3498db; margin-bottom: 10px; }}
            .metric-value {{ font-size: 24px; font-weight: bold; color: #2c3e50; }}
            .metric-label {{ font-size: 14px; color: #7f8c8d; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
            th, td {{ text-align: left; padding: 12px; border-bottom: 1px solid #eee; }}
            th {{ background-color: #f8f9fa; color: #2c3e50; }}
            .status-badge {{ background: #2ecc71; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🛡️ Avisense Model Health Dashboard</h1>
            
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <strong>Version:</strong> {metadata.get('version', 'N/A')}
                    <span class="status-badge">ACTIVE</span>
                </div>
                <div>
                    <strong>Trained:</strong> {metadata.get('train_date', 'N/A')}
                </div>
            </div>
            
            <h2>📈 Performance Metrics</h2>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                <div class="metric-card">
                    <div class="metric-label">RUL Mean Absolute Error (MAE)</div>
                    <div class="metric-value">{metadata.get('rul_metrics', {}).get('mae', 'N/A'):.4f} cycles</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Classifier Brier Score</div>
                    <div class="metric-value">{metadata.get('cls_metrics', {}).get('brier_score', 'N/A'):.4f}</div>
                    <div style="font-size: 12px; color: #666;">(Lower is better, 0.0 = Perfect, 0.25 = Random)</div>
                </div>
            </div>
            
            <h2>⚙️ Model Parameters</h2>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                <div>
                    <h3>RUL Model (LSTM)</h3>
                    <table>
                        <tr><th>Parameter</th><th>Value</th></tr>
                        {''.join(f'<tr><td>{k}</td><td>{v}</td></tr>' for k, v in metadata.get('rul_params', {}).items())}
                    </table>
                </div>
                <div>
                    <h3>Classifier (RandomForest)</h3>
                    <table>
                        <tr><th>Parameter</th><th>Value</th></tr>
                        {''.join(f'<tr><td>{k}</td><td>{v}</td></tr>' for k, v in metadata.get('cls_params', {}).items())}
                    </table>
                </div>
            </div>
            
            <h2>🔍 Features Used</h2>
            <div style="background: #f8f9fa; padding: 15px; border-radius: 8px;">
                <code>{', '.join(metadata.get('features', []))}</code>
            </div>
            
            <div style="margin-top: 40px; text-align: center; color: #95a5a6; font-size: 12px;">
                Generated automatically by Avisense ML Pipeline
            </div>
        </div>
    </body>
    </html>
    """
    
    output_path = Path("backend/static/dashboard.html")
    output_path.parent.mkdir(exist_ok=True)
    
    with open(output_path, "w") as f:
        f.write(html_content)
        
    print(f"✅ Dashboard generated at {output_path}")

if __name__ == "__main__":
    generate_dashboard()
