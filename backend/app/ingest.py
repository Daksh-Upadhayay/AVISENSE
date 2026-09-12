"""Parse and validate uploaded engine histories.

Accepted formats
- CSV with a header row: `cycle`, `setting_1..3`, and sensor columns named either
  `sensor_N` or by symbol (`T24`, `Ps30`, ...). Extra columns are ignored.
- Raw NASA C-MAPSS text: 26 whitespace-separated columns, no header. Files with
  several engines need the `unit` to import.
"""

from __future__ import annotations

import io

import numpy as np
import pandas as pd

from app.ml.cmapss import ALL_SENSORS, RAW_COLUMNS, SENSOR_INFO, SETTINGS
from app.ml.model import REQUIRED_COLUMNS

ALIASES = {info["symbol"].lower(): key for key, info in SENSOR_INFO.items()}
ALIASES.update({k: k for k in (*SETTINGS, *ALL_SENSORS, "cycle", "unit")})
ALIASES.update({"time_cycles": "cycle", "time": "cycle", "alt": "setting_1", "altitude": "setting_1", "mach": "setting_2", "tra": "setting_3"})


class UploadError(ValueError):
    pass


def parse_history(content: bytes, unit: int | None = None, max_rows: int = 2000) -> list[dict]:
    text = content.decode("utf-8-sig", errors="replace").strip()
    if not text:
        raise UploadError("The file is empty.")
    first = text.splitlines()[0]
    if any(c.isalpha() for c in first):
        df = _read_csv(text)
    else:
        df = _read_raw(text)

    if "unit" in df.columns:
        units = sorted(df["unit"].dropna().astype(int).unique())
        if unit is None and len(units) > 1:
            shown = ", ".join(map(str, units[:10])) + (" ..." if len(units) > 10 else "")
            raise UploadError(f"The file contains {len(units)} engines (units {shown}). Choose which unit to import.")
        if unit is not None:
            if unit not in units:
                raise UploadError(f"Unit {unit} is not in the file.")
            df = df[df["unit"] == unit]

    return validate_frame(df, max_rows)


def validate_rows(rows: list[dict], max_rows: int = 2000) -> list[dict]:
    """Validate readings sent as JSON, with the same rules as file uploads."""
    if not rows:
        raise UploadError("No readings given.")
    df = pd.DataFrame(rows)
    df = df.rename(columns={c: ALIASES[str(c).lower()] for c in df.columns if str(c).lower() in ALIASES})
    return validate_frame(df, max_rows)


def validate_frame(df: pd.DataFrame, max_rows: int) -> list[dict]:
    if "cycle" not in df.columns:
        df = df.assign(cycle=np.arange(1, len(df) + 1))
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise UploadError(f"Missing columns: {', '.join(missing)}.")

    keep = ["cycle", *[c for c in (*SETTINGS, *ALL_SENSORS) if c in df.columns]]
    df = df[keep].apply(pd.to_numeric, errors="coerce")
    bad = df[list(REQUIRED_COLUMNS)].isna().any(axis=1)
    if bad.any():
        rows = ", ".join(str(i + 1) for i in np.flatnonzero(bad.to_numpy())[:5])
        raise UploadError(f"Non-numeric or empty values in required columns (readings {rows}).")
    values = df.to_numpy(dtype=float)
    if np.isinf(values).any():
        raise UploadError("The file contains infinite values.")
    df["cycle"] = df["cycle"].astype(int)
    if (df["cycle"] < 1).any():
        raise UploadError("Cycle numbers must start at 1 or higher.")
    if df["cycle"].duplicated().any():
        raise UploadError("Cycle numbers repeat. Each cycle may appear once.")
    if len(df) > max_rows:
        raise UploadError(f"At most {max_rows} cycles per upload.")

    df = df.sort_values("cycle")
    records = df.to_dict("records")
    for r in records:
        r["cycle"] = int(r["cycle"])
        for k, v in list(r.items()):
            if isinstance(v, float) and np.isnan(v):
                r[k] = None
    return records


def _read_csv(text: str) -> pd.DataFrame:
    try:
        df = pd.read_csv(io.StringIO(text), sep=None, engine="python")
    except (pd.errors.ParserError, ValueError) as e:
        raise UploadError("Could not read the CSV file.") from e
    renamed = {}
    for col in df.columns:
        key = ALIASES.get(str(col).strip().lower())
        if key and key not in renamed.values():
            renamed[col] = key
    return df.rename(columns=renamed)[list(renamed.values())]


def _read_raw(text: str) -> pd.DataFrame:
    try:
        df = pd.read_csv(io.StringIO(text), sep=r"\s+", header=None)
    except (pd.errors.ParserError, ValueError) as e:
        raise UploadError("Could not read the file.") from e
    if df.shape[1] != len(RAW_COLUMNS):
        raise UploadError(
            f"Files without a header must be in NASA C-MAPSS format ({len(RAW_COLUMNS)} columns). "
            f"This file has {df.shape[1]}. Add a header row naming the columns instead."
        )
    df.columns = list(RAW_COLUMNS)
    return df
