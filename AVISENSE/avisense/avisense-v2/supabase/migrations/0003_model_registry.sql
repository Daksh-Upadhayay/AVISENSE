-- Model Registry and Production Integration Tables
-- Migration: 0003_model_registry.sql

-- =====================================================
-- 1. Model Registry Table
-- =====================================================
CREATE TABLE IF NOT EXISTS public.model_registry (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_family TEXT NOT NULL CHECK (model_family IN ('random_forest', 'dense_ae', 'lstm_ae', 'vae', 'rul_lstm', 'rul_gru')),
    version TEXT NOT NULL,
    artifact_url TEXT,
    framework TEXT CHECK (framework IN ('sklearn', 'pytorch', 'tensorflow', 'onnx')),
    input_shape JSONB,
    window_length INTEGER,
    sequence_stride INTEGER,
    metrics JSONB, -- {auroc: 0.93, precision_at_10: 0.87, rmse: 12.5}
    config JSONB, -- Training configuration
    status TEXT NOT NULL DEFAULT 'staging' CHECK (status IN ('staging', 'production', 'deprecated', 'failed')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID REFERENCES auth.users(id),
    promoted_at TIMESTAMPTZ,
    promoted_by UUID REFERENCES auth.users(id),
    deprecated_at TIMESTAMPTZ,
    notes TEXT,
    UNIQUE(model_family, version)
);

-- Index for quick lookups
CREATE INDEX idx_model_registry_status ON public.model_registry(status);
CREATE INDEX idx_model_registry_family ON public.model_registry(model_family);
CREATE INDEX idx_model_registry_created ON public.model_registry(created_at DESC);

-- RLS Policies
ALTER TABLE public.model_registry ENABLE ROW LEVEL SECURITY;

-- Authenticated users can read all models
CREATE POLICY "Authenticated users can read models"
    ON public.model_registry FOR SELECT
    TO authenticated
    USING (true);

-- Only admins can insert/update models (you can adjust this based on your needs)
CREATE POLICY "Service role can manage models"
    ON public.model_registry FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- =====================================================
-- 2. Prediction Stats Table (for monitoring)
-- =====================================================
CREATE TABLE IF NOT EXISTS public.prediction_stats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    date DATE NOT NULL,
    model_family TEXT NOT NULL,
    model_version TEXT,
    total_predictions INTEGER DEFAULT 0,
    failure_predictions INTEGER DEFAULT 0,
    safe_predictions INTEGER DEFAULT 0,
    avg_anomaly_score FLOAT,
    p50_anomaly_score FLOAT,
    p95_anomaly_score FLOAT,
    avg_risk_percent FLOAT,
    p50_risk_percent FLOAT,
    p95_risk_percent FLOAT,
    avg_latency_ms FLOAT,
    p95_latency_ms FLOAT,
    error_count INTEGER DEFAULT 0,
    timeout_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(date, model_family, model_version)
);

CREATE INDEX idx_prediction_stats_date ON public.prediction_stats(date DESC);
CREATE INDEX idx_prediction_stats_family ON public.prediction_stats(model_family);

ALTER TABLE public.prediction_stats ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Authenticated users can read stats"
    ON public.prediction_stats FOR SELECT
    TO authenticated
    USING (true);

CREATE POLICY "Service role can manage stats"
    ON public.prediction_stats FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- =====================================================
