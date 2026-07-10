"""Load and normalise the Summer Ridge master meter register.

The Excel file in data/ is the single source of truth for which meters exist,
which stand and floor they belong to, and whether AMR is installed. Keep it
updated in the GitHub repo and both the app and the hourly import pick the
changes up automatically.
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

MASTER_SHEET_PATH = Path(__file__).resolve().parent.parent / "data" / "Summer_Ridge_Master_Sheet.xlsx"

COMMUNAL_FLOOR = "Communal / Bulk"
FLOOR_ORDER = ["01", "02", "03", "04", "05", "06", "07", "08", COMMUNAL_FLOOR]


def _floor_from_stand(stand: str) -> str:
    m = re.match(r"\s*FL(\d+)", str(stand))
    return m.group(1).zfill(2) if m else COMMUNAL_FLOOR


def load_master(path: Path | str = MASTER_SHEET_PATH) -> pd.DataFrame:
    """Return one tidy DataFrame with both utilities.

    Columns: serial, stand, utility ('elec'|'gas'), floor, parent_meter,
    model, amr_active.
    """
    xl = pd.ExcelFile(path)

    elec = pd.read_excel(xl, "Elec")
    elec.columns = [c.strip() for c in elec.columns]
    elec = elec.rename(
        columns={
            "SerialNumber": "serial",
            "Stand": "stand",
            "Parent Meter": "parent_meter",
            "Manufacturer-Model": "model",
            "AMR Active": "amr_active",
        }
    )
    elec["utility"] = "elec"

    gas = pd.read_excel(xl, "Gas")
    gas.columns = [c.strip() for c in gas.columns]
    gas = gas.rename(
        columns={"Meter Serial": "serial", "Stand": "stand", "AMR Active": "amr_active"}
    )
    gas["utility"] = "gas"
    gas["parent_meter"] = None
    gas["model"] = None

    cols = ["serial", "stand", "utility", "parent_meter", "model", "amr_active"]
    df = pd.concat([elec[cols], gas[cols]], ignore_index=True)

    df["serial"] = df["serial"].astype(str).str.strip()
    df["stand"] = df["stand"].astype(str).str.strip()
    for col in ("parent_meter", "model"):
        df[col] = df[col].map(lambda v: str(v).strip() if pd.notna(v) else None)
    df["amr_active"] = df["amr_active"].fillna(False).astype(bool)
    df["floor"] = df["stand"].map(_floor_from_stand)
    df = df.dropna(subset=["serial"])
    df = df[df["serial"].str.lower().isin(["nan", "none", ""]) == False]  # noqa: E712
    return df
