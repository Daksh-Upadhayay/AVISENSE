-- Migration: Add RUL fields to predictions table
-- Version: 0005_add_rul_features
-- Description: Ensure all columns required for RUL prediction are present

ALTER TABLE public.predictions
ADD COLUMN IF NOT EXISTS model_family TEXT,
ADD COLUMN IF NOT EXISTS model_version TEXT,
ADD COLUMN IF NOT EXISTS rul_prediction DOUBLE PRECISION,
ADD COLUMN IF NOT EXISTS rul_uncertainty DOUBLE PRECISION,
ADD COLUMN IF NOT EXISTS explainability JSONB,
ADD COLUMN IF NOT EXISTS input_sequence JSONB;

-- Add index for RUL queries
CREATE INDEX IF NOT EXISTS idx_predictions_rul ON public.predictions(rul_prediction);
CREATE INDEX IF NOT EXISTS idx_predictions_model_family ON public.predictions(model_family);

COMMENT ON COLUMN public.predictions.rul_prediction IS 'Predicted Remaining Useful Life (cycles)';
COMMENT ON COLUMN public.predictions.rul_uncertainty IS 'Uncertainty/Variance of RUL prediction';
COMMENT ON COLUMN public.predictions.input_sequence IS 'Input sequence used for RUL prediction (JSON)';