-- 3. Model Comparison Table (for A/B testing)
-- =====================================================
CREATE TABLE IF NOT EXISTS public.model_comparison (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_a TEXT NOT NULL,
    model_b TEXT NOT NULL,
    comparison_start TIMESTAMPTZ NOT NULL,
    comparison_end TIMESTAMPTZ,
    metric_name TEXT NOT NULL,
    model_a_value FLOAT,
    model_b_value FLOAT,
    sample_size INTEGER,
    statistical_significance FLOAT, -- p-value
    winner TEXT CHECK (winner IN ('model_a', 'model_b', 'tie', 'inconclusive')),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_model_comparison_dates ON public.model_comparison(comparison_start DESC);

ALTER TABLE public.model_comparison ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Authenticated users can read comparisons"
    ON public.model_comparison FOR SELECT
    TO authenticated
    USING (true);

CREATE POLICY "Service role can manage comparisons"
    ON public.model_comparison FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- =====================================================
-- 4. Prediction Feedback Table (HITL)
-- =====================================================
CREATE TABLE IF NOT EXISTS public.prediction_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prediction_id UUID NOT NULL REFERENCES public.predictions(id) ON DELETE CASCADE,
    feedback_type TEXT NOT NULL CHECK (feedback_type IN ('correct', 'false_positive', 'false_negative', 'uncertain')),
    operator_notes TEXT,
    actual_outcome TEXT, -- What actually happened
    created_by UUID REFERENCES auth.users(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_feedback_prediction ON public.prediction_feedback(prediction_id);
CREATE INDEX idx_feedback_type ON public.prediction_feedback(feedback_type);
CREATE INDEX idx_feedback_created ON public.prediction_feedback(created_at DESC);

ALTER TABLE public.prediction_feedback ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read their own feedback"
    ON public.prediction_feedback FOR SELECT
    TO authenticated
    USING (created_by = auth.uid());

CREATE POLICY "Users can insert feedback"
    ON public.prediction_feedback FOR INSERT
    TO authenticated
    WITH CHECK (created_by = auth.uid());

CREATE POLICY "Service role can manage feedback"
    ON public.prediction_feedback FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- =====================================================
-- 5. Extend predictions table with provenance
-- =====================================================
ALTER TABLE public.predictions
ADD COLUMN IF NOT EXISTS model_provenance JSONB; -- {primary: 'vae_v1', fallback: false, shadow: 'vae_v2'}

ALTER TABLE public.predictions
ADD COLUMN IF NOT EXISTS inference_latency_ms FLOAT;

ALTER TABLE public.predictions
ADD COLUMN IF NOT EXISTS ensemble_weights JSONB; -- {rf: 0.4, ae: 0.35, rul: 0.25}

-- =====================================================
-- 6. Drift Detection Table
-- =====================================================
CREATE TABLE IF NOT EXISTS public.drift_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    date DATE NOT NULL,
    feature_name TEXT NOT NULL,
    psi_score FLOAT, -- Population Stability Index
    ks_statistic FLOAT, -- Kolmogorov-Smirnov
    ks_pvalue FLOAT,
    mean_shift FLOAT, -- Difference from baseline mean
    std_shift FLOAT,
    alert_triggered BOOLEAN DEFAULT false,
    baseline_period TEXT, -- e.g., '2024-01-01 to 2024-01-31'
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(date, feature_name)
);

CREATE INDEX idx_drift_date ON public.drift_metrics(date DESC);
CREATE INDEX idx_drift_alerts ON public.drift_metrics(alert_triggered) WHERE alert_triggered = true;

ALTER TABLE public.drift_metrics ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Authenticated users can read drift metrics"
    ON public.drift_metrics FOR SELECT
    TO authenticated
    USING (true);

CREATE POLICY "Service role can manage drift metrics"
    ON public.drift_metrics FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- =====================================================
-- 7. Comments
-- =====================================================
COMMENT ON TABLE public.model_registry IS 'Central registry for all ML models with versioning and promotion workflow';
COMMENT ON TABLE public.prediction_stats IS 'Daily aggregated statistics for monitoring model performance';
COMMENT ON TABLE public.model_comparison IS 'A/B test results comparing different model versions';
COMMENT ON TABLE public.prediction_feedback IS 'Human-in-the-loop feedback for model predictions';
COMMENT ON TABLE public.drift_metrics IS 'Feature drift detection metrics for monitoring data distribution shifts';
