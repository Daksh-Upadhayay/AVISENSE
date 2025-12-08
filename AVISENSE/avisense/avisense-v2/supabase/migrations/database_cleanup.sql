-- ============================================================================
-- Avisense Database Cleanup & Refinement Script
-- ============================================================================
-- This script:
-- 1. Lists all existing tables
-- 2. Drops unused/deprecated tables
-- 3. Ensures only active tables remain
-- 4. Optimizes schema for current codebase
-- ============================================================================

-- ============================================================================
-- PART 1: DIAGNOSTIC - Check what tables currently exist
-- ============================================================================
-- Run this first to see what you have:
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;

-- ============================================================================
-- PART 2: ACTIVE TABLES (Keep These)
-- ============================================================================
-- Based on code analysis, these tables are actively used:
-- 
-- 1. profiles              (User management)
-- 2. engines               (Engine registry)
-- 3. telemetry             (Time-series sensor data)
-- 4. predictions           (Prediction results)
-- 5. model_registry        (Model versioning - replaces old 'models' table)
-- 6. prediction_stats      (Monitoring)
-- 7. drift_metrics         (Drift detection)
-- 8. model_comparison      (A/B testing)
-- 9. prediction_feedback   (Human-in-the-loop)
--
-- Total: 9 active tables

-- ============================================================================
-- PART 3: DROP DEPRECATED TABLES
-- ============================================================================

-- Drop old 'models' table (replaced by 'model_registry')
-- WARNING: This will delete data! Backup first if needed
DROP TABLE IF EXISTS public.models CASCADE;

-- Drop any other unused tables that might exist
-- (Add any additional tables you want to remove here)

-- ============================================================================
-- PART 4: ENSURE SCHEMA IS UP TO DATE
-- ============================================================================

-- Add missing columns to predictions table (if not already present)
ALTER TABLE public.predictions 
ADD COLUMN IF NOT EXISTS risk_percent DOUBLE PRECISION,
ADD COLUMN IF NOT EXISTS anomaly_score DOUBLE PRECISION,
ADD COLUMN IF NOT EXISTS reconstruction_errors JSONB,
ADD COLUMN IF NOT EXISTS shap_values JSONB,
ADD COLUMN IF NOT EXISTS correlated_anomalies JSONB,
ADD COLUMN IF NOT EXISTS rul_prediction DOUBLE PRECISION,
ADD COLUMN IF NOT EXISTS source TEXT,
ADD COLUMN IF NOT EXISTS model_provenance JSONB,
ADD COLUMN IF NOT EXISTS inference_latency_ms FLOAT,
ADD COLUMN IF NOT EXISTS ensemble_weights JSONB;

-- Add indexes for new columns
CREATE INDEX IF NOT EXISTS idx_predictions_risk ON public.predictions(risk_percent);
CREATE INDEX IF NOT EXISTS idx_predictions_rul ON public.predictions(rul_prediction);
CREATE INDEX IF NOT EXISTS idx_predictions_source ON public.predictions(source);

-- ============================================================================
-- PART 5: VERIFY TABLE COUNTS
-- ============================================================================
-- Run this to verify the cleanup:
SELECT 
    schemaname,
    tablename
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;

-- Expected result: 9 tables
-- ✓ drift_metrics
-- ✓ engines
-- ✓ model_comparison
-- ✓ model_registry
-- ✓ prediction_feedback
-- ✓ prediction_stats
-- ✓ predictions
-- ✓ profiles
-- ✓ telemetry

-- ============================================================================
-- PART 6: CLEANUP SCRIPT SUMMARY
-- ============================================================================
-- Tables Dropped:
-- - models (replaced by model_registry)
--
-- Tables Kept (9):
-- - profiles, engines, telemetry, predictions
-- - model_registry, prediction_stats, drift_metrics
-- - model_comparison, prediction_feedback
--
-- Schema Updates:
-- - Added missing columns to predictions table
-- - Added performance indexes
-- ============================================================================
