-- Add explainability columns to predictions table
ALTER TABLE public.predictions
ADD COLUMN IF NOT EXISTS shap_values JSONB,
ADD COLUMN IF NOT EXISTS risk_percent DOUBLE PRECISION,
ADD COLUMN IF NOT EXISTS correlated_anomalies JSONB,
ADD COLUMN IF NOT EXISTS feature_importance JSONB,
ADD COLUMN IF NOT EXISTS anomaly_scores JSONB;

-- Comment on columns
COMMENT ON COLUMN public.predictions.shap_values IS 'SHAP feature importance values';
COMMENT ON COLUMN public.predictions.risk_percent IS 'Unified risk score (0-100)';
COMMENT ON COLUMN public.predictions.correlated_anomalies IS 'Groups of correlated sensor anomalies';
