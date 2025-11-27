-- Avisense Database Schema Migration
-- Version: 0001_initial
-- Description: Create all tables, indexes, RLS policies, and triggers

-- Extensions
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- PROFILES TABLE (extends auth.users)
-- ============================================================================
CREATE TABLE public.profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  email TEXT UNIQUE NOT NULL,
  full_name TEXT,
  role TEXT NOT NULL DEFAULT 'engineer' CHECK (role IN ('admin','engineer','readonly','pilot')),
  organization_id UUID,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE public.profiles IS 'User profiles extending Supabase auth.users';
COMMENT ON COLUMN public.profiles.role IS 'User role: admin, engineer, readonly, or pilot';

-- ============================================================================
-- ENGINES TABLE
-- ============================================================================
CREATE TABLE public.engines (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  engine_id TEXT NOT NULL,
  model TEXT,
  serial_number TEXT,
  aircraft_registration TEXT,
  owner_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
  organization_id UUID,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','maintenance','retired')),
  metadata JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(engine_id, owner_id)
);

COMMENT ON TABLE public.engines IS 'Flight engine registry';
COMMENT ON COLUMN public.engines.engine_id IS 'User-facing engine identifier (e.g., ENG-123)';
COMMENT ON COLUMN public.engines.status IS 'Engine operational status';

