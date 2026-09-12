"""Fleet replay: stream NASA test engines into the app one cycle at a time.

Test engines stop before failure and the true remaining life at the last
recorded cycle is published, so for replayed engines we know the true RUL at
every cycle. The UI shows it next to the prediction.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from app.ml.cmapss import ALL_SENSORS, DATASETS, SETTINGS, load_test

REPLAY_COLUMNS = ("cycle", *SETTINGS, *ALL_SENSORS)


@dataclass(frozen=True)
class ReplaySource:
    dataset: str
    unit: int
    length: int  # cycles available
    final_rul: int  # true RUL after the last available cycle

    def true_rul(self, cycle: int) -> int:
        return self.final_rul + self.length - cycle


@lru_cache(maxsize=4)
def _dataset(data_dir: Path, name: str) -> pd.DataFrame:
    return load_test(name, data_dir)


def source_for(data_dir: Path, dataset: str, unit: int) -> ReplaySource:
    df = _dataset(data_dir, dataset)
    rows = df[df["unit"] == unit]
    if rows.empty:
        raise ValueError(f"{dataset} has no unit {unit}")
    return ReplaySource(dataset, unit, int(rows["cycle"].max()), int(rows["rul"].iloc[-1]))


def cycles(data_dir: Path, source: ReplaySource, start: int, stop: int) -> list[dict]:
    """Readings for cycles start+1 .. stop (1-based cycle numbers)."""
    df = _dataset(data_dir, source.dataset)
    rows = df[(df["unit"] == source.unit) & (df["cycle"] > start) & (df["cycle"] <= stop)]
    out = rows[list(REPLAY_COLUMNS)].to_dict("records")
    for r in out:
        r["cycle"] = int(r["cycle"])
    return out


def pick_demo_fleet(data_dir: Path, size: int, seed: int | None = None) -> list[tuple[ReplaySource, int]]:
    """A varied demo fleet: engines from every subset, half of them heading for failure.

    Returns (source, starting cycle) pairs. Each engine starts part-way through
    its record so there is history to assess and cycles left to replay.
    """
    rng = np.random.default_rng(seed)
    fleet = []
    taken: set[tuple[str, int]] = set()
    for i in range(size):
        dataset = DATASETS[i % len(DATASETS)]
        df = _dataset(data_dir, dataset)
        ends = df.groupby("unit").agg(length=("cycle", "max"), final_rul=("rul", "last"))
        ends = ends[(ends["length"] >= 80) & ~ends.index.isin([u for d, u in taken if d == dataset])]
        # Alternate between engines that end close to failure and random ones.
        pool = ends[ends["final_rul"] <= 25] if i % 2 == 0 else ends
        unit = int(rng.choice(pool.index.to_numpy()))
        length, final_rul = int(ends.loc[unit, "length"]), int(ends.loc[unit, "final_rul"])
        taken.add((dataset, unit))
        if i % 4 == 0:
            # Start close to the end so the fleet opens with engines that need attention.
            start = length - int(rng.integers(5, 25))
        else:
            start = int(rng.integers(int(length * 0.45), int(length * 0.75)))
        fleet.append((ReplaySource(dataset, unit, length, final_rul), max(30, start)))
    return fleet
