# Data Quality & Leakage Audit Report

**Date:** 2025-12-07
**Dataset:** CMAPSS FD001

## Executive Summary
A comprehensive audit of the CMAPSS FD001 dataset and the existing preprocessing pipeline revealed a **critical data leakage issue** in the validation split strategy. The current implementation splits sequences by index, causing at least one engine (Engine 82) to be split across training and validation sets. This inflates validation metrics and compromises model evaluation.

## Findings

### 1. Data Leakage (Critical)
- **Issue:** The train/validation split is performed on the flattened sequence array (`X[:split_idx]`, `X[split_idx:]`) rather than by Engine ID.
- **Impact:** Engine 82 has its early life cycles in the Training set and its late life cycles in the Validation set. The model learns the specific behavior of this engine during training and is tested on it, leading to overly optimistic performance estimates.
- **Fix Required:** Implement **GroupKFold** or manual engine-wise splitting to ensure all sequences from a single engine belong exclusively to one fold.

### 2. Constant Features
- **Issue:** Several sensors and settings have zero variance (constant values) across the entire dataset.
- **Features:** `setting_3`, `sensor_1`, `sensor_5`, `sensor_10`, `sensor_16`, `sensor_18`, `sensor_19`.
- **Action:** These features provide no information and should be dropped to reduce noise and model complexity. The current pipeline drops most but misses `setting_3`.

### 3. Missing Values & Duplicates
- **Status:** ✅ Clean. No missing values or duplicate rows were found.

### 4. RUL Calculation
- **Status:** ✅ Correct. RUL is calculated as `max_cycle - current_cycle` per engine, which is appropriate for run-to-failure data.

## Recommendations for Retraining Pipeline
1.  **Strict Engine-wise Splitting:** Use `GroupKFold` or filter by `engine_id` for all cross-validation and train/test splits.
2.  **Feature Selection:** Explicitly drop all constant columns identified above.
3.  **Reproducibility:** Fix random seeds for all split operations.

## Next Steps
Proceed with **Step B: Reproducible Retraining**, implementing the engine-wise split and dropping the identified constant features.
