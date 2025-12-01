-- Migration: Add Deep Learning Models Support
-- This migration adds tables and columns to support deep learning models
-- (autoencoders, LSTM, RUL regression) and their inference outputs.

-- ============================================================================
-- Models Table: Store metadata for all registered models
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.models (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_family TEXT NOT NULL,  -- 'lstm_autoencoder', 'rul_lstm', 'random_forest', etc.
    version TEXT NOT NULL,
    framework TEXT,  -- 'pytorch', 'tensorflow', 'onnx', 'sklearn'
    artifact_url TEXT,  -- Supabase Storage or S3 URL
    input_shape JSONB,  -- e.g., {"window_length": 64, "n_features": 14}
    window_length INTEGER,
    sequence_stride INTEGER,
    trained_on TIMESTAMPTZ,
    metrics JSONB,  -- e.g., {"auc": 0.95, "rmse": 12.3, "recall": 0.89}
    hyperparameters JSONB,  -- Training config
    status TEXT DEFAULT 'staging',  -- 'staging', 'production', 'deprecated'
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID REFERENCES auth.users(id),
    UNIQUE(model_family, version)
);

-- Index for fast lookups
CREATE INDEX idx_models_family_version ON public.models(model_family, version);
CREATE INDEX idx_models_status ON public.models(status);

-- Comment on table
COMMENT ON TABLE public.models IS 'Registry of all ML models (RF, deep learning, etc.)';

-- ============================================================================
-- Extend Predictions Table: Add deep model outputs
-- ============================================================================

ALTER TABLE public.predictions
ADD COLUMN IF NOT EXISTS model_family TEXT DEFAULT 'random_forest',
ADD COLUMN IF NOT EXISTS model_version TEXT,
ADD COLUMN IF NOT EXISTS anomaly_score DOUBLE PRECISION,  -- 0-1 from autoencoder
ADD COLUMN IF NOT EXISTS reconstruction_errors JSONB,  -- per-feature reconstruction errors
ADD COLUMN IF NOT EXISTS rul_prediction DOUBLE PRECISION,  -- remaining useful life (cycles)
ADD COLUMN IF NOT EXISTS rul_uncertainty DOUBLE PRECISION,  -- RUL confidence interval
ADD COLUMN IF NOT EXISTS explainability JSONB;  -- shap/ig values for deep models

-- Indexes for filtering
CREATE INDEX IF NOT EXISTS idx_predictions_model_family ON public.predictions(model_family);
CREATE INDEX IF NOT EXISTS idx_predictions_anomaly_score ON public.predictions(anomaly_score);
CREATE INDEX IF NOT EXISTS idx_predictions_rul ON public.predictions(rul_prediction);

-- Comments
COMMENT ON COLUMN public.predictions.model_family IS 'Model family used for this prediction';
COMMENT ON COLUMN public.predictions.anomaly_score IS 'Anomaly score from autoencoder (0-1)';
COMMENT ON COLUMN public.predictions.reconstruction_errors IS 'Per-feature reconstruction errors from AE';
COMMENT ON COLUMN public.predictions.rul_prediction IS 'Predicted remaining useful life in cycles';
COMMENT ON COLUMN public.predictions.explainability IS 'Deep model explainability (SHAP, IG, etc.)';

-- ============================================================================
-- Model Inferences Table: Detailed logging for ensemble predictions
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.model_inferences (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    prediction_id UUID REFERENCES public.predictions(id) ON DELETE CASCADE,
    model_id UUID REFERENCES public.models(id),
    inference_time_ms DOUBLE PRECISION,  -- Latency for this model
    output JSONB,  -- Full model output
    error TEXT,  -- Error message if inference failed
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_model_inferences_prediction ON public.model_inferences(prediction_id);
CREATE INDEX idx_model_inferences_model ON public.model_inferences(model_id);
CREATE INDEX idx_model_inferences_created_at ON public.model_inferences(created_at);

-- Comment
COMMENT ON TABLE public.model_inferences IS 'Detailed logs for individual model inferences in ensemble';

-- ============================================================================
-- Row-Level Security (RLS) Policies
-- ============================================================================

-- Enable RLS
ALTER TABLE public.models ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.model_inferences ENABLE ROW LEVEL SECURITY;

-- Models: Anyone can view, only admins can modify
CREATE POLICY "Users can view models" ON public.models
    FOR SELECT USING (true);

CREATE POLICY "Admins can insert models" ON public.models
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM auth.users
            WHERE id = auth.uid()
            -- Add admin role check here if you have role-based access
        )
    );

CREATE POLICY "Admins can update models" ON public.models
    FOR UPDATE USING (
        EXISTS (
            SELECT 1 FROM auth.users
            WHERE id = auth.uid()
        )
    );

-- Model Inferences: Users can view their own inferences
CREATE POLICY "Users can view their inferences" ON public.model_inferences
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.predictions p
            WHERE p.id = model_inferences.prediction_id
            AND p.created_by = auth.uid()
        )
    );

CREATE POLICY "System can insert inferences" ON public.model_inferences
    FOR INSERT WITH CHECK (true);

-- ============================================================================
-- Functions & Triggers
-- ============================================================================

-- Update timestamp trigger for models table
CREATE OR REPLACE FUNCTION update_models_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_models_timestamp
    BEFORE UPDATE ON public.models
    FOR EACH ROW
    EXECUTE FUNCTION update_models_updated_at();

-- ============================================================================
-- Seed Data: Register existing RandomForest model
-- ============================================================================

INSERT INTO public.models (
    model_family,
    version,
    framework,
    artifact_url,
    metrics,
    status,
    trained_on
) VALUES (
    'random_forest',
    'v1.2',
    'sklearn',
    'models/avisense_model_cmapss.joblib',
    '{"safe_recall": 0.976, "failure_recall": 0.869, "auc": 0.92}',
    'production',
    NOW()
) ON CONFLICT (model_family, version) DO NOTHING;

-- ============================================================================
-- Verification Queries
-- ============================================================================

-- Verify tables created
DO $$
BEGIN
    RAISE NOTICE 'Migration complete!';
    RAISE NOTICE 'Models table: %', (SELECT COUNT(*) FROM public.models);
    RAISE NOTICE 'New prediction columns: model_family, anomaly_score, rul_prediction, etc.';
END $$;
