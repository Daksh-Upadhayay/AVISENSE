-- SQL Cleanup Helper
-- Run these commands in your Supabase SQL Editor to clean up redundant data or schema elements.
-- UNCOMMENT the lines you want to execute.

-- ==========================================
-- 1. Remove RUL Prediction Column
-- ==========================================
-- If you decided not to use the RUL prediction feature (since it was disabled in the UI),
-- you can remove the column from the database.
-- ALTER TABLE predictions DROP COLUMN IF EXISTS rul_prediction;

-- ==========================================
-- 2. Clean up Test/Manual Data
-- ==========================================
-- Delete predictions and telemetry generated during testing or manual entry.
-- DELETE FROM predictions WHERE source IN ('test', 'manual', 'ui');
-- DELETE FROM telemetry WHERE source IN ('test', 'manual', 'ui');

-- ==========================================
-- 3. Reset Model Registry
-- ==========================================
-- If you want to clear all registered models and start fresh.
-- TRUNCATE TABLE model_registry;

-- ==========================================
-- 4. Remove Deep Learning Fields
-- ==========================================
-- If you want to revert the schema to before deep learning features were added.
-- ALTER TABLE predictions DROP COLUMN IF EXISTS anomaly_score;
-- ALTER TABLE predictions DROP COLUMN IF EXISTS reconstruction_errors;
-- ALTER TABLE predictions DROP COLUMN IF EXISTS correlated_anomalies;
-- ALTER TABLE predictions DROP COLUMN IF EXISTS shap_values;
