# Avisense Database Schema Reference

**Last Updated:** 2025-12-08  
**Version:** v2.0.0

## Current Active Tables (9 Total)

### Core Tables

#### 1. **profiles**
- **Purpose**: User profiles extending Supabase auth
- **Key Columns**: `id`, `email`, `full_name`, `role`, `organization_id`
- **Relationships**: Referenced by engines, predictions
- **Status**: ✅ Active

#### 2. **engines**
- **Purpose**: Flight engine registry
- **Key Columns**: `id`, `engine_id`, `model`, `serial_number`, `owner_id`, `status`
- **Relationships**: Referenced by telemetry, predictions
- **Status**: ✅ Active

#### 3. **telemetry**
- **Purpose**: Time-series sensor data (11 active sensors)
- **Key Columns**: `id`, `engine_id`, `timestamp`, `setting_1-3`, `sensor_2,3,4,7,9,11,12,14,17,20,21`, `source`, `metadata`
- **Relationships**: References engines, referenced by predictions
- **Status**: ✅ Active

#### 4. **predictions**
- **Purpose**: ML prediction results and audit trail
- **Key Columns**: 
  - Core: `id`, `engine_id`, `telemetry_id`, `prediction`, `probability`
  - Metrics: `risk_percent`, `rul_prediction`, `anomaly_score`
  - Metadata: `model_version`, `model_type`, `input_data`, `shap_values`
  - Provenance: `model_provenance`, `inference_latency_ms`, `ensemble_weights`
- **Relationships**: References engines, telemetry, profiles
- **Status**: ✅ Active

### ML Operations Tables

#### 5. **model_registry**
- **Purpose**: Central registry for all ML models (v2.0.0)
- **Key Columns**: `id`, `model_family`, `version`, `artifact_url`, `metrics`, `status`
- **Replaces**: Old `models` table (deprecated)
- **Status**: ✅ Active

#### 6. **prediction_stats**
- **Purpose**: Daily aggregated monitoring statistics
- **Key Columns**: `id`, `date`, `model_family`, `total_predictions`, `avg_anomaly_score`, `avg_risk_percent`
- **Usage**: Monitoring dashboard
- **Status**: ✅ Active

#### 7. **drift_metrics**
- **Purpose**: Feature drift detection for data monitoring
- **Key Columns**: `id`, `date`, `feature_name`, `psi_score`, `ks_statistic`, `mean_shift`, `alert_triggered`
- **Usage**: Data quality monitoring
- **Status**: ✅ Active

#### 8. **model_comparison**
- **Purpose**: A/B testing results
- **Key Columns**: `id`, `model_a`, `model_b`, `metric_name`, `statistical_significance`, `winner`
- **Usage**: Model evaluation
- **Status**: ✅ Active

#### 9. **prediction_feedback**
- **Purpose**: Human-in-the-loop feedback
- **Key Columns**: `id`, `prediction_id`, `feedback_type`, `actual_outcome`, `operator_notes`
- **Usage**: Active learning, model improvement
- **Status**: ✅ Active

## Deprecated Tables

### ❌ models (OLD)
- **Status**: DEPRECATED - Replace with `model_registry`
- **Action**: Run cleanup script to drop
- **Migration**: Data should be migrated to `model_registry` if needed

## Schema Relationships

```
profiles (users)
  └─► engines (1:many)
       ├─► telemetry (1:many)
       └─► predictions (1:many)
            └─► prediction_feedback (1:many)

model_registry (central)
  └─► prediction_stats (tracking)

drift_metrics (independent monitoring)
model_comparison (independent analysis)
```

## Usage by API Endpoints

| Table | Endpoints Using It |
|-------|-------------------|
| `predictions` | `/predict`, `/api/rul`, `/api/feedback` |
| `telemetry` | `/api/rul` |
| `engines` | All endpoints (ownership verification) |
| `model_registry` | `/api/models/*`, `/api/monitoring` |
| `prediction_stats` | `/api/monitoring/*` |
| `drift_metrics` | `/api/monitoring/drift` |
| `model_comparison` | `/api/monitoring/compare` |
| `prediction_feedback` | `/api/feedback/*` |
| `profiles` | All endpoints (RLS) |

## Indexes Summary

**Performance Optimizations:**
- Time-series queries: `idx_telemetry_engine_time`
- Recent predictions: `idx_predictions_engine`
- Monitoring lookups: `idx_prediction_stats_date`
- Drift alerts: `idx_drift_alerts`

## How to Apply Cleanup

1. **Backup your database first:**
   ```bash
   pg_dump your_database > backup_$(date +%Y%m%d).sql
   ```

2. **Run diagnostic query:**
   ```sql
   -- See Part 1 of database_cleanup.sql
   ```

3. **Apply cleanup:**
   ```bash
   psql your_database < supabase/migrations/database_cleanup.sql
   ```

4. **Verify:**
   ```sql
   -- See Part 5 of database_cleanup.sql
   ```

## Next Steps

- [ ] Backup current database
- [ ] Review existing tables with diagnostic query
- [ ] Run cleanup script (drops `models` table)
- [ ] Verify 9 active tables remain
- [ ] Update application config if needed