-- ============================================================================
-- TELEMETRY TABLE (Time-series sensor data)
-- ============================================================================
CREATE TABLE public.telemetry (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  engine_id UUID NOT NULL REFERENCES public.engines(id) ON DELETE CASCADE,
  timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  time_cycles INTEGER,
  
  -- Operational settings
  setting_1 DOUBLE PRECISION,
  setting_2 DOUBLE PRECISION,
  setting_3 DOUBLE PRECISION,
  
  -- Sensor readings (11 active sensors)
  sensor_2 DOUBLE PRECISION,
  sensor_3 DOUBLE PRECISION,
  sensor_4 DOUBLE PRECISION,
  sensor_7 DOUBLE PRECISION,
  sensor_9 DOUBLE PRECISION,
  sensor_11 DOUBLE PRECISION,
  sensor_12 DOUBLE PRECISION,
  sensor_14 DOUBLE PRECISION,
  sensor_17 DOUBLE PRECISION,
  sensor_20 DOUBLE PRECISION,
  sensor_21 DOUBLE PRECISION,
  
  -- Metadata
  source TEXT,
  metadata JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE public.telemetry IS 'Time-series engine sensor data';
COMMENT ON COLUMN public.telemetry.source IS 'Data source: manual, batch_upload, or realtime_stream';

-- ============================================================================
-- PREDICTIONS TABLE
-- ============================================================================
CREATE TABLE public.predictions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  engine_id UUID NOT NULL REFERENCES public.engines(id) ON DELETE CASCADE,
  telemetry_id UUID REFERENCES public.telemetry(id) ON DELETE SET NULL,
  
  -- Prediction results
  prediction TEXT NOT NULL CHECK (prediction IN ('SAFE','PRONE TO FAILURE')),
  probability DOUBLE PRECISION NOT NULL,
  confidence DOUBLE PRECISION NOT NULL,
  safe_probability DOUBLE PRECISION NOT NULL,
  failure_probability DOUBLE PRECISION NOT NULL,
  
  -- Actions and anomalies
  actions TEXT,
  anomalies JSONB,
  
  -- Model metadata
  model_version TEXT NOT NULL,
  model_type TEXT NOT NULL,
  
  -- Input snapshot (for audit trail)
  input_data JSONB NOT NULL,
  
  -- Metadata
  created_by UUID REFERENCES public.profiles(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE public.predictions IS 'ML prediction results and audit trail';
COMMENT ON COLUMN public.predictions.anomalies IS 'Detected sensor anomalies (JSON array)';
COMMENT ON COLUMN public.predictions.input_data IS 'Snapshot of input data for audit';

-- ============================================================================
-- MODELS TABLE (Model versioning)
-- ============================================================================
CREATE TABLE public.models (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  version TEXT UNIQUE NOT NULL,
  model_type TEXT NOT NULL,
  dataset TEXT,
  
  -- Performance metrics
  safe_recall DOUBLE PRECISION,
  failure_recall DOUBLE PRECISION,
  accuracy DOUBLE PRECISION,
  
  -- Model artifact
  artifact_url TEXT,
  feature_names JSONB NOT NULL,
  
  -- Status
  status TEXT NOT NULL DEFAULT 'training' CHECK (status IN ('training','testing','active','deprecated')),
  is_active BOOLEAN NOT NULL DEFAULT FALSE,
  
  -- Metadata
  trained_by UUID REFERENCES public.profiles(id),
  trained_at TIMESTAMPTZ,
  metadata JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE public.models IS 'ML model versioning and metadata';
COMMENT ON COLUMN public.models.is_active IS 'Only one model can be active at a time';

-- Ensure only one active model
CREATE UNIQUE INDEX idx_models_active ON public.models(is_active) WHERE is_active = TRUE;

-- ============================================================================
-- INDEXES
-- ============================================================================

-- Profiles
CREATE INDEX idx_profiles_email ON public.profiles(email);
CREATE INDEX idx_profiles_org ON public.profiles(organization_id);

-- Engines
CREATE INDEX idx_engines_owner ON public.engines(owner_id);
CREATE INDEX idx_engines_org ON public.engines(organization_id);
CREATE INDEX idx_engines_status ON public.engines(status);
CREATE INDEX idx_engines_engine_id ON public.engines(engine_id);

-- Telemetry (optimized for time-series queries)
CREATE INDEX idx_telemetry_engine_time ON public.telemetry(engine_id, timestamp DESC);
CREATE INDEX idx_telemetry_timestamp ON public.telemetry(timestamp DESC);
CREATE INDEX idx_telemetry_engine ON public.telemetry(engine_id);

-- Predictions
CREATE INDEX idx_predictions_engine ON public.predictions(engine_id, created_at DESC);
CREATE INDEX idx_predictions_timestamp ON public.predictions(created_at DESC);
CREATE INDEX idx_predictions_result ON public.predictions(prediction);
CREATE INDEX idx_predictions_created_by ON public.predictions(created_by);

-- Models
CREATE INDEX idx_models_version ON public.models(version);
CREATE INDEX idx_models_status ON public.models(status);

-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to profiles
CREATE TRIGGER trg_profiles_updated_at
  BEFORE UPDATE ON public.profiles
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- Apply to engines
CREATE TRIGGER trg_engines_updated_at
  BEFORE UPDATE ON public.engines
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ============================================================================

-- Enable RLS on all tables
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.engines ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.telemetry ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.predictions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.models ENABLE ROW LEVEL SECURITY;

-- Profiles: Users can view and update their own profile
CREATE POLICY "profiles_select_self"
  ON public.profiles FOR SELECT
  USING (auth.uid() = id);

CREATE POLICY "profiles_update_self"
  ON public.profiles FOR UPDATE
  USING (auth.uid() = id);

CREATE POLICY "profiles_insert_self"
  ON public.profiles FOR INSERT
  WITH CHECK (auth.uid() = id);

-- Engines: Users can only access their own engines
CREATE POLICY "engines_select_owner"
  ON public.engines FOR SELECT
  USING (owner_id = auth.uid());

CREATE POLICY "engines_insert_owner"
  ON public.engines FOR INSERT
  WITH CHECK (owner_id = auth.uid());

CREATE POLICY "engines_update_owner"
  ON public.engines FOR UPDATE
  USING (owner_id = auth.uid());

CREATE POLICY "engines_delete_owner"
  ON public.engines FOR DELETE
  USING (owner_id = auth.uid());

-- Telemetry: Users can only access telemetry for their engines
CREATE POLICY "telemetry_select_owner"
  ON public.telemetry FOR SELECT
  USING (
    engine_id IN (
      SELECT id FROM public.engines WHERE owner_id = auth.uid()
    )
  );

CREATE POLICY "telemetry_insert_owner"
  ON public.telemetry FOR INSERT
  WITH CHECK (
    engine_id IN (
      SELECT id FROM public.engines WHERE owner_id = auth.uid()
    )
  );

-- Predictions: Users can only access predictions for their engines
CREATE POLICY "predictions_select_owner"
  ON public.predictions FOR SELECT
  USING (
    engine_id IN (
      SELECT id FROM public.engines WHERE owner_id = auth.uid()
    )
  );

CREATE POLICY "predictions_insert_owner"
  ON public.predictions FOR INSERT
  WITH CHECK (
    engine_id IN (
      SELECT id FROM public.engines WHERE owner_id = auth.uid()
    )
  );

-- Models: All authenticated users can view models, only admins can manage
CREATE POLICY "models_select_authenticated"
  ON public.models FOR SELECT
  USING (auth.role() = 'authenticated');

CREATE POLICY "models_manage_admin"
  ON public.models FOR ALL
  USING (
    EXISTS (
      SELECT 1 FROM public.profiles
      WHERE id = auth.uid() AND role = 'admin'
    )
  );

-- ============================================================================
-- INITIAL DATA
-- ============================================================================

-- Insert initial active model metadata (update with actual values)
INSERT INTO public.models (
  version,
  model_type,
  dataset,
  safe_recall,
  failure_recall,
  accuracy,
  feature_names,
  status,
  is_active,
  trained_at
) VALUES (
  'v1.0.0',
  'RandomForestClassifier',
  'NASA_C-MAPSS_FD001',
  0.976,
  0.869,
  0.95,
  '["setting_1","setting_2","setting_3","sensor_2","sensor_3","sensor_4","sensor_7","sensor_9","sensor_11","sensor_12","sensor_14","sensor_17","sensor_20","sensor_21"]'::jsonb,
  'active',
  true,
  NOW()
);

-- ============================================================================
-- NOTES
-- ============================================================================

-- 1. After running this migration, test RLS policies:
--    - Create two test users
--    - Verify User A cannot access User B's data
--    - Verify admins can manage models

-- 2. For production scale, consider:
--    - Partitioning telemetry table by timestamp
--    - Enabling TimescaleDB extension for time-series optimization
--    - Setting up automatic archival of old data

-- 3. Enable Realtime for predictions table:
--    ALTER PUBLICATION supabase_realtime ADD TABLE predictions;

-- 4. Storage buckets (create in Supabase Dashboard):
--    - model-artifacts (for .joblib files)
--    - telemetry-uploads (for CSV/JSON batches)
