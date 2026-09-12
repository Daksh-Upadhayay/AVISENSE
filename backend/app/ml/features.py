"""Operating-condition normalization and rolling-window features.

Raw C-MAPSS sensor values mostly reflect the flight condition (altitude, Mach,
throttle), not engine health. We first map every reading to one of the six
operating regimes, then express each sensor as a z-score against the healthy
early-life baseline for that regime. Degradation then shows up as drift away
from zero, which is comparable across regimes and across engines.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from app.ml.cmapss import MODEL_SENSORS, SETTINGS

# Settings span very different ranges (altitude 0-42, Mach 0-0.84, TRA 60-100).
SETTING_SCALE = np.array([42.0, 0.84, 40.0])
HEALTHY_CYCLES = 30  # early-life window used as each engine's healthy reference
FAILURE_RUL = 10  # rows this close to failure define the "typical failure" level
HEALTHY_RUL = 100  # rows further than this from failure define normal noise
MIN_STD = 1e-3

SHORT_WINDOW = 10
LONG_WINDOW = 30
SLOPE_WINDOW = 20


@dataclass
class Normalizer:
    """Maps raw readings to per-regime z-scores. Fitted on training data only."""

    centroids: np.ndarray  # (n_regimes, 3) operating settings
    mean: np.ndarray  # (n_regimes, n_sensors) healthy mean
    std: np.ndarray  # (n_regimes, n_sensors) healthy std
    direction: np.ndarray  # (n_sensors,) +1 if drift near failure is usually upward, -1 if downward
    noise_level: np.ndarray  # (n_sensors,) 95th percentile |drift| of healthy engines
    failure_level: np.ndarray  # (n_sensors,) median |drift| near failure
    sensors: tuple[str, ...] = MODEL_SENSORS

    @classmethod
    def fit(cls, train: pd.DataFrame) -> "Normalizer":
        rounded = pd.DataFrame(
            {
                "a": train["setting_1"].round(0),
                "m": train["setting_2"].round(2),
                "t": train["setting_3"].round(0),
            }
        )
        groups = rounded.value_counts()
        # Real regimes have thousands of rows. Rounding noise gives a handful.
        centroids = np.array([list(k) for k, n in groups.items() if n >= 100], dtype=float)
        centroids = centroids[np.lexsort(centroids.T[::-1])]

        partial = cls(
            centroids=centroids,
            mean=np.zeros((len(centroids), len(MODEL_SENSORS))),
            std=np.ones((len(centroids), len(MODEL_SENSORS))),
            direction=np.ones(len(MODEL_SENSORS)),
            noise_level=np.zeros(len(MODEL_SENSORS)),
            failure_level=np.ones(len(MODEL_SENSORS)),
        )
        regime = partial.assign_regime(train)
        healthy = train["cycle"].to_numpy() <= HEALTHY_CYCLES
        values = train[list(MODEL_SENSORS)].to_numpy(dtype=float)
        for r in range(len(centroids)):
            rows = values[healthy & (regime == r)]
            partial.mean[r] = rows.mean(axis=0)
            partial.std[r] = np.maximum(rows.std(axis=0), MIN_STD)

        drift = sensor_drift(train, partial).to_numpy()
        rul = train["rul"].to_numpy()
        at_failure = drift[rul <= FAILURE_RUL]
        healthy_drift = np.abs(drift[rul > HEALTHY_RUL])
        partial.direction = np.where(np.median(at_failure, axis=0) >= 0, 1.0, -1.0)
        partial.noise_level = np.quantile(healthy_drift, 0.95, axis=0)
        partial.failure_level = np.maximum(np.median(np.abs(at_failure), axis=0), partial.noise_level + 0.5)
        return partial

    def assign_regime(self, df: pd.DataFrame) -> np.ndarray:
        settings = df[list(SETTINGS)].to_numpy(dtype=float) / SETTING_SCALE
        centroids = self.centroids / SETTING_SCALE
        dist = ((settings[:, None, :] - centroids[None, :, :]) ** 2).sum(axis=2)
        return dist.argmin(axis=1)

    def zscore(self, df: pd.DataFrame) -> pd.DataFrame:
        regime = self.assign_regime(df)
        values = df[list(self.sensors)].to_numpy(dtype=float)
        z = (values - self.mean[regime]) / self.std[regime]
        return pd.DataFrame(z, columns=list(self.sensors), index=df.index)

    def to_dict(self) -> dict:
        return {
            "centroids": self.centroids.tolist(),
            "mean": self.mean.tolist(),
            "std": self.std.tolist(),
            "direction": self.direction.tolist(),
            "noise_level": self.noise_level.tolist(),
            "failure_level": self.failure_level.tolist(),
            "sensors": list(self.sensors),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Normalizer":
        return cls(
            centroids=np.array(d["centroids"]),
            mean=np.array(d["mean"]),
            std=np.array(d["std"]),
            direction=np.array(d["direction"]),
            noise_level=np.array(d["noise_level"]),
            failure_level=np.array(d["failure_level"]),
            sensors=tuple(d["sensors"]),
        )


def feature_names(sensors: tuple[str, ...] = MODEL_SENSORS) -> list[str]:
    names = ["cycle"]
    for s in sensors:
        names += [
            f"{s}__mean{SHORT_WINDOW}",
            f"{s}__mean{LONG_WINDOW}",
            f"{s}__slope{SLOPE_WINDOW}",
            f"{s}__drift",
        ]
    return names


def feature_sensor(name: str) -> str:
    """Sensor a feature was derived from ('cycle' for engine age)."""
    return name.split("__")[0]


def _rolling_slope(t: pd.Series, x: pd.DataFrame, groups: pd.Series, window: int) -> pd.DataFrame:
    """Least-squares slope of x against t over a trailing window, per engine."""

    tx = x.mul(t, axis=0)
    t_frame = pd.DataFrame({"t": t, "t2": t * t}, index=x.index)
    mt = _rolling_mean(t_frame, groups, window)
    mx = _rolling_mean(x, groups, window)
    mtx = _rolling_mean(tx, groups, window)
    var_t = (mt["t2"] - mt["t"] ** 2).to_numpy()[:, None]
    cov = mtx.to_numpy() - mt["t"].to_numpy()[:, None] * mx.to_numpy()
    with np.errstate(divide="ignore", invalid="ignore"):
        slope = np.where(var_t > 1e-9, cov / var_t, 0.0)
    return pd.DataFrame(slope, columns=x.columns, index=x.index)


def _rolling_mean(frame: pd.DataFrame, groups: pd.Series, window: int) -> pd.DataFrame:
    return frame.groupby(groups).rolling(window, min_periods=1).mean().reset_index(level=0, drop=True).reindex(frame.index)


def _drift(z: pd.DataFrame, short: pd.DataFrame, groups: pd.Series) -> pd.DataFrame:
    # Engines leave the factory with different amounts of wear. Measuring drift
    # against each engine's own first recorded cycles removes that offset.
    first_rows = groups.groupby(groups).cumcount() < SHORT_WINDOW
    reference = z.where(first_rows).groupby(groups).expanding().mean().reset_index(level=0, drop=True).reindex(z.index)
    return short - reference


def sensor_drift(df: pd.DataFrame, normalizer: Normalizer) -> pd.DataFrame:
    """Smoothed z-score minus the engine's own starting level, in healthy standard deviations."""
    z = normalizer.zscore(df)
    return _drift(z, _rolling_mean(z, df["unit"], SHORT_WINDOW), df["unit"])


def build_features(df: pd.DataFrame, normalizer: Normalizer) -> pd.DataFrame:
    """Feature matrix with one row per input row.

    `df` needs `unit`, `cycle`, the three settings and the model sensors. Rows
    must be sorted by unit then cycle. Each row only uses its own past, so the
    features for cycle t are what the model would have seen live at cycle t.
    """
    z = normalizer.zscore(df)
    groups = df["unit"]
    short = _rolling_mean(z, groups, SHORT_WINDOW)
    long = _rolling_mean(z, groups, LONG_WINDOW)
    slope = _rolling_slope(df["cycle"].astype(float), z, groups, SLOPE_WINDOW)
    drift = _drift(z, short, groups)

    columns = {"cycle": df["cycle"].to_numpy(dtype=float)}
    for s in normalizer.sensors:
        columns[f"{s}__mean{SHORT_WINDOW}"] = short[s].to_numpy()
        columns[f"{s}__mean{LONG_WINDOW}"] = long[s].to_numpy()
        columns[f"{s}__slope{SLOPE_WINDOW}"] = slope[s].to_numpy()
        columns[f"{s}__drift"] = drift[s].to_numpy()
    return pd.DataFrame(columns, index=df.index)[feature_names(normalizer.sensors)]
