"""Trained model bundle: RUL estimate, calibrated interval, failure probability, explanations.

The same class is used by the training script for evaluation and by the API for
serving, so the two can never disagree about preprocessing.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd

from app.ml.cmapss import MODEL_SENSORS, SENSOR_INFO, SETTINGS
from app.ml.features import Normalizer, build_features, feature_sensor, sensor_drift

DEFAULT_MODEL_DIR = Path(__file__).resolve().parents[2] / "models" / "current"

STATUS_HEALTHY = "healthy"
STATUS_WATCH = "watch"
STATUS_CRITICAL = "critical"

REQUIRED_COLUMNS = ("cycle", *SETTINGS, *MODEL_SENSORS)


@dataclass
class Policy:
    """How numbers become a status. Stored with the model so the UI can show it."""

    horizon: int  # failure window for the classifier, in cycles
    rul_cap: int  # RUL target is clipped here; the model cannot see further
    alert_threshold: float  # P(failure within horizon) at or above this is critical
    watch_rul: int  # interval lower bound at or below this is watch
    interval_level: float  # nominal coverage of the RUL interval
    interval_bins: list[dict]  # conformal residual offsets per predicted-RUL band


class RulModel:
    def __init__(self, directory: Path = DEFAULT_MODEL_DIR):
        meta = json.loads((directory / "metadata.json").read_text())
        self.meta = meta
        self.version: str = meta["version"]
        self.features: list[str] = meta["features"]
        self.normalizer = Normalizer.from_dict(meta["normalizer"])
        self.policy = Policy(**meta["policy"])
        self.point = lgb.Booster(model_file=str(directory / "rul_point.txt"))
        self.classifier = lgb.Booster(model_file=str(directory / "failure_classifier.txt"))

    # ------------------------------------------------------------------ core

    def features_for(self, history: pd.DataFrame) -> pd.DataFrame:
        df = history.sort_values("cycle").reset_index(drop=True).copy()
        if "unit" not in df:
            df["unit"] = 0
        return build_features(df, self.normalizer)

    def predict_frame(self, X: pd.DataFrame) -> pd.DataFrame:
        """Point RUL, calibrated interval and failure probability for each row."""
        cap = self.policy.rul_cap
        point = np.clip(self.point.predict(X), 0, cap)
        lo, hi = self.interval(point)
        prob = self.classifier.predict(X)
        return pd.DataFrame({"rul": point, "rul_low": lo, "rul_high": hi, "failure_probability": prob}, index=X.index)

    def interval(self, point: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Calibrated interval around the point estimate.

        Error grows with distance from failure, so residual offsets are
        calibrated separately for each band of predicted RUL.
        """
        lo = np.empty_like(point)
        hi = np.empty_like(point)
        for band in self.policy.interval_bins:
            m = (point >= band["from"]) & (point < band["to"])
            lo[m] = point[m] + band["low"]
            hi[m] = point[m] + band["high"]
        cap = self.policy.rul_cap
        return np.clip(np.minimum(lo, point), 0, cap), np.clip(np.maximum(hi, point), 0, cap)

    def status(self, rul_low: float, failure_probability: float) -> str:
        if failure_probability >= self.policy.alert_threshold:
            return STATUS_CRITICAL
        if rul_low <= self.policy.watch_rul:
            return STATUS_WATCH
        return STATUS_HEALTHY

    # ------------------------------------------------------------ assessment

    def assess(self, history: pd.DataFrame) -> dict:
        """Full assessment of one engine from its recorded cycles."""
        missing = [c for c in REQUIRED_COLUMNS if c not in history.columns]
        if missing:
            raise ValueError(f"Missing columns: {', '.join(missing)}")
        if history[list(REQUIRED_COLUMNS)].isna().any().any():
            raise ValueError("History contains empty values")
        if history["cycle"].duplicated().any():
            raise ValueError("Duplicate cycle numbers in history")

        df = history.sort_values("cycle").reset_index(drop=True)
        X = self.features_for(df)
        preds = self.predict_frame(X)
        last = preds.iloc[-1]
        status = self.status(last["rul_low"], last["failure_probability"])
        contributions, base, raw = self._contributions(X.iloc[[-1]])
        sensors = self._sensor_health(df)

        return {
            "model_version": self.version,
            "cycle": int(df["cycle"].iloc[-1]),
            "cycles_observed": int(len(df)),
            "status": status,
            "rul": round(float(last["rul"]), 1),
            "rul_low": round(float(last["rul_low"]), 1),
            "rul_high": round(float(last["rul_high"]), 1),
            "failure_probability": round(float(last["failure_probability"]), 4),
            "explanation": {
                "base_rul": round(base, 1),
                "raw_rul": round(raw, 1),
                "contributions": contributions,
                "summary": self._summary(last, contributions, sensors),
            },
            "sensors": sensors,
            "trajectory": [
                {
                    "cycle": int(c),
                    "rul": round(float(r.rul), 1),
                    "rul_low": round(float(r.rul_low), 1),
                    "rul_high": round(float(r.rul_high), 1),
                    "failure_probability": round(float(r.failure_probability), 4),
                }
                for c, r in zip(df["cycle"], preds.itertuples())
            ],
            "warnings": self._warnings(df),
            "policy": {k: v for k, v in self.policy.__dict__.items() if k != "interval_bins"},
        }

    def _contributions(self, x_last: pd.DataFrame) -> tuple[list[dict], float, float]:
        """Exact TreeSHAP values of the point model, summed per sensor, in cycles.

        base + sum(contributions) == raw model output, before clipping to [0, cap].
        """
        shap = self.point.predict(x_last, pred_contrib=True)[0]
        base = float(shap[-1])
        per_sensor: dict[str, float] = {}
        for name, value in zip(self.features, shap[:-1]):
            key = feature_sensor(name)
            per_sensor[key] = per_sensor.get(key, 0.0) + float(value)

        items = []
        for key, value in per_sensor.items():
            if key == "cycle":
                label, symbol = "Cycles in service", "Age"
            else:
                label, symbol = SENSOR_INFO[key]["name"], SENSOR_INFO[key]["symbol"]
            items.append({"feature": key, "symbol": symbol, "label": label, "cycles": round(value, 2)})
        items.sort(key=lambda i: abs(i["cycles"]), reverse=True)
        return items, base, float(shap.sum())

    def _sensor_health(self, df: pd.DataFrame) -> list[dict]:
        """Per-sensor drift from the engine's own starting level, in healthy standard deviations.

        `progress` puts the drift on a scale where 0 is within normal noise and
        1 is the median drift seen on training engines 10 cycles before failure.
        """
        frame = df.assign(unit=0)
        drift = sensor_drift(frame, self.normalizer)
        out = []
        for i, s in enumerate(self.normalizer.sensors):
            noise = self.normalizer.noise_level[i]
            level = self.normalizer.failure_level[i]
            series = drift[s].to_numpy()
            current = float(series[-1])
            progress = float(np.clip((abs(current) - noise) / (level - noise), 0, 1.5))
            info = SENSOR_INFO[s]
            out.append(
                {
                    "sensor": s,
                    "symbol": info["symbol"],
                    "name": info["name"],
                    "unit": info["unit"],
                    "subsystem": info["subsystem"],
                    "value": round(float(df[s].iloc[-1]), 4),
                    "drift": round(current, 2),
                    "noise_level": round(float(noise), 2),
                    "failure_level": round(float(level), 2),
                    "typical_direction": "up" if self.normalizer.direction[i] > 0 else "down",
                    "progress": round(progress, 3),
                    "state": "alert" if progress >= 1.0 else "elevated" if progress >= 0.5 else "normal",
                    "series": [round(float(v), 3) for v in series],
                }
            )
        out.sort(key=lambda s: s["progress"], reverse=True)
        return out

    def _warnings(self, df: pd.DataFrame) -> list[str]:
        warnings = []
        n = len(df)
        if n < 30:
            warnings.append(
                f"Only {n} cycles recorded. Trend features need about 30 cycles, so this estimate is less reliable."
            )
        if int(df["cycle"].iloc[0]) > 10:
            warnings.append(
                f"History starts at cycle {int(df['cycle'].iloc[0])}. Drift is measured from the first recorded "
                "cycles, so wear before that point is not visible to the model."
            )
        gaps = np.diff(df["cycle"].to_numpy())
        if len(gaps) and gaps.max() > 1:
            warnings.append("Some cycles are missing from the history. Rolling features treat the gap as continuous.")
        return warnings

    def _summary(self, last: pd.Series, contributions: list[dict], sensors: list[dict]) -> str:
        horizon = self.policy.horizon
        rul, lo, hi = last["rul"], last["rul_low"], last["rul_high"]
        prob = last["failure_probability"]
        cap = self.policy.rul_cap
        if rul >= cap - 1:
            life = f"No degradation trend yet. Estimated life is beyond the model's {cap}-cycle horizon"
        else:
            life = f"Estimated remaining life is {rul:.0f} cycles (80% range {lo:.0f}–{hi:.0f})"
        chance = "under 1%" if prob < 0.01 else "over 99%" if prob > 0.99 else f"{prob:.0%}"
        risk = f"{chance} chance of failure within {horizon} cycles"

        drivers = [c for c in contributions if c["cycles"] < 0 and c["feature"] != "cycle"][:3]
        if drivers and rul < cap - 1:
            names = ", ".join(f"{c['symbol']} ({c['label']})" for c in drivers)
            why = f"Life is shortened mainly by {names}."
        else:
            why = "No sensor is pulling the estimate down noticeably."

        worst = [s for s in sensors if s["state"] != "normal"][:2]
        if worst:
            parts = [
                f"{s['symbol']} is past its typical failure-level drift ({s['drift']:+.1f}σ)"
                if s["progress"] >= 1
                else f"{s['symbol']} has drifted {s['progress']:.0%} of the way to its typical failure level"
                for s in worst
            ]
            drift = " " + "; ".join(parts) + "."
        else:
            drift = ""
        return f"{life}, {risk}. {why}{drift}"

    # --------------------------------------------------------------- display

    def card(self) -> dict:
        """Public model card: what the model is, how it was tested, how status is decided."""
        m = self.meta
        return {
            "version": self.version,
            "trained_at": m["trained_at"],
            "algorithm": m["algorithm"],
            "training_data": m["training_data"],
            "features": {
                "count": len(self.features),
                "sensors": [{"sensor": s, **SENSOR_INFO[s]} for s in self.normalizer.sensors],
                "description": m["feature_description"],
            },
            "policy": self.policy.__dict__,
            "metrics": m["metrics"],
            "limitations": m["limitations"],
        }
