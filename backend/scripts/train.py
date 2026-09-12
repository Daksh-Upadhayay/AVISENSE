"""Train, calibrate and evaluate the Avisense models on NASA C-MAPSS FD001-FD004.

Usage (from backend/):  python -m scripts.train

Protocol
- One model for all four subsets. Training engines are split 80/20 by engine
  (never by row) so validation engines are unseen during fitting.
- The validation engines drive early stopping, the conformal interval calibration and
  the alert threshold. The official test sets are used only for the final report.
- Test RUL is scored at the last recorded cycle of each test engine with the
  truth capped at 125 cycles, the convention used in most C-MAPSS papers.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

from app.ml.cmapss import DATASET_INFO, DATASETS, MODEL_SENSORS, load_test, load_train
from app.ml.features import LONG_WINDOW, SHORT_WINDOW, SLOPE_WINDOW, Normalizer, build_features, feature_names
from app.ml.model import RulModel

VERSION = "3.0.0"
SEED = 7
RUL_CAP = 125
HORIZON = 30
TARGET_RECALL = 0.95  # on validation rows; test recall runs lower, see model card
INTERVAL_LEVEL = 0.80
WATCH_RUL = 60
VAL_FRACTION = 0.2
INTERVAL_EDGES = (0, 20, 40, 60, 80, 100, 115, RUL_CAP + 1)
# Intervals are calibrated on validation rows this close to failure. Further out,
# the capped target says nothing useful and would make every interval look tight.
CALIBRATION_HORIZON = 150

OUT_DIR = Path(__file__).resolve().parents[1] / "models" / "current"

BASE_PARAMS = {
    "learning_rate": 0.05,
    "num_leaves": 31,
    "min_data_in_leaf": 100,
    "feature_fraction": 0.8,
    "bagging_fraction": 0.8,
    "bagging_freq": 1,
    "lambda_l2": 1.0,
    "verbose": -1,
    "seed": SEED,
    "deterministic": True,
    "force_row_wise": True,
    "num_threads": 4,
}

# Reference numbers for the previous release (v2 LSTM), measured on the FD001
# test set before this rewrite. Kept so the model card shows what changed.
PREVIOUS_RELEASE = {
    "name": "v2.0.0 LSTM (FD001 only)",
    "fd001_rmse_as_served": 27.81,
    "fd001_rmse_with_history": 13.04,
    "note": "The v2 API repeated one reading 30 times instead of using the engine's history.",
}


def stack(loader) -> pd.DataFrame:
    frames = []
    for i, name in enumerate(DATASETS):
        df = loader(name)
        df["dataset"] = name
        df["source_unit"] = df["unit"]
        df["unit"] = df["unit"] + 1000 * (i + 1)
        frames.append(df)
    return pd.concat(frames, ignore_index=True).sort_values(["unit", "cycle"]).reset_index(drop=True)


def split_engines(train: pd.DataFrame) -> np.ndarray:
    """Boolean mask of validation rows: 20% of engines from every subset."""
    rng = np.random.default_rng(SEED)
    val_units = []
    for _, group in train.groupby("dataset"):
        units = group["unit"].unique()
        val_units += list(rng.choice(units, int(round(VAL_FRACTION * len(units))), replace=False))
    return train["unit"].isin(val_units).to_numpy()


def fit(params: dict, X_tr, y_tr, X_va, y_va) -> lgb.Booster:
    return lgb.train(
        {**BASE_PARAMS, **params},
        lgb.Dataset(X_tr, y_tr),
        num_boost_round=4000,
        valid_sets=[lgb.Dataset(X_va, y_va)],
        callbacks=[lgb.early_stopping(150, verbose=False)],
    )


def nasa_score(y: np.ndarray, pred: np.ndarray) -> float:
    """PHM08 asymmetric score: late predictions cost more than early ones."""
    d = pred - y
    return float(np.sum(np.where(d < 0, np.exp(-d / 13) - 1, np.exp(d / 10) - 1)))


def interval_bins(point: np.ndarray, y: np.ndarray, level: float) -> list[dict]:
    """Split-conformal residual quantiles per predicted-RUL band (Mondrian conformal).

    Signed residuals keep the interval asymmetric where errors are.
    """
    tail = (1 - level) / 2
    bins = []
    for a, b in zip(INTERVAL_EDGES[:-1], INTERVAL_EDGES[1:]):
        r = (y - point)[(point >= a) & (point < b)]
        n = len(r)
        lo_q = max(0.0, np.floor((n + 1) * tail) / n)
        hi_q = min(1.0, np.ceil((n + 1) * (1 - tail)) / n)
        bins.append({"from": a, "to": b, "low": round(float(np.quantile(r, lo_q)), 2), "high": round(float(np.quantile(r, hi_q)), 2), "rows": n})
    return bins


def threshold_for_recall(y: np.ndarray, prob: np.ndarray, recall: float) -> float:
    """Highest threshold that still catches `recall` of true positives."""
    positives = np.sort(prob[y == 1])[::-1]
    k = int(np.ceil(recall * len(positives))) - 1
    return float(positives[k])


def main() -> None:
    train = stack(load_train)
    test = stack(load_test)
    print(f"train rows {len(train)} engines {train['unit'].nunique()} | test rows {len(test)} engines {test['unit'].nunique()}")

    normalizer = Normalizer.fit(train)
    names = feature_names()
    X = build_features(train, normalizer)
    X_test = build_features(test, normalizer)
    y_rul = np.minimum(train["rul"].to_numpy(), RUL_CAP).astype(float)
    y_fail = (train["rul"].to_numpy() <= HORIZON).astype(int)
    va = split_engines(train)
    tr = ~va
    print(f"features {len(names)} | fit engines {train.loc[tr, 'unit'].nunique()} val engines {train.loc[va, 'unit'].nunique()}")

    point = fit({"objective": "regression"}, X[tr], y_rul[tr], X[va], y_rul[va])
    classifier = fit({"objective": "binary"}, X[tr], y_fail[tr], X[va], y_fail[va])
    print(f"trees: point {point.best_iteration} classifier {classifier.best_iteration}")

    point_va = np.clip(point.predict(X[va], num_iteration=point.best_iteration), 0, RUL_CAP)
    near = train.loc[va, "rul"].to_numpy() <= CALIBRATION_HORIZON
    bins = interval_bins(point_va[near], y_rul[va][near], INTERVAL_LEVEL)
    prob_va = classifier.predict(X[va], num_iteration=classifier.best_iteration)
    threshold = threshold_for_recall(y_fail[va], prob_va, TARGET_RECALL)
    print(f"alert threshold {threshold:.3f} | interval bins", [(b["from"], b["low"], b["high"]) for b in bins])

    # Save, then reload through the serving class so the report measures exactly what the API runs.
    tmp = OUT_DIR.with_name("current.tmp")
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    for booster, name in [(point, "rul_point"), (classifier, "failure_classifier")]:
        booster.save_model(str(tmp / f"{name}.txt"), num_iteration=booster.best_iteration)

    meta = {
        "version": VERSION,
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "algorithm": {
            "rul": "LightGBM gradient-boosted trees (L2 loss), RUL target capped at 125 cycles",
            "interval": (
                f"{INTERVAL_LEVEL:.0%} split-conformal interval, calibrated per band of predicted RUL on validation "
                f"engines within {CALIBRATION_HORIZON} cycles of failure"
            ),
            "failure": f"LightGBM binary classifier for failure within {HORIZON} cycles",
            "explanations": "Exact TreeSHAP contributions of the RUL model, summed per sensor",
        },
        "training_data": {
            "source": "NASA C-MAPSS turbofan degradation simulation (Saxena et al., 2008)",
            "subsets": {d: DATASET_INFO[d] for d in DATASETS},
            "fit_engines": int(train.loc[tr, "unit"].nunique()),
            "validation_engines": int(train.loc[va, "unit"].nunique()),
            "rows": int(len(train)),
        },
        "feature_description": (
            "Each sensor is converted to a z-score against the healthy early-life baseline of its operating "
            f"regime (6 regimes from altitude, Mach and throttle). Per sensor: {SHORT_WINDOW}- and "
            f"{LONG_WINDOW}-cycle rolling means, {SLOPE_WINDOW}-cycle trend slope, and drift from the engine's "
            "own first recorded cycles. Plus cycles in service."
        ),
        "features": names,
        "normalizer": normalizer.to_dict(),
        "policy": {
            "horizon": HORIZON,
            "rul_cap": RUL_CAP,
            "alert_threshold": round(threshold, 4),
            "watch_rul": WATCH_RUL,
            "interval_level": INTERVAL_LEVEL,
            "interval_bins": bins,
        },
        "metrics": {},
        "limitations": [
            "Trained on simulated data (C-MAPSS). Real engines need retraining on their own run-to-failure records.",
            f"The RUL target is capped at {RUL_CAP} cycles, so early-life engines all read as '{RUL_CAP}+'.",
            "Drift is measured from the first recorded cycles. Histories that start mid-life hide earlier wear.",
            "Only degradation modes present in the training data (HPC and fan) are represented.",
        ],
    }
    (tmp / "metadata.json").write_text(json.dumps(meta, indent=1))
    model = RulModel(tmp)

    metrics = evaluate(model, test, X_test)
    metrics["validation"] = {"alert_threshold_recall_target": TARGET_RECALL}
    metrics["previous_release"] = PREVIOUS_RELEASE
    metrics["global_importance"] = global_importance(model, X_test)
    meta["metrics"] = metrics
    (tmp / "metadata.json").write_text(json.dumps(meta, indent=1))

    shutil.rmtree(OUT_DIR, ignore_errors=True)
    tmp.rename(OUT_DIR)
    print_report(metrics)
    print(f"saved to {OUT_DIR}")


def evaluate(model: RulModel, test: pd.DataFrame, X_test: pd.DataFrame) -> dict:
    cap, horizon = model.policy.rul_cap, model.policy.horizon
    preds = model.predict_frame(X_test)
    last = test.groupby("unit").tail(1).index
    y_last = np.minimum(test.loc[last, "rul"].to_numpy(), cap)
    p_last = preds.loc[last]

    per_dataset = {}
    for name in DATASETS:
        m = (test.loc[last, "dataset"] == name).to_numpy()
        rows = (test["dataset"] == name).to_numpy()
        per_dataset[name] = {
            **rul_metrics(y_last[m], p_last[m]),
            **failure_metrics(test.loc[rows, "rul"].to_numpy() <= horizon, preds.loc[rows, "failure_probability"].to_numpy(), model.policy.alert_threshold),
            "engines": int(m.sum()),
        }

    y_all_fail = test["rul"].to_numpy() <= horizon
    overall = {
        **rul_metrics(y_last, p_last),
        **failure_metrics(y_all_fail, preds["failure_probability"].to_numpy(), model.policy.alert_threshold),
        "engines": int(len(last)),
    }

    # Near failure is where accuracy matters: RUL error by true-RUL band, all test rows.
    y_all = test["rul"].to_numpy()
    bands = []
    for lo, hi in [(0, 25), (25, 50), (50, 75), (75, 100), (100, 125)]:
        m = (y_all >= lo) & (y_all < hi)
        err = preds["rul"].to_numpy()[m] - y_all[m]
        bands.append({"band": f"{lo}–{hi}", "rows": int(m.sum()), "mae": round(float(np.mean(np.abs(err))), 2), "bias": round(float(np.mean(err)), 2)})

    prob = preds["failure_probability"].to_numpy()
    edges = np.linspace(0, 1, 11)
    reliability = []
    for a, b in zip(edges[:-1], edges[1:]):
        m = (prob >= a) & (prob < b if b < 1 else prob <= b)
        if m.sum() >= 20:
            reliability.append({"predicted": round(float(prob[m].mean()), 3), "observed": round(float(y_all_fail[m].mean()), 3), "rows": int(m.sum())})

    scatter = [
        {"dataset": d, "true": int(t), "predicted": round(float(p), 1), "low": round(float(lo), 1), "high": round(float(hi), 1)}
        for d, t, p, lo, hi in zip(test.loc[last, "dataset"], y_last, p_last["rul"], p_last["rul_low"], p_last["rul_high"])
    ]
    return {"overall": overall, "per_dataset": per_dataset, "error_by_rul": bands, "reliability": reliability, "test_scatter": scatter}


def rul_metrics(y: np.ndarray, p: pd.DataFrame) -> dict:
    err = p["rul"].to_numpy() - y
    covered = (y >= p["rul_low"].to_numpy()) & (y <= p["rul_high"].to_numpy())
    return {
        "rmse": round(float(np.sqrt(np.mean(err**2))), 2),
        "mae": round(float(np.mean(np.abs(err))), 2),
        "nasa_score": round(nasa_score(y, p["rul"].to_numpy()), 1),
        "interval_coverage": round(float(covered.mean()), 3),
        "interval_width": round(float((p["rul_high"] - p["rul_low"]).mean()), 1),
    }


def failure_metrics(y: np.ndarray, prob: np.ndarray, threshold: float) -> dict:
    alert = prob >= threshold
    tp = int((alert & y).sum())
    return {
        "pr_auc": round(float(average_precision_score(y, prob)), 3),
        "roc_auc": round(float(roc_auc_score(y, prob)), 3),
        "brier": round(float(brier_score_loss(y, prob)), 4),
        "recall": round(tp / max(1, int(y.sum())), 3),
        "precision": round(tp / max(1, int(alert.sum())), 3),
    }


def global_importance(model: RulModel, X_test: pd.DataFrame) -> list[dict]:
    """Mean absolute SHAP contribution per sensor over a sample of test rows."""
    sample = X_test.sample(min(5000, len(X_test)), random_state=SEED)
    contrib = model.point.predict(sample, pred_contrib=True)[:, :-1]
    totals: dict[str, float] = {}
    for name, col in zip(model.features, np.abs(contrib).mean(axis=0)):
        key = name.split("__")[0]
        totals[key] = totals.get(key, 0.0) + float(col)
    return [{"feature": k, "mean_abs_cycles": round(v, 2)} for k, v in sorted(totals.items(), key=lambda kv: -kv[1])]


def print_report(metrics: dict) -> None:
    print("\nOfficial test sets (RUL at last cycle, truth capped at 125; failure metrics over all test rows)")
    print(f"{'subset':8} {'RMSE':>6} {'MAE':>6} {'NASA':>8} {'cover':>6} {'width':>6} {'PR-AUC':>7} {'recall':>7} {'prec':>6}")
    for name, m in [*metrics["per_dataset"].items(), ("overall", metrics["overall"])]:
        print(
            f"{name:8} {m['rmse']:6.2f} {m['mae']:6.2f} {m['nasa_score']:8.1f} {m['interval_coverage']:6.2f} "
            f"{m['interval_width']:6.1f} {m['pr_auc']:7.3f} {m['recall']:7.3f} {m['precision']:6.3f}"
        )
    print("error by true RUL:", ", ".join(f"{b['band']}: MAE {b['mae']}" for b in metrics["error_by_rul"]))


if __name__ == "__main__":
    main()
