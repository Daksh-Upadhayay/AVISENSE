"""NASA C-MAPSS turbofan dataset: column layout, sensor catalog and file loaders.

Sensor names and units follow Saxena et al. (2008), "Damage Propagation Modeling
for Aircraft Engine Run-to-Failure Simulation", Table 2.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

DATASETS = ("FD001", "FD002", "FD003", "FD004")

SETTINGS = ("setting_1", "setting_2", "setting_3")
ALL_SENSORS = tuple(f"sensor_{i}" for i in range(1, 22))
RAW_COLUMNS = ("unit", "cycle", *SETTINGS, *ALL_SENSORS)

# Sensors that carry degradation signal in every subset. The others are constant
# within an operating condition and add nothing once the condition is removed.
MODEL_SENSORS = (
    "sensor_2", "sensor_3", "sensor_4", "sensor_7", "sensor_8", "sensor_9", "sensor_11",
    "sensor_12", "sensor_13", "sensor_14", "sensor_15", "sensor_17", "sensor_20", "sensor_21",
)

SETTING_INFO = {
    "setting_1": {"symbol": "Alt", "name": "Altitude", "unit": "kft"},
    "setting_2": {"symbol": "Mach", "name": "Mach number", "unit": ""},
    "setting_3": {"symbol": "TRA", "name": "Throttle resolver angle", "unit": "%"},
}

SENSOR_INFO = {
    "sensor_1": {"symbol": "T2", "name": "Fan inlet temperature", "unit": "°R", "subsystem": "Fan"},
    "sensor_2": {"symbol": "T24", "name": "LPC outlet temperature", "unit": "°R", "subsystem": "Low-pressure compressor"},
    "sensor_3": {"symbol": "T30", "name": "HPC outlet temperature", "unit": "°R", "subsystem": "High-pressure compressor"},
    "sensor_4": {"symbol": "T50", "name": "LPT outlet temperature", "unit": "°R", "subsystem": "Turbine"},
    "sensor_5": {"symbol": "P2", "name": "Fan inlet pressure", "unit": "psia", "subsystem": "Fan"},
    "sensor_6": {"symbol": "P15", "name": "Bypass-duct pressure", "unit": "psia", "subsystem": "Fan"},
    "sensor_7": {"symbol": "P30", "name": "HPC outlet pressure", "unit": "psia", "subsystem": "High-pressure compressor"},
    "sensor_8": {"symbol": "Nf", "name": "Physical fan speed", "unit": "rpm", "subsystem": "Fan"},
    "sensor_9": {"symbol": "Nc", "name": "Physical core speed", "unit": "rpm", "subsystem": "High-pressure compressor"},
    "sensor_10": {"symbol": "epr", "name": "Engine pressure ratio", "unit": "", "subsystem": "Engine"},
    "sensor_11": {"symbol": "Ps30", "name": "HPC outlet static pressure", "unit": "psia", "subsystem": "High-pressure compressor"},
    "sensor_12": {"symbol": "phi", "name": "Fuel flow to Ps30 ratio", "unit": "pps/psi", "subsystem": "Combustor"},
    "sensor_13": {"symbol": "NRf", "name": "Corrected fan speed", "unit": "rpm", "subsystem": "Fan"},
    "sensor_14": {"symbol": "NRc", "name": "Corrected core speed", "unit": "rpm", "subsystem": "High-pressure compressor"},
    "sensor_15": {"symbol": "BPR", "name": "Bypass ratio", "unit": "", "subsystem": "Fan"},
    "sensor_16": {"symbol": "farB", "name": "Burner fuel-air ratio", "unit": "", "subsystem": "Combustor"},
    "sensor_17": {"symbol": "htBleed", "name": "Bleed enthalpy", "unit": "", "subsystem": "Engine"},
    "sensor_18": {"symbol": "Nf_dmd", "name": "Demanded fan speed", "unit": "rpm", "subsystem": "Fan"},
    "sensor_19": {"symbol": "PCNfR_dmd", "name": "Demanded corrected fan speed", "unit": "rpm", "subsystem": "Fan"},
    "sensor_20": {"symbol": "W31", "name": "HPT coolant bleed", "unit": "lbm/s", "subsystem": "Turbine"},
    "sensor_21": {"symbol": "W32", "name": "LPT coolant bleed", "unit": "lbm/s", "subsystem": "Turbine"},
}

DATASET_INFO = {
    "FD001": {"conditions": 1, "fault_modes": "HPC degradation"},
    "FD002": {"conditions": 6, "fault_modes": "HPC degradation"},
    "FD003": {"conditions": 1, "fault_modes": "HPC and fan degradation"},
    "FD004": {"conditions": 6, "fault_modes": "HPC and fan degradation"},
}

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "cmapss"


def read_raw(path: Path) -> pd.DataFrame:
    """Read a whitespace-separated C-MAPSS file (26 columns, no header)."""
    df = pd.read_csv(path, sep=r"\s+", header=None, names=list(RAW_COLUMNS))
    df["unit"] = df["unit"].astype(int)
    df["cycle"] = df["cycle"].astype(int)
    return df


def load_train(dataset: str, data_dir: Path = DEFAULT_DATA_DIR) -> pd.DataFrame:
    """Training trajectories run to failure, with the true RUL of every row."""
    df = read_raw(data_dir / f"train_{dataset}.txt")
    last = df.groupby("unit")["cycle"].transform("max")
    df["rul"] = last - df["cycle"]
    return df


def load_test(dataset: str, data_dir: Path = DEFAULT_DATA_DIR) -> pd.DataFrame:
    """Test trajectories cut off before failure, with the true RUL of every row.

    The official RUL file gives the remaining life after the last recorded cycle.
    """
    df = read_raw(data_dir / f"test_{dataset}.txt")
    final_rul = pd.read_csv(data_dir / f"RUL_{dataset}.txt", header=None).iloc[:, 0].to_numpy()
    units = sorted(df["unit"].unique())
    end_rul = dict(zip(units, final_rul))
    last = df.groupby("unit")["cycle"].transform("max")
    df["rul"] = df["unit"].map(end_rul) + last - df["cycle"]
    return df
